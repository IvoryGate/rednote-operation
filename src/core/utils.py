import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[-\s]+", "-", text)
    return text


def ensure_dir(path: str | Path) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def read_json(path: str | Path) -> dict[str, Any]:
    with open(path) as f:
        return json.load(f)


def write_json(path: str | Path, data: dict[str, Any]) -> None:
    with open(path, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def parse_timestamp(ts: str) -> datetime | None:
    formats = [
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y/%m/%d %H:%M:%S",
        "%Y-%m-%d",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(ts, fmt)
        except ValueError:
            continue
    return None


def days_ago(days: int) -> datetime:
    return datetime.now() - timedelta(days=days)


def truncate_text(text: str, max_length: int = 100) -> str:
    return text[:max_length] + "..." if len(text) > max_length else text
