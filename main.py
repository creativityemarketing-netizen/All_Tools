from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.wsgi import WSGIMiddleware

from tools.instagram_date.app import app as instagram_date_app
from tools.instagram_words.app import app as instagram_words_app
from tools.tiktok.app import app as tiktok_app


BASE_DIR = Path(__file__).parent

app = FastAPI(title="Social Tools")
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
        "path": "/tools/instagram-words/",
        "platform": "Instagram",
        "title": "Words Finder",
        "description": "Find words inside captions from profile posts and reels, then export results.",
        "icon": "W",
        "class": "words",
    },
    {
        "path": "/tools/tiktok/",
        "platform": "TikTok",
        "title": "Extract & Downloader",
        "description": "Fetch video metadata, filter account videos, export data, or download selected files.",
        "icon": "T",
        "class": "tiktok",
    },
]

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
app.mount("/tools/instagram-date", WSGIMiddleware(instagram_date_app), name="instagram_date")
app.mount("/tools/instagram-words", WSGIMiddleware(instagram_words_app), name="instagram_words")
app.mount("/tools/tiktok", tiktok_app, name="tiktok")


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(request, "home.html", {"tools": TOOLS})


@app.get("/health")
async def health():
    return {"ok": True, "tools": len(TOOLS)}
