from __future__ import annotations

import os
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("SOCIAL_TOOLS_DATA_DIR", PROJECT_DIR / "runtime")).resolve()


def tool_data_dir(tool_name: str) -> Path:
    path = DATA_DIR / tool_name
    path.mkdir(parents=True, exist_ok=True)
    return path
