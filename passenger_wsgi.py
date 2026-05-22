import os
import sys
from pathlib import Path

from a2wsgi import ASGIMiddleware


BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault("INSTAGRAM_REQUEST_TIMEOUT", "18")

from main import app as asgi_app  # noqa: E402


application = ASGIMiddleware(asgi_app)
