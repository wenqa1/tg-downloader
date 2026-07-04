"""
File/media download handler.
Processes messages containing videos, audio, photos, and documents.
"""

import asyncio
import logging
import os
import time
from typing import Optional

from telethon import TelegramClient
from telethon.tl.custom import Message

from config import Config
from helpers import format_size, format_speed, format_time, monitor_torrent
from notifiers.base import BaseNotifier
from organizer.classifier import classify, get_filename, get_download_path, resolve_conflict

logger = logging.getLogger("tg-downloader.file_handler")

# Files above this size (in bytes) will show progress notifications
PROGRESS_THRESHOLD = 50 * 1024 * 1024  # 50 MB

# Progress notification intervals (percentage)
PROGRESS_STEPS = [25, 50, 75]


async def handle_file(
    event,
    client: TelegramClient,
    config: Config,
    notifier: BaseNotifier,
    qb_client,  # QBittorrentClient, not used here
) -> None:
    """
    Handle a message that contains downloadable media (file/photo/video/audio/document).

    Returns early (without error) if the message doesn't contain media,
    so handlers can be chained.
    """
    msg: Message = event.message

    # Skip if no media content
    if not (msg.video or msg.audio or msg.voice or msg.photo or
            msg.document or msg.video_note or msg.sticker):
        return

    # Classify the file type
    category = classify(msg)
    if category == "unknown":
        logger.debug(f"Message {msg.id} has no recognizable media")
        return

    # Handle torrent files separately (send to qBittorrent, not download here)
    if category == "torrent":
        logger.info(f"Torrent file detected in message {msg.id}, queuing for qBittorrent")
        await _handle_torrent_file(msg, client, config, notifier, qb_client)
        return

    # Generate file info
    filename = get_filename(msg, category)
    file_size = _get_file_size(msg)
    size_str = format_size(file_size)
    download_path = get_download_path(config.download_base_path, category, filename)
    download_path = resolve_conflict(download_path)

    # Notify: starting download
    await notifier.send(
        f"📥 *开始下载*\n"
        f"📄 `{filename}`\n"
        f"📦 {size_str}\n"
        f"📂 分类: {category}"
    )

    logger.info(f"Downloading: {filename} ({size_str}) to {download_path}")

    # Track progress for large files
    progress_callback = None
    if file_size and file_size > PROGRESS_THRESHOLD:
        progress_callback = _make_progress_callback(
            notifier, filename, file_size
        )

    # Download the file using Telethon
    start_time = time.time()
    try:
        downloaded_path = await client.download_media(
            message=msg,
            file=download_path,
            progress_callback=progress_callback,
        )
    except Exception as e:
        logger.error(f"Download failed for {filename}: {e}", exc_info=True)
        await notifier.send(
            f"❌ *下载失败*\n📄 `{filename}`\n原因: {str(e)[:200]}"
        )
        return

    # Check result
    if downloaded_path:
        elapsed = time.time() - start_time
        final_size = format_size(os.path.getsize(downloaded_path))
        speed = format_speed(file_size, elapsed) if elapsed > 0 else ""

        await notifier.send(
            f"✅ *下载完成*\n"
            f"📄 `{os.path.basename(downloaded_path)}`\n"
            f"📦 {final_size}\n"
            f"⏱️ {format_time(elapsed)}{speed}\n"
            f"📂 `{downloaded_path}`"
        )
        logger.info(f"Download complete: {downloaded_path}")
    else:
        await notifier.send(
            f"❌ *下载失败*\n📄 `{filename}`\n原因: 下载返回空结果"
        )


async def _handle_torrent_file(
    msg, client, config, notifier, qb_client,
) -> None:
    """Download a .torrent file to the watch directory, then hand off to qBittorrent."""
    # Download torrent file to watch directory
    watch_dir = os.path.join(config.download_base_path, "torrents", "watch")
    os.makedirs(watch_dir, exist_ok=True)

    try:
        torrent_path = await client.download_media(
            message=msg,
            file=os.path.join(watch_dir, get_filename(msg, "torrent")),
        )
    except Exception as e:
        logger.error(f"Failed to download torrent file: {e}")
        await notifier.send(f"❌ *种子文件下载失败*\n原因: {str(e)[:200]}")
        return

    if not torrent_path:
        await notifier.send("❌ *种子文件下载失败*\n原因: 下载返回空结果")
        return

    # Add to qBittorrent
    torrents_dir = os.path.join(config.download_base_path, "torrents")
    added = await qb_client.add_torrent_file(torrent_path, save_path=torrents_dir)

    if added:
        await notifier.send(
            f"🧲 *已添加种子到 qBittorrent*\n"
            f"📄 `{os.path.basename(torrent_path)}`\n"
            f"进度: 0% (等待下载中...)"
        )
    else:
        await notifier.send(
            f"❌ *种子添加到 qBittorrent 失败*\n"
            f"请检查 qBittorrent 是否正常运行"
        )


def _get_file_size(msg: Message) -> Optional[int]:
    """Extract file size from a message in bytes."""
    if msg.video:
        return msg.video.size
    if msg.audio:
        return msg.audio.size
    if msg.voice:
        return msg.voice.size
    if msg.document:
        return msg.document.size
    if msg.video_note:
        return msg.video_note.size
    if msg.photo:
        # Estimate photo size from largest size
        sizes = getattr(msg.photo, "sizes", [])
        if sizes:
            last = sizes[-1]
            return getattr(last, "size", 0) or 0
    if msg.sticker:
        return getattr(msg.sticker, "size", 0) or 0
    return None


def _make_progress_callback(notifier, filename: str, file_size: int):
    """
    Create a progress callback for Telethon's download_media.
    Sends notification at predefined percentage steps.
    """
    reported_steps = set()

    async def callback(current: int, total: int) -> None:
        if total <= 0:
            return
        pct = int((current / total) * 100)

        # Find which step thresholds we've crossed
        for step in PROGRESS_STEPS:
            if pct >= step and step not in reported_steps:
                reported_steps.add(step)
                downloaded = format_size(current)
                await notifier.send(
                    f"⏳ *下载中:* `{filename}`\n"
                    f"📊 {pct}% ({downloaded})"
                )

    return callback
