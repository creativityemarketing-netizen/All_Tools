from __future__ import annotations

import asyncio
import json
import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import quote

import httpx
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from tools.storage import tool_data_dir


BASE_DIR = Path(__file__).parent
FRONTEND_DIR = BASE_DIR / "frontend"
TMP_DIR = tool_data_dir("video_transcription") / "tmp"
UPLOAD_DIR = TMP_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

MAX_MEDIA_SIZE = 25 * 1024 * 1024
ALLOWED_UPLOADS = {".mp3", ".mp4", ".mpeg", ".mpga", ".m4a", ".wav", ".webm"}

app = FastAPI(title="Video Transcription")

LANGUAGE_CODES = {
    "Arabic": "ar",
    "Chinese": "zh",
    "English": "en",
    "French": "fr",
    "German": "de",
    "Italian": "it",
    "Portuguese": "pt",
    "Spanish": "es",
}


@app.exception_handler(Exception)
async def json_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error. Check the Render logs for the full backend error."},
    )


def language_code(language: str | None) -> str | None:
    if not language or language == "Auto detect":
        return None
    return LANGUAGE_CODES.get(language, language.lower()[:2])


def referer_for(url: str) -> str | None:
    try:
        host = httpx.URL(url).host or ""
        host = host.removeprefix("www.")
    except Exception:
        return None
    if "instagram" in host:
        return "https://www.instagram.com/"
    if "facebook" in host or "fb.watch" in host:
        return "https://www.facebook.com/"
    if "tiktok" in host:
        return "https://www.tiktok.com/"
    if "youtube" in host or "youtu.be" in host:
        return "https://www.youtube.com/"
    if "twitter" in host or host == "x.com":
        return "https://x.com/"
    return None


def request_headers_for(url: str, cookies: str = "") -> dict[str, str]:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
        "Accept": "*/*",
    }
    referer = referer_for(url)
    if referer:
        headers["Referer"] = referer
    if cookies:
        headers["Cookie"] = cookies
    return headers


async def run_command(command: str, args: list[str], cwd: Path, timeout: int = 240) -> tuple[str, str]:
    def _run() -> tuple[str, str]:
        completed = subprocess.run(
            [command, *args],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
        if completed.returncode != 0:
            raise RuntimeError(completed.stderr or completed.stdout or f"{command} exited with code {completed.returncode}")
        return completed.stdout, completed.stderr

    try:
        return await asyncio.to_thread(_run)
    except subprocess.TimeoutExpired as exc:
        raise HTTPException(status_code=504, detail="The operation took too long. Try a shorter video or upload the file directly.") from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def compact_number(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "-"
    if number >= 1_000_000:
        return f"{number / 1_000_000:.1f}M".replace(".0M", "M")
    if number >= 1_000:
        return f"{number / 1_000:.1f}K".replace(".0K", "K")
    return str(int(number))


def format_duration(seconds: Any) -> str:
    try:
        total = round(float(seconds))
    except (TypeError, ValueError):
        return "-"
    minutes, remaining = divmod(total, 60)
    return f"{minutes:02d}:{remaining:02d}"


def tool_url(path: str, value: str) -> str:
    return f"api/{path}?url={quote(value, safe='')}" if value else ""


def normalize_media_info(info: dict[str, Any], source_url: str) -> dict[str, Any]:
    blocked = bool(info.get("__previewBlocked"))
    thumbnails = info.get("thumbnails") if isinstance(info.get("thumbnails"), list) else []
    thumbnail = info.get("thumbnail") or next((item.get("url") for item in thumbnails if item.get("preference") == 0), "") or (thumbnails[-1].get("url") if thumbnails else "")
    download = info.get("requested_downloads", [{}])[0] if isinstance(info.get("requested_downloads"), list) and info.get("requested_downloads") else {}
    download_url = info.get("url") or download.get("url") or ""
    download_cookies = info.get("cookies") or download.get("cookies") or ""
    has_preview = bool(thumbnail or download_url)
    width = int(info.get("width") or 0)
    height = int(info.get("height") or 0)
    return {
        "id": info.get("id") or "-",
        "title": info.get("title") or info.get("fulltitle") or "Untitled media",
        "description": info.get("description") or "",
        "account": info.get("uploader") or info.get("channel") or info.get("uploader_id") or "Unknown account",
        "accountId": info.get("uploader_id") or info.get("channel_id") or info.get("channel") or "-",
        "duration": format_duration(info.get("duration")),
        "durationSeconds": float(info.get("duration") or 0),
        "width": width,
        "height": height,
        "aspectRatio": (width / height) if width and height else None,
        "views": compact_number(info.get("view_count")),
        "likes": compact_number(info.get("like_count")),
        "comments": compact_number(info.get("comment_count")),
        "thumbnail": tool_url("proxy-image", thumbnail),
        "mediaUrl": tool_url("proxy-media", download_url),
        "downloadUrl": download_url,
        "downloadCookies": download_cookies,
        "pageUrl": info.get("webpage_url") or source_url,
        "previewStatus": "blocked" if blocked else "available" if has_preview else "missing",
        "previewMessage": "This platform blocked preview details. Transcription may still work, or upload the video file."
        if blocked
        else "" if has_preview else "No preview was found for this link. Transcription may still work.",
    }


async def get_media_info(url: str) -> dict[str, Any]:
    try:
        stdout, _ = await run_command(
            "yt-dlp",
            ["--no-playlist", "--skip-download", "--dump-single-json", "--no-write-comments", url],
            BASE_DIR,
            timeout=90,
        )
        return normalize_media_info(json.loads(stdout), url)
    except Exception:
        return normalize_media_info({"webpage_url": url, "__previewBlocked": True}, url)


async def download_video(url: str) -> tuple[Path, Path]:
    job_dir = TMP_DIR / uuid.uuid4().hex
    job_dir.mkdir(parents=True, exist_ok=True)
    await run_command(
        "yt-dlp",
        [
            "--no-playlist",
            "--max-filesize",
            "24M",
            "--format",
            "bestaudio[ext=m4a]/bestaudio/best[ext=mp4][vcodec^=h264][filesize<24M]/worst[ext=mp4][vcodec^=h264]/best",
            "--output",
            "%(id)s.%(ext)s",
            url,
        ],
        job_dir,
        timeout=180,
    )
    media_file = next(
        (
            file
            for file in job_dir.iterdir()
            if file.is_file() and file.suffix.lower() in ALLOWED_UPLOADS
        ),
        None,
    )
    if not media_file:
        raise HTTPException(status_code=422, detail="The video could not be downloaded. It may be private, blocked, or too large.")
    if media_file.stat().st_size > MAX_MEDIA_SIZE:
        raise HTTPException(status_code=413, detail="The downloaded media is larger than 25MB. Try a shorter video or upload the file directly.")
    return media_file, job_dir


async def download_direct_media(media_url: str, source_url: str, cookies: str = "") -> tuple[Path, Path]:
    job_dir = TMP_DIR / uuid.uuid4().hex
    job_dir.mkdir(parents=True, exist_ok=True)
    async with httpx.AsyncClient(timeout=120, follow_redirects=True) as client:
        response = await client.get(
            media_url,
            headers={
                **request_headers_for(source_url or media_url, cookies),
                "Accept": "video/mp4,audio/mp4,audio/mpeg,video/*,audio/*,*/*",
            },
        )
    if response.status_code >= 400:
        raise HTTPException(status_code=422, detail="The preview loaded, but the platform blocked the media download needed for transcription. Upload the file directly.")
    if len(response.content) > MAX_MEDIA_SIZE:
        raise HTTPException(status_code=413, detail="The downloaded media is larger than 25MB. Try a shorter video or upload the file directly.")
    ext = "m4a" if "audio" in response.headers.get("content-type", "") else "mp4"
    file_path = job_dir / f"media.{ext}"
    file_path.write_bytes(response.content)
    return file_path, job_dir


def format_segments(transcription: Any) -> list[dict[str, Any]]:
    segments = getattr(transcription, "segments", None)
    if segments is None and isinstance(transcription, dict):
        segments = transcription.get("segments")
    if not isinstance(segments, list):
        return []
    formatted = []
    for segment in segments:
        get = segment.get if isinstance(segment, dict) else lambda key, default=None: getattr(segment, key, default)
        text = str(get("text", "")).strip()
        if text:
            formatted.append({
                "start": float(get("start", 0) or 0),
                "end": float(get("end", 0) or 0),
                "text": text,
                "speaker": f"Speaker {get('speaker')}" if get("speaker") else None,
            })
    return formatted


async def transcribe_locally(file_path: Path, language: str | None, speed: str | None) -> dict[str, Any]:
    stdout, _ = await run_command(
        sys.executable,
        ["transcribe_local.py", str(file_path), language or "Auto detect", speed or "balanced"],
        BASE_DIR,
        timeout=720 if speed == "accurate" else 420,
    )
    try:
        return json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail="Local Whisper finished, but the transcript output could not be read.") from exc


async def transcribe_with_openai(file_path: Path, language: str | None, diarize: bool) -> dict[str, Any]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="Missing OPENAI_API_KEY. Add it in Bluehost environment variables, then restart the app.")
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise HTTPException(status_code=500, detail="The Python OpenAI package is not installed. Install requirements.txt again.") from exc

    def _transcribe() -> dict[str, Any]:
        client = OpenAI(api_key=api_key)
        request: dict[str, Any] = {
            "file": file_path.open("rb"),
            "model": os.getenv("DIARIZATION_MODEL" if diarize else "TRANSCRIPTION_MODEL", "gpt-4o-transcribe-diarize" if diarize else "gpt-4o-transcribe"),
            "response_format": "diarized_json" if diarize else "json",
        }
        if diarize:
            request["chunking_strategy"] = "auto"
        code = language_code(language)
        if code:
            request["language"] = code
        try:
            transcription = client.audio.transcriptions.create(**request)
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"OpenAI transcription failed: {exc}") from exc
        finally:
            request["file"].close()
        return {"text": getattr(transcription, "text", "") or "", "segments": format_segments(transcription), "diarized": diarize}

    return await asyncio.to_thread(_transcribe)


async def transcribe_file(file_path: Path, language: str | None, speed: str | None, diarize: bool = False) -> dict[str, Any]:
    provider = os.getenv("TRANSCRIPTION_PROVIDER", "local").lower()
    if diarize or provider != "local":
        return await transcribe_with_openai(file_path, language, diarize)
    return await transcribe_locally(file_path, language, speed)


def clean_media_info(info: dict[str, Any]) -> dict[str, Any]:
    cleaned = dict(info)
    cleaned.pop("downloadUrl", None)
    cleaned.pop("downloadCookies", None)
    return cleaned


@app.post("/api/media-info")
async def api_media_info(request: Request):
    payload = await request.json()
    url = str(payload.get("url") or "").strip()
    if not url:
        raise HTTPException(status_code=400, detail="Paste a public video URL first.")
    return {"info": clean_media_info(await get_media_info(url))}


@app.post("/api/transcribe")
async def api_transcribe(request: Request):
    payload = await request.json()
    url = str(payload.get("url") or "").strip()
    if not url:
        raise HTTPException(status_code=400, detail="Paste a public video URL first.")
    language = payload.get("language")
    speed = payload.get("speed") or "balanced"
    diarize = payload.get("diarize") in (True, "true", "True", "1")
    job_dir: Path | None = None
    try:
        media_info = await get_media_info(url)
        try:
            media_file, job_dir = await download_video(url)
        except Exception:
            if not media_info.get("downloadUrl"):
                raise
            media_file, job_dir = await download_direct_media(media_info["downloadUrl"], url, media_info.get("downloadCookies", ""))
        result = await transcribe_file(media_file, language, speed, diarize)
        result["info"] = clean_media_info(media_info)
        return result
    finally:
        if job_dir:
            shutil.rmtree(job_dir, ignore_errors=True)


@app.post("/api/transcribe-upload")
async def api_transcribe_upload(media: UploadFile = File(...), language: str = "Auto detect", speed: str = "balanced", diarize: str = "false"):
    suffix = Path(media.filename or "").suffix.lower()
    if suffix not in ALLOWED_UPLOADS:
        raise HTTPException(status_code=400, detail="Use MP3, MP4, MPEG, MPGA, M4A, WAV, or WEBM media.")
    upload_path = UPLOAD_DIR / f"{uuid.uuid4().hex}{suffix}"
    try:
        size = 0
        with upload_path.open("wb") as dest:
            while chunk := await media.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_MEDIA_SIZE:
                    raise HTTPException(status_code=413, detail="Uploaded media is larger than 25MB.")
                dest.write(chunk)
        result = await transcribe_file(upload_path, language, speed, diarize in ("true", "True", "1"))
        result["info"] = {
            "id": "-",
            "title": media.filename or "Uploaded media",
            "description": "Uploaded local file",
            "account": "Local upload",
            "accountId": "-",
            "duration": "-",
            "durationSeconds": 0,
            "width": 0,
            "height": 0,
            "aspectRatio": None,
            "views": "-",
            "likes": "-",
            "comments": "-",
            "thumbnail": "",
            "mediaUrl": "",
            "pageUrl": "",
        }
        return result
    finally:
        upload_path.unlink(missing_ok=True)


@app.get("/api/proxy-image")
async def api_proxy_image(url: str):
    if not url.lower().startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="Invalid image URL.")
    async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
        response = await client.get(url, headers={**request_headers_for(url), "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8"})
    if response.status_code >= 400:
        raise HTTPException(status_code=response.status_code, detail="Thumbnail could not be loaded.")
    return Response(content=response.content, media_type=response.headers.get("content-type", "image/jpeg"), headers={"Cache-Control": "public, max-age=300"})


@app.get("/api/proxy-media")
async def api_proxy_media(url: str):
    if not url.lower().startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="Invalid media URL.")
    async with httpx.AsyncClient(timeout=120, follow_redirects=True) as client:
        response = await client.get(url, headers={**request_headers_for(url), "Accept": "video/mp4,video/*,*/*"})
    if response.status_code >= 400:
        raise HTTPException(status_code=response.status_code, detail="Video preview could not be loaded.")
    headers = {"Cache-Control": "public, max-age=120"}
    if response.headers.get("content-length"):
        headers["Content-Length"] = response.headers["content-length"]
    return Response(content=response.content, media_type=response.headers.get("content-type", "video/mp4"), headers=headers)


app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="video_transcription_static")
