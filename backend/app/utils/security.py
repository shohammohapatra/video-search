import re
from pathlib import Path
from urllib.parse import urlparse, parse_qs

from fastapi import HTTPException, UploadFile, status

from app.core.config import settings


SAFE_NAME_RE = re.compile(r"[^a-zA-Z0-9._-]+")


def sanitize_filename(filename: str) -> str:
    name = Path(filename).name.strip().replace(" ", "_")
    name = SAFE_NAME_RE.sub("_", name)
    return name[:180] or "video"


def validate_upload(file: UploadFile) -> None:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in settings.allowed_video_extensions:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Unsupported video format: {suffix}")


def normalize_youtube_url(url: str) -> str:
    parsed = urlparse(url)
    host = parsed.netloc.lower().replace("www.", "")
    if host not in {"youtube.com", "m.youtube.com", "youtu.be"}:
        raise ValueError("Only YouTube URLs are supported")
    if host == "youtu.be":
        video_id = parsed.path.strip("/")
    else:
        video_id = parse_qs(parsed.query).get("v", [""])[0]
    if not re.fullmatch(r"[A-Za-z0-9_-]{6,}", video_id or ""):
        raise ValueError("Invalid YouTube video id")
    return f"https://www.youtube.com/watch?v={video_id}"

