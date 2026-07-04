"""
Shared utility helpers for TG Downloader Bot.

Consolidates duplicated _format_size, _format_time, _format_speed
and torrent monitoring logic used by multiple modules.
"""

import asyncio
import logging
from typing import Optional

logger = logging.getLogger("tg-downloader.helpers")


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def format_size(size_bytes: Optional[int]) -> str:
    """Format bytes into a human-readable string."""
    if not size_bytes:
        return "未知大小"
    size = float(size_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} PB"


def format_time(seconds: float) -> str:
    """Format seconds into a human-readable time string."""
    if seconds < 60:
        return f"{seconds:.0f}秒"
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    if minutes < 60:
        return f"{minutes}分{secs}秒"
    hours = minutes // 60
    minutes = minutes % 60
    return f"{hours}时{minutes}分{secs}秒"


def format_speed(size_bytes: int, elapsed_seconds: float) -> str:
    """Format download speed as a human-readable string."""
    if elapsed_seconds <= 0:
        return ""
    speed = size_bytes / elapsed_seconds
    return f" | ⚡ {format_size(int(speed))}/s"


# ---------------------------------------------------------------------------
# Torrent monitoring
# ---------------------------------------------------------------------------

async def monitor_torrent(
    qb_client,
    info_hash: str,
    notifier,
    *,
    label: str = "磁力链",
    interval: int = 30,
) -> None:
    """
    Periodically poll qBittorrent for torrent progress and send notifications.

    Sends progress updates at 25 % intervals, notifies on completion and errors.
    Runs until the torrent completes, errors, or is removed.

    Args:
        qb_client: QBittorrentClient instance.
        info_hash: Torrent info hash to monitor.
        notifier: BaseNotifier instance for sending messages.
        label: Display label for notifications (e.g. "磁力链" or "种子").
        interval: Polling interval in seconds (default 30).
    """
    last_progress = -1
    while True:
        await asyncio.sleep(interval)
        try:
            info = await qb_client.get_torrent_info(info_hash)
            if info is None:
                logger.warning("Torrent %s not found (may have been removed)", info_hash)
                return

            name = info.get("name", "Unknown")
            progress = info.get("progress", 0) * 100  # 0.0-1.0 → percentage
            state = info.get("state", "")

            # Notify every 25 % (send all missed thresholds on large jumps)
            current_step = int(progress / 25) * 25
            if current_step > last_progress:
                for step in range(max(last_progress + 25, 25), current_step + 1, 25):
                    if step > progress:
                        break
                    last_progress = step
                    await notifier.send(
                        f"🧲 *{label}下载进度*\n"
                        f"📄 `{name}`\n"
                        f"📊 {step:.0f}% (实际 {progress:.0f}%) - 状态: {state}"
                    )

            # Completion
            if state in ("completed", "downloaded"):
                await notifier.send(
                    f"✅ *{label}下载完成*\n📄 `{name}`"
                )
                return

            # Errors
            if state in ("error", "missingFiles", "unknown"):
                await notifier.send(
                    f"❌ *{label}下载异常*\n📄 `{name}`\n状态: {state}"
                )
                return

        except Exception as e:
            logger.error("Error monitoring torrent %s: %s", info_hash, e)
            # Don't abort on transient errors, keep polling at a slower rate
            await asyncio.sleep(interval * 2)
