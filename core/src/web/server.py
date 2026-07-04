"""
TG Downloader - Web Management Interface

FastAPI-based web server providing:
  - Dashboard with download stats
  - File browser by category
  - Torrent management (qBittorrent proxy)
  - Recent download history

Run with: python -m src.web.server
Access at: http://localhost:8081
"""

import logging
import os
import re
import sys
from datetime import datetime
from typing import Optional

import uvicorn
from fastapi import FastAPI, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# Add src to path so we can import config
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from src.config import load_config
from src.downloaders.qb_client import QBittorrentClient
from src.helpers import format_size

logger = logging.getLogger("tg-downloader.web")

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------
config = load_config()

BASE_PATH = config.download_base_path  # /downloads
LOG_PATH = "/app/logs/bot.log"
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")

CATEGORIES = ["video", "audio", "photo", "document", "torrents"]

# Shared qBittorrent client (created once, reused across requests)
_qb_client: Optional[QBittorrentClient] = None


def _get_qb_client() -> QBittorrentClient:
    """Get or create the shared qBittorrent client singleton."""
    global _qb_client
    if _qb_client is None:
        _qb_client = QBittorrentClient(
            base_url=config.qb_url,
            username=config.qb_username,
            password=config.qb_password,
        )
    return _qb_client
CATEGORY_ICONS = {
    "video": "🎬", "audio": "🎵", "photo": "🖼️",
    "document": "📄", "torrents": "🧲",
}
CATEGORY_LABELS = {
    "video": "视频", "audio": "音频", "photo": "图片",
    "document": "文档", "torrents": "种子",
}

app = FastAPI(title="TG Downloader Manager")

# Mount static files
os.makedirs(STATIC_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

templates = Jinja2Templates(directory=TEMPLATE_DIR)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_time(timestamp_str: str) -> Optional[str]:
    """Parse log timestamp like '2026-07-04 12:30:45' to friendly format."""
    try:
        dt = datetime.strptime(timestamp_str.strip()[:19], "%Y-%m-%d %H:%M:%S")
        now = datetime.now()
        diff = now - dt
        if diff.days == 0:
            if diff.seconds < 60:
                return "刚刚"
            elif diff.seconds < 3600:
                return f"{diff.seconds // 60}分钟前"
            else:
                return f"{diff.seconds // 3600}小时前"
        elif diff.days == 1:
            return "昨天"
        elif diff.days < 7:
            return f"{diff.days}天前"
        else:
            return dt.strftime("%m-%d")
    except ValueError:
        return timestamp_str[:19]


def _scan_category(category: str) -> list[dict]:
    """Scan a download category directory and return file info."""
    if category == "torrents":
        dir_path = os.path.join(BASE_PATH, "torrents")
        # Skip the watch subdirectory
        files = []
        if os.path.isdir(dir_path):
            for name in os.listdir(dir_path):
                filepath = os.path.join(dir_path, name)
                if os.path.isfile(filepath) and name != "watch":
                    stat = os.stat(filepath)
                    files.append({
                        "name": name,
                        "size": stat.st_size,
                        "size_str": format_size(stat.st_size),
                        "modified": stat.st_mtime,
                        "time_str": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
                    })
        return sorted(files, key=lambda f: f["modified"], reverse=True)
    else:
        dir_path = os.path.join(BASE_PATH, category)
        if not os.path.isdir(dir_path):
            return []
        files = []
        for name in os.listdir(dir_path):
            filepath = os.path.join(dir_path, name)
            if os.path.isfile(filepath):
                stat = os.stat(filepath)
                files.append({
                    "name": name,
                    "size": stat.st_size,
                    "size_str": format_size(stat.st_size),
                    "modified": stat.st_mtime,
                    "time_str": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
                })
        return sorted(files, key=lambda f: f["modified"], reverse=True)


def _get_category_stats() -> dict:
    """Get statistics for all categories."""
    stats = {}
    total_files = 0
    total_size = 0

    for cat in CATEGORIES:
        files = _scan_category(cat)
        cat_size = sum(f["size"] for f in files)
        stats[cat] = {
            "count": len(files),
            "size": cat_size,
            "size_str": format_size(cat_size),
        }
        total_files += len(files)
        total_size += cat_size

    return {
        "categories": stats,
        "total_files": total_files,
        "total_size": total_size,
        "total_size_str": format_size(total_size),
    }


def _parse_recent_logs(lines: int = 50) -> list[dict]:
    """Parse recent download events from the log file."""
    events = []
    if not os.path.exists(LOG_PATH):
        return events

    # Download-related patterns
    patterns = [
        (r"开始下载", "start", "📥"),
        (r"下载完成|下载成功", "complete", "✅"),
        (r"下载失败", "error", "❌"),
        (r"已添加磁力链|磁力链已添加", "magnet", "🧲"),
        (r"磁力链下载完成", "torrent_done", "✅"),
        (r"磁力链下载异常", "torrent_error", "❌"),
    ]

    try:
        with open(LOG_PATH, "r", encoding="utf-8") as f:
            lines = f.readlines()[-lines:]
    except (FileNotFoundError, IOError):
        return events

    for line in reversed(lines):
        line = line.strip()
        if not line:
            continue

        # Parse timestamp
        time_str = line[:19] if len(line) > 19 else ""
        relative = _parse_time(time_str)
        message = line[30:] if len(line) > 30 else line  # Strip timestamp + level

        # Check for download events
        event_type = None
        icon = None
        for pattern, etype, eicon in patterns:
            if re.search(pattern, line, re.IGNORECASE):
                event_type = etype
                icon = eicon
                break

        if event_type:
            events.append({
                "time": relative,
                "type": event_type,
                "icon": icon,
                "message": message[:120],
            })

    return events[:30]


# ---------------------------------------------------------------------------
# Routes - Pages
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "page": "dashboard",
    })


@app.get("/files", response_class=HTMLResponse)
async def files_page(request: Request, category: str = "video"):
    if category not in CATEGORIES:
        category = "video"
    return templates.TemplateResponse("files.html", {
        "request": request,
        "page": "files",
        "current_category": category,
        "categories": CATEGORIES,
        "category_labels": CATEGORY_LABELS,
        "category_icons": CATEGORY_ICONS,
    })


@app.get("/torrents", response_class=HTMLResponse)
async def torrents_page(request: Request):
    return templates.TemplateResponse("torrents.html", {
        "request": request,
        "page": "torrents",
    })


# ---------------------------------------------------------------------------
# Routes - API
# ---------------------------------------------------------------------------

@app.get("/api/stats")
async def api_stats():
    """Dashboard statistics."""
    stats = _get_category_stats()
    recent = _parse_recent_logs(20)

    # Check if qBittorrent is alive (proxy check)
    qb_status = "unknown"
    try:
        qb = _get_qb_client()
        qb_status = "online" if await qb.is_alive() else "offline"
    except Exception:
        qb_status = "offline"

    # Check bot status (log file freshness)
    bot_status = "offline"
    if os.path.exists(LOG_PATH):
        mtime = os.path.getmtime(LOG_PATH)
        if (datetime.now().timestamp() - mtime) < 300:  # Updated within 5 min
            bot_status = "online"
        else:
            bot_status = "idle"

    return {
        "stats": stats,
        "recent": recent,
        "qb_status": qb_status,
        "bot_status": bot_status,
    }


@app.get("/api/files/{category}")
async def api_files(category: str, search: str = ""):
    """List files in a category, optionally filtered by search."""
    if category not in CATEGORIES:
        return {"error": "Invalid category"}

    files = _scan_category(category)
    if search:
        search_lower = search.lower()
        files = [f for f in files if search_lower in f["name"].lower()]

    return {
        "category": category,
        "files": files,
        "total": len(files),
        "label": CATEGORY_LABELS.get(category, category),
        "icon": CATEGORY_ICONS.get(category, "📁"),
    }


@app.get("/api/torrents")
async def api_torrents():
    """Proxy to qBittorrent - list active torrents."""
    try:
        qb = _get_qb_client()
        torrents = await qb.list_torrents()

        # Filter and simplify
        active = []
        for t in torrents:
            progress = t.get("progress", 0) * 100
            state = t.get("state", "")
            active.append({
                "name": t.get("name", "Unknown"),
                "progress": round(progress, 1),
                "state": state,
                "size": format_size(t.get("total_size", 0)),
                "downloaded": format_size(t.get("downloaded", 0)),
                "speed": format_size(t.get("dlspeed", 0)) + "/s",
                "eta": _format_eta(t.get("eta", 0)),
                "ratio": round(t.get("ratio", 0), 2),
            })

        return {"torrents": active, "count": len(active)}
    except Exception:
        logger.exception("Failed to fetch torrents from qBittorrent")
        return {"error": "无法连接 qBittorrent，请检查服务状态", "torrents": []}


@app.get("/api/logs")
async def api_logs():
    """Recent download events from logs."""
    events = _parse_recent_logs(100)
    return {"events": events}


def _format_eta(seconds: int) -> str:
    if seconds <= 0 or seconds == 8640000:
        return "∞"
    if seconds < 60:
        return f"{seconds}s"
    if seconds < 3600:
        return f"{seconds // 60}m {seconds % 60}s"
    return f"{seconds // 3600}h {(seconds % 3600) // 60}m"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    port = int(os.getenv("WEB_PORT", "8081"))
    host = os.getenv("WEB_HOST", "0.0.0.0")

    print(f"🌐 TG Downloader Manager starting on http://{host}:{port}")
    print(f"📂 Download path: {BASE_PATH}")

    uvicorn.run(
        "src.web.server:app",
        host=host,
        port=port,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()
