"""
Command handler - processes text commands in the download group.
Supports: status, help, stats, id
"""

import logging
import os
import time

from telethon import TelegramClient

from config import Config
from helpers import format_size, format_time
from notifiers.base import BaseNotifier

logger = logging.getLogger("tg-downloader.command_handler")

# App start time (for uptime calculation)
_START_TIME = time.time()

# Recognized text commands (case-insensitive)
COMMANDS = {
    "help": "显示帮助信息",
    "start": "启动/帮助信息",
    "status": "查看下载状态",
    "stats": "查看下载统计",
    "id": "获取当前群组和用户 ID",
}


async def handle_command(
    event,
    client: TelegramClient,
    config: Config,
    notifier: BaseNotifier,
    qb_client,
) -> None:
    """
    Handle text commands like "help", "status", "stats", "id".
    Only responds to the owner. Returns early if no command is matched.
    """
    msg = event.message
    text = (msg.text or msg.message or "").strip().lower()

    if not text:
        return

    # Skip if it's a magnet/URL (those are handled by magnet_handler)
    if text.startswith("magnet:") or text.startswith("http"):
        return

    # Check if this looks like a command
    command = text.lstrip("/")  # Also support /command format for bot-mode compat

    if command not in COMMANDS:
        return  # Not a recognized command

    logger.info(f"Command received: '{command}' from user {event.sender_id}")

    if command in ("help", "start"):
        await _cmd_help(notifier, config)
    elif command == "status":
        await _cmd_status(notifier, qb_client)
    elif command == "stats":
        await _cmd_stats(notifier, config)
    elif command == "id":
        await _cmd_id(event, notifier)


async def _cmd_help(notifier: BaseNotifier, config: Config) -> None:
    """Show help information."""
    help_text = (
        "🤖 *TG Downloader Bot*\n\n"
        "把我转发到群里，我来帮你下载文件！\n\n"
        "*支持的内容:*\n"
        "🎬 视频 (mp4, mkv, avi, mov...)\n"
        "🎵 音乐 (mp3, flac, wav...)\n"
        "🖼️ 图片 (jpg, png, gif...)\n"
        "📄 文档 (pdf, zip, rar...)\n"
        "🧲 磁力链 (magnet:?...)\n"
        "🌱 种子文件 (.torrent)\n\n"
        "*可用命令:*\n"
        "• `help` / `start` - 显示此帮助\n"
        "• `status` - 查看 qBittorrent 下载状态\n"
        "• `stats` - 查看下载统计\n"
        "• `id` - 获取当前群和用户 ID\n\n"
        "直接转发文件或发送磁力链到群里即可开始下载 ✅"
    )
    await notifier.send(help_text)


async def _cmd_status(notifier: BaseNotifier, qb_client) -> None:
    """Show qBittorrent download status."""
    try:
        torrents = await qb_client.list_torrents()
    except Exception as e:
        await notifier.send(f"❌ 无法连接 qBittorrent: {e}")
        return

    if not torrents:
        await notifier.send("📊 *qBittorrent 状态*\n当前没有活动的下载任务。")
        return

    # Group by state
    downloading = [t for t in torrents if t.get("state") in ("downloading", "stalledDL")]
    seeding = [t for t in torrents if t.get("state") in ("uploading", "stalledUP")]
    paused = [t for t in torrents if t.get("state") == "pausedDL"]
    completed = [t for t in torrents if t.get("state") in ("completed", "downloaded")]
    error = [t for t in torrents if t.get("state") in ("error", "missingFiles")]

    lines = ["📊 *qBittorrent 状态*"]
    if downloading:
        lines.append(f"\n⬇️ *下载中:* {len(downloading)} 个")
        for t in downloading[:5]:
            pct = t.get("progress", 0) * 100
            name = t.get("name", "Unknown")[:50]
            lines.append(f"  • `{name}` — {pct:.0f}%")
    if seeding:
        lines.append(f"\n⬆️ *做种中:* {len(seeding)} 个")
    if paused:
        lines.append(f"\n⏸️ *已暂停:* {len(paused)} 个")
    if completed:
        lines.append(f"\n✅ *已完成:* {len(completed)} 个")
    if error:
        lines.append(f"\n❌ *异常:* {len(error)} 个")

    await notifier.send("\n".join(lines))


async def _cmd_stats(notifier: BaseNotifier, config: Config) -> None:
    """Show download statistics."""
    base = config.download_base_path

    # Count files by category
    categories = ["video", "audio", "photo", "document", "torrents"]
    stats_lines = ["📊 *下载统计*"]

    for cat in categories:
        dir_path = os.path.join(base, cat)
        if os.path.isdir(dir_path):
            files = [f for f in os.listdir(dir_path) if os.path.isfile(os.path.join(dir_path, f))]
            total_size = sum(
                os.path.getsize(os.path.join(dir_path, f))
                for f in files
                if os.path.isfile(os.path.join(dir_path, f))
            )
            icon = {"video": "🎬", "audio": "🎵", "photo": "🖼️", "document": "📄", "torrents": "🧲"}.get(cat, "📁")
            label = {"torrents": "Torrents"}.get(cat, cat.capitalize())
            stats_lines.append(f"\n{icon} *{label}:* {len(files)} 个 ({format_size(total_size)})")

    # Uptime
    uptime = time.time() - _START_TIME
    stats_lines.append(f"\n⏱️ *运行时间:* {format_time(int(uptime))}")

    await notifier.send("\n".join(stats_lines))


async def _cmd_id(event, notifier: BaseNotifier) -> None:
    """Show current chat and user IDs."""
    msg = event.message
    chat_id = msg.chat_id
    sender_id = event.sender_id

    await notifier.send(
        f"📋 *群组信息*\n"
        f"👤 你的 User ID: `{sender_id}`\n"
        f"💬 当前群 Chat ID: `{chat_id}`"
    )


