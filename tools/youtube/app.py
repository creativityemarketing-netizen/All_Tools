from __future__ import annotations

import json
import threading
import uuid
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from tools.youtube.server import (
    YoutubeApiError,
    collect_channel_export,
    collect_channel_export_no_api,
    get_job,
    make_xlsx,
    preview_channel_no_api,
    run_export_job,
    safe_filename,
    set_job,
)


class ExportPayload(BaseModel):
    channelUrl: str
    limit: int | str | None = None
    apiKey: str | None = None


app = FastAPI(title="YouTube Channel Exporter")


def parse_payload(payload: ExportPayload) -> tuple[str, int | None]:
    channel_url = payload.channelUrl.strip()
    limit_text = str(payload.limit or "").strip()
    limit = int(limit_text) if limit_text else None
    if limit is not None and limit <= 0:
        raise ValueError("Limit must be empty or greater than zero.")
    return channel_url, limit


def json_error(status_code: int, message: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"error": message})


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> Response:
    if isinstance(exc.detail, dict):
        return Response(
            json.dumps(exc.detail),
            status_code=exc.status_code,
            media_type="application/json",
        )
    return Response(
        json.dumps({"error": str(exc.detail)}),
        status_code=exc.status_code,
        media_type="application/json",
    )


@app.post("/preview")
def preview(payload: ExportPayload) -> dict[str, Any]:
    try:
        channel_url, _ = parse_payload(payload)
        return preview_channel_no_api(channel_url)
    except (ValueError, YoutubeApiError) as exc:
        raise json_error(400, str(exc)) from exc
    except Exception as exc:
        raise json_error(500, f"Unexpected error: {exc}") from exc


@app.post("/export/start")
def export_start(payload: ExportPayload) -> dict[str, str]:
    try:
        channel_url, limit = parse_payload(payload)
        job_id = uuid.uuid4().hex
        set_job(job_id, status="queued", percent=0, message="Waiting to start")
        thread = threading.Thread(
            target=run_export_job,
            args=(job_id, channel_url, limit),
            daemon=True,
        )
        thread.start()
        return {"jobId": job_id}
    except (ValueError, YoutubeApiError) as exc:
        raise json_error(400, str(exc)) from exc
    except Exception as exc:
        raise json_error(500, f"Unexpected error: {exc}") from exc


@app.get("/export/status")
def export_status(id: str) -> dict[str, Any]:
    job = get_job(id)
    if not job:
        raise json_error(404, "Export job was not found.")
    return {key: value for key, value in job.items() if key != "workbook"}


@app.get("/export/download")
def export_download(id: str) -> Response:
    job = get_job(id)
    if not job or job.get("status") != "done" or not job.get("workbook"):
        raise json_error(404, "Excel file is not ready yet.")
    workbook = job["workbook"]
    filename = job.get("filename", "youtube-channel.xlsx")
    return Response(
        workbook,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.post("/export")
def export(payload: ExportPayload) -> Response:
    try:
        channel_url, limit = parse_payload(payload)
        api_key = str(payload.apiKey or "").strip()
        export_data = (
            collect_channel_export(channel_url, api_key, limit)
            if api_key
            else collect_channel_export_no_api(channel_url, limit)
        )
        workbook = make_xlsx(export_data)
        filename = safe_filename(export_data["channel"].get("Title") or "youtube-channel")
        return Response(
            workbook,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{filename}.xlsx"'},
        )
    except (ValueError, YoutubeApiError) as exc:
        raise json_error(400, str(exc)) from exc
    except Exception as exc:
        raise json_error(500, f"Unexpected error: {exc}") from exc


frontend_dir = Path(__file__).parent / "static"
app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")
