import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, urlparse

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from starlette.middleware.wsgi import WSGIMiddleware

from tools.instagram_date.app import app as instagram_date_app
from tools.instagram_words.app import app as instagram_words_app
from tools.tiktok.app import app as tiktok_app
from tools.video_transcription.app import app as video_transcription_app
from tools.youtube.app import app as youtube_app


BASE_DIR = Path(__file__).parent
TIKTOK_VIDEO_ID_PATTERN = re.compile(r"^\d{15,25}$")
TIKTOK_VIDEO_URL_PATTERN = re.compile(r"/video/(\d{15,25})")
TIKTOK_QUERY_ID_PATTERN = re.compile(r"(?:item_id|video_id|id)=(\d{15,25})")
TIKTOK_LOOSE_ID_PATTERN = re.compile(r"\b\d{15,25}\b")

app = FastAPI(title="Creativity Solutions")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


class TikTokLookupRequest(BaseModel):
    id: str


TOOLS = [
    {
        "path": "/tools/instagram-date/",
        "platform": "Instagram",
        "title": "Post Date Finder",
        "description": "Search the fixed database by Instagram link, shortcode, or post ID.",
        "icon": "D",
        "class": "instagram",
    },
    {
        "path": "/tools/video-transcription/",
        "platform": "Audio & Video",
        "title": "Video Transcription",
        "description": "Turn video or audio links and uploaded files into editable transcripts.",
        "icon": "V",
        "class": "video",
    },
    {
        "path": "/tools/youtube/",
        "platform": "YouTube",
        "title": "YouTube Channel Exporter",
        "description": "Export channel videos, shorts, dates, links, and engagement into an Excel workbook.",
        "icon": "Y",
        "class": "youtube",
    },
    {
        "path": "/tools/instagram-extension/",
        "platform": "Chrome Extension",
        "title": "Extension Instagram",
        "description": "Install the Instagram scraper extension and learn what it can extract or download.",
        "icon": "E",
        "class": "extension",
    },
    {
        "path": "/tools/tiktok-extension/",
        "platform": "Chrome Extension",
        "title": "TikTok Extension",
        "description": "Install TikGrab to download TikTok videos, export profile data, and search descriptions.",
        "icon": "T",
        "class": "tiktok",
    },
    {
        "path": "/tools/tiktok-id-link/",
        "platform": "TikTok",
        "title": "TikTok ID to Link",
        "description": "Turn a TikTok publication ID into its original video and creator profile links.",
        "icon": "L",
        "class": "tiktok-link",
    },
]

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
app.mount("/tools/instagram-date", WSGIMiddleware(instagram_date_app), name="instagram_date")
app.mount("/tools/instagram-words", WSGIMiddleware(instagram_words_app), name="instagram_words")
app.mount("/tools/tiktok", tiktok_app, name="tiktok")
app.mount("/tools/video-transcription", video_transcription_app, name="video_transcription")
app.mount("/tools/youtube", youtube_app, name="youtube")


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(request, "home.html", {"tools": TOOLS})


@app.get("/tools/instagram-extension/", response_class=HTMLResponse)
async def instagram_extension(request: Request):
    return templates.TemplateResponse(request, "instagram_extension.html")


@app.get("/tools/tiktok-extension/", response_class=HTMLResponse)
async def tiktok_extension(request: Request):
    return templates.TemplateResponse(request, "tiktok_extension.html")


@app.get("/tools/tiktok-id-link/", response_class=HTMLResponse)
async def tiktok_id_link(request: Request):
    return templates.TemplateResponse(request, "tiktok_id_link.html", {"tools": TOOLS})


def extract_tiktok_video_id(value: str) -> str | None:
    value = str(value or "").strip()
    if TIKTOK_VIDEO_ID_PATTERN.fullmatch(value):
        return value
    try:
        parsed = urlparse(value)
        match = TIKTOK_VIDEO_URL_PATTERN.search(parsed.path)
        if match:
            return match.group(1)
        query_match = TIKTOK_QUERY_ID_PATTERN.search(parsed.query)
        if query_match:
            return query_match.group(1)
    except ValueError:
        pass

    loose_match = TIKTOK_LOOSE_ID_PATTERN.search(value)
    return loose_match.group(0) if loose_match else None


def decode_tiktok_publish_date(video_id: str) -> str:
    return datetime.fromtimestamp(int(video_id) >> 32, timezone.utc).isoformat()


def tiktok_fallback_result(
    video_id: str,
    message: str = "Date decoded from the TikTok ID.",
) -> dict:
    fallback_url = f"https://www.tiktok.com/@_/video/{video_id}"
    return {
        "status": "decoded",
        "public_found": False,
        "message": message,
        "video_id": video_id,
        "published_at": decode_tiktok_publish_date(video_id),
        "video_url": fallback_url,
        "profile_url": None,
        "username": None,
        "author_name": None,
        "title": "TikTok publication date decoded from ID",
        "thumbnail_url": None,
    }


@app.post("/api/tiktok-id-lookup")
async def tiktok_id_lookup(payload: TikTokLookupRequest):
    video_id = extract_tiktok_video_id(payload.id)
    if not video_id:
        return JSONResponse(
            {"error": "Enter a valid TikTok publication ID or video URL."},
            status_code=400,
        )

    fallback_url = f"https://www.tiktok.com/@_/video/{video_id}"
    endpoint = "https://www.tiktok.com/oembed?url=" + quote(fallback_url, safe="")
    try:
        async with httpx.AsyncClient(
            timeout=12,
            follow_redirects=True,
            headers={
                "Accept": "application/json",
                "User-Agent": "Creativity-Solutions-TikTok-Resolver/1.0",
            },
        ) as client:
            response = await client.get(endpoint)
    except httpx.RequestError:
        return tiktok_fallback_result(
            video_id,
            "Could not reach TikTok. Date decoded from the ID.",
        )

    if response.status_code in (400, 404):
        return tiktok_fallback_result(
            video_id,
            "TikTok did not return a public video. Date decoded from the ID.",
        )
    if response.status_code >= 400:
        return tiktok_fallback_result(
            video_id,
            "TikTok is temporarily unavailable. Date decoded from the ID.",
        )

    try:
        data = response.json()
    except ValueError:
        return tiktok_fallback_result(
            video_id,
            "TikTok returned an invalid response. Date decoded from the ID.",
        )

    profile_url = data.get("author_url") or ""
    username = data.get("author_unique_id") or ""
    if not username and profile_url:
        username = urlparse(profile_url).path.lstrip("@/").split("/")[0]
    video_url = (
        f"https://www.tiktok.com/@{username}/video/{video_id}"
        if username
        else fallback_url
    )

    return {
        "status": "public",
        "public_found": True,
        "message": "Public video found on TikTok.",
        "video_id": video_id,
        "published_at": decode_tiktok_publish_date(video_id),
        "video_url": video_url,
        "profile_url": profile_url,
        "username": username,
        "author_name": data.get("author_name") or username,
        "title": data.get("title") or "TikTok publication",
        "thumbnail_url": data.get("thumbnail_url") or "",
    }


@app.get("/downloads/instagram-scraper-extension.zip")
async def download_instagram_extension():
    return FileResponse(
        BASE_DIR / "static" / "downloads" / "instagram-extension.zip",
        media_type="application/zip",
        filename="instagram-scraper-extension.zip",
    )


@app.get("/downloads/instagram-extension.zip")
async def download_instagram_extension_legacy():
    return FileResponse(
        BASE_DIR / "static" / "downloads" / "instagram-extension.zip",
        media_type="application/zip",
        filename="instagram-extension.zip",
    )


@app.get("/downloads/tiktok-extension.zip")
async def download_tiktok_extension():
    return FileResponse(
        BASE_DIR / "static" / "downloads" / "tiktok-extension.zip",
        media_type="application/zip",
        filename="tiktok-extension.zip",
    )


@app.get("/health")
async def health():
    return {"ok": True, "tools": len(TOOLS)}
