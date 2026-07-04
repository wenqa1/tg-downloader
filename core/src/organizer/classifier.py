"""
File classifier - determines download category and destination path
based on message media type and file properties.
"""

import mimetypes
import os
import time as _time
from datetime import datetime
from pathlib import Path
from typing import Optional

from telethon.tl.custom import Message

# File extension -> category mapping
EXTENSION_MAP: dict[str, str] = {
    # Video
    ".mp4": "video", ".mkv": "video", ".avi": "video",
    ".mov": "video", ".webm": "video",
    ".flv": "video", ".wmv": "video", ".ts": "video",
    # Audio
    ".mp3": "audio", ".flac": "audio", ".wav": "audio",
    ".aac": "audio", ".ogg": "audio", ".m4a": "audio",
    ".opus": "audio", ".wma": "audio",
    # Image
    ".jpg": "photo", ".jpeg": "photo", ".png": "photo",
    ".gif": "photo", ".webp": "photo", ".bmp": "photo",
    ".tiff": "photo", ".svg": "photo",
    # Document
    ".pdf": "document", ".zip": "document", ".rar": "document",
    ".7z": "document", ".tar": "document", ".gz": "document",
    ".doc": "document", ".docx": "document", ".xls": "document",
    ".xlsx": "document", ".ppt": "document", ".pptx": "document",
    ".txt": "document", ".epub": "document", ".cbz": "document",
    # Torrent
    ".torrent": "torrent",
}


def classify(message: Message) -> str:
    """
    Determine the category of a message's media content.

    Returns one of: "video", "audio", "photo", "document", "torrent"
    """
    # Direct media type checks (fast path)
    if message.video:
        return "video"
    if message.audio or message.voice:
        return "audio"
    if message.photo:
        return "photo"
    if message.video_note:
        return "video"

    # Document - check mime type and extension
    if message.document:
        doc = message.document
        mime = (doc.mime_type or "").lower()
        name = getattr(doc, "file_name", None) or ""
        ext = os.path.splitext(name)[1].lower()

        # MIME type based classification
        if mime.startswith("video/"):
            return "video"
        if mime.startswith("audio/"):
            return "audio"
        if mime.startswith("image/"):
            return "photo"

        # Extension based classification
        if ext in EXTENSION_MAP:
            return EXTENSION_MAP[ext]

        # Fallback: check if it's a torrent file
        if name.endswith(".torrent") or "torrent" in mime:
            return "torrent"

        # Unknown document type
        return "document"

    # WebP stickers with no document wrapper
    if message.sticker:
        return "photo"

    # No media found
    return "unknown"


def get_filename(message: Message, category: str) -> str:
    """
    Generate a safe filename for the downloaded file.
    Preserves original name when available, falls back to date-based naming.
    """
    now = datetime.now()
    date_str = now.strftime("%Y%m%d_%H%M%S")
    msg_id = message.id

    # Try to extract original filename
    original_name: Optional[str] = None

    if message.document:
        original_name = getattr(message.document, "file_name", None)

    if original_name:
        # Sanitize filename
        safe_name = _sanitize_filename(original_name)
        if safe_name:
            return safe_name

    # Generate filename from type and date
    ext = _guess_extension(message, category)
    return f"{category}_{date_str}_{msg_id}{ext}"


def get_download_path(base_path: str, category: str, filename: str) -> str:
    """
    Build the full download path for a file.
    Ensures the target directory exists.

    Special case: torrent files go to a separate path for qBittorrent.
    """
    if category == "torrent":
        # Torrent files go to a watch directory for qBittorrent
        dir_path = os.path.join(base_path, "torrents", "watch")
    else:
        dir_path = os.path.join(base_path, category)

    # Ensure directory exists
    Path(dir_path).mkdir(parents=True, exist_ok=True)

    return os.path.join(dir_path, filename)


def resolve_conflict(filepath: str) -> str:
    """
    If a file already exists, append _1, _2, etc. to avoid overwriting.

    Falls back to a timestamp suffix after MAX_RETRIES attempts.
    """
    if not os.path.exists(filepath):
        return filepath

    base, ext = os.path.splitext(filepath)
    MAX_RETRIES = 1000
    for counter in range(1, MAX_RETRIES + 1):
        new_path = f"{base}_{counter}{ext}"
        if not os.path.exists(new_path):
            return new_path

    # Last resort: timestamp-based suffix (unlikely to reach here)
    return f"{base}_{int(_time.time())}{ext}"


def _sanitize_filename(name: str) -> str:
    """Remove or replace characters that are problematic in filenames."""
    if not name:
        return ""

    # Replace problematic characters
    unsafe_chars = '<>:"/\\|?*'
    for c in unsafe_chars:
        name = name.replace(c, "_")

    # Remove leading/trailing spaces and dots
    name = name.strip(". ")

    # Limit length (keep extension)
    if len(name) > 200:
        base, ext = os.path.splitext(name)
        name = base[:195] + ext

    return name if name else ""


def _guess_extension(message: Message, category: str) -> str:
    """Guess file extension from message media attributes."""
    # Check document for explicit filename
    if message.document:
        doc = message.document
        name = getattr(doc, "file_name", None)
        if name:
            ext = os.path.splitext(name)[1]
            if ext:
                return ext
        # Guess from MIME type
        mime = doc.mime_type or ""
        guessed = mimetypes.guess_extension(mime)
        if guessed:
            return guessed

    # Default extensions per category
    return {
        "video": ".mp4",
        "audio": ".mp3",
        "photo": ".jpg",
        "document": ".bin",
        "torrent": ".torrent",
    }.get(category, ".bin")
