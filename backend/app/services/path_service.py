from __future__ import annotations

import re
from pathlib import Path


def slugify(value: str, default: str = "item") -> str:
    text = re.sub(r"[^\w\-]+", "_", value.strip(), flags=re.UNICODE)
    text = re.sub(r"_+", "_", text).strip("_")
    return text or default


def require_existing_dir(path_text: str) -> Path:
    path = Path(path_text).expanduser().resolve()
    if not path.exists() or not path.is_dir():
        raise ValueError(f"目录不存在: {path}")
    return path


def require_existing_path(path_text: str) -> Path:
    path = Path(path_text).expanduser().resolve()
    if not path.exists():
        raise ValueError(f"路径不存在: {path}")
    return path


def ensure_dir(path_text: str) -> Path:
    path = Path(path_text).expanduser().resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path

