"""
Magnet link handler.
Detects magnet links in text messages and sends them to qBittorrent.
"""

import asyncio
import logging
import os
import re
import time
from typing import Optional

import aiohttp

from telethon import TelegramClient

from config import Config
from notifiers.base import BaseNotifier

logger = logging.getLogger("tg-downloader.magnet_handler")

# Magnet link pattern
MAGNET_PATTERN = re.compile(r"magnet:\?xt=urn:btih:[a-fA-F0-9]{40}(?:[^\s]*)?", re.IGNORECASE)

# Torrent URL pattern (direct .torrent file URLs)
TORRENT_URL_PATTERN = re.compile(
    r"https?://[^\s]+\.torrent(?:\?[^\s]*)?", re.IGNORECASE
)


async def handle_magnet(
    event,
    client: TelegramClient,
    config: Config,
    notifier: BaseNotifier,
    qb_client,
) -> None:
    """
    Handle messages containing magnet links or torrent URLs.
    Returns early if no magnet/torrent link is found.
    """
    msg = event.message
    text = msg.text or msg.message or ""

    if not text.strip():
        return

    # Check for magnet links
    magnet_matches = MAGNET_PATTERN.findall(text)
    if magnet_matches:
        logger.info(f"Found {len(magnet_matches)} magnet link(s) in message {msg.id}")
        for magnet_link in magnet_matches[:5]:  # Limit to 5 per message
            await _process_magnet(magnet_link, qb_client, notifier, config)
        return

    # Check for torrent URLs
    torrent_matches = TORRENT_URL_PATTERN.findall(text)
    if torrent_matches:
        logger.info(f"Found {len(torrent_matches)} torrent URL(s) in message {msg.id}")
        for url in torrent_matches[:5]:
            await _process_torrent_url(url, qb_client, notifier, config)
        return


async def _process_magnet(
    magnet_link: str, qb_client, notifier: BaseNotifier, config: Config,
) -> None:
    """Add a magnet link to qBittorrent and notify."""
    await notifier.send(
        f"🧲 *检测到磁力链*\n`{magnet_link[:80]}...`\n正在添加到 qBittorrent..."
    )

    torrents_dir = f"{config.download_base_path}/torrents"
    info_hash = await qb_client.add_magnet(magnet_link, save_path=torrents_dir)

    if info_hash:
        await notifier.send(
            f"✅ *磁力链已添加*\n"
            f"哈希: `{info_hash}`\n"
            f"📊 进度: 0% (等待下载中...)"
        )
        # Start monitoring in background
        asyncio.ensure_future(
            _monitor_torrent_internal(qb_client, info_hash, notifier)
        )
    else:
        await notifier.send(
            "❌ *磁力链添加失败*\n请检查 qBittorrent 是否正常运行"
        )


async def _process_torrent_url(
    url: str, qb_client, notifier: BaseNotifier, config: Config,
) -> None:
    """Download a .torrent URL and add it to qBittorrent."""
    await notifier.send(f"🌐 *检测到种子链接*\n正在下载种子文件...")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status != 200:
                    await notifier.send(f"❌ *种子文件下载失败*\nHTTP {resp.status}")
                    return

                # Save to watch directory
                watch_dir = f"{config.download_base_path}/torrents/watch"
                os.makedirs(watch_dir, exist_ok=True)

                filename = os.path.basename(url.split("?")[0])
                if not filename.endswith(".torrent"):
                    filename = f"torrent_{int(time.time())}.torrent"

                filepath = os.path.join(watch_dir, filename)
                content = await resp.read()
                with open(filepath, "wb") as f:
                    f.write(content)

                # Add to qBittorrent
                torrents_dir = f"{config.download_base_path}/torrents"
                info_hash = await qb_client.add_torrent_file(filepath, save_path=torrents_dir)

                if info_hash:
                    await notifier.send(
                        f"✅ *种子已添加到 qBittorrent*\n📄 `{filename}`"
                    )
                else:
                    await notifier.send("❌ *种子添加失败*")
    except Exception as e:
        logger.error(f"Failed to process torrent URL: {e}")
        await notifier.send(f"❌ *种子处理失败*\n原因: {str(e)[:200]}")


async def _monitor_torrent_internal(qb_client, info_hash: str, notifier):
    """Monitor torrent progress and notify on completion."""
    last_progress = -1
    while True:
        await asyncio.sleep(30)
        try:
            info = await qb_client.get_torrent_info(info_hash)
            if info is None:
                return

            name = info.get("name", "Unknown")
            progress = info.get("progress", 0) * 100
            state = info.get("state", "")

            # Progress notification at 25% intervals
            progress_step = int(progress / 25) * 25
            if progress_step > last_progress and progress_step > 0:
                last_progress = progress_step
                await notifier.send(
                    f"🧲 *磁力链下载进度*\n📄 `{name}`\n📊 {progress_step}%"
                )

            if state in ("completed", "downloaded"):
                await notifier.send(f"✅ *磁力链下载完成*\n📄 `{name}`")
                return

            if state in ("error", "missingFiles"):
                await notifier.send(f"❌ *磁力链下载异常*\n📄 `{name}`\n状态: {state}")
                return

        except Exception as e:
            logger.error(f"Torrent monitor error: {e}")
            await asyncio.sleep(60)
