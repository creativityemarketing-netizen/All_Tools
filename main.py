from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.wsgi import WSGIMiddleware

from tools.instagram_date.app import app as instagram_date_app
from tools.instagram_words.app import app as instagram_words_app
from tools.tiktok.app import app as tiktok_app
from tools.video_transcription.app import app as video_transcription_app


BASE_DIR = Path(__file__).parent

app = FastAPI(title="Creativity Solutions")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

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
        "path": "/tools/instagram-extension/",
        "platform": "Chrome Extension",
        "title": "Extension Instagram",
        "description": "Install the Instagram scraper extension and learn what it can extract or download.",
        "icon": "E",
        "class": "extension",
    },
]

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
app.mount("/tools/instagram-date", WSGIMiddleware(instagram_date_app), name="instagram_date")
app.mount("/tools/instagram-words", WSGIMiddleware(instagram_words_app), name="instagram_words")
app.mount("/tools/tiktok", tiktok_app, name="tiktok")
app.mount("/tools/video-transcription", video_transcription_app, name="video_transcription")


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(request, "home.html", {"tools": TOOLS})


@app.get("/tools/instagram-extension/", response_class=HTMLResponse)
async def instagram_extension(request: Request):
    return templates.TemplateResponse(request, "instagram_extension.html")


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


@app.get("/health")
async def health():
    return {"ok": True, "tools": len(TOOLS)}
