from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from tools.tiktok.api.routes import bulk, export, single, zip as zip_route


app = FastAPI(title="TikTok Extract")

app.include_router(single.router, prefix="/api")
app.include_router(bulk.router, prefix="/api")
app.include_router(export.router, prefix="/api")
app.include_router(zip_route.router, prefix="/api")

frontend_dir = Path(__file__).parent / "frontend"
app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")

