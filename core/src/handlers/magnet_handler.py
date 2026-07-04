"""
Magnet link handler.
Detects magnet links in text messages and sends them to qBittorrent.
"""

import asyncio
import logging
import os
import re
import time

import aiohttp

from telethon import TelegramClient

from config import Config
from helpers import monitor_torrent
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
        asyncio.create_task(
            monitor_torrent(qb_client, info_hash, notifier, label="磁力链")
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

                # Check content size before reading (max 10MB)
                content_length = resp.headers.get("Content-Length")
                if content_length and int(content_length) > 10 * 1024 * 1024:
                    await notifier.send(
                        f"❌ *种子文件过大*\n文件超过 10MB 限制，已跳过"
                    )
                    return

                content = await resp.read()
                if len(content) > 10 * 1024 * 1024:
                    await notifier.send(
                        f"❌ *种子文件过大*\n实际大小 {len(content)} 字节超过 10MB 限制"
                    )
                    return

                # Generate safe filename from URL
                raw_name = os.path.basename(url.split("?")[0])
                if raw_name.endswith(".torrent"):
                    # Sanitize: only allow safe characters
                    safe_name = re.sub(r'[^\w.\-]', '_', raw_name)
                    filename = safe_name if safe_name else f"torrent_{int(time.time())}.torrent"
                else:
                    filename = f"torrent_{int(time.time())}.torrent"

                # Save to watch directory (async I/O)
                watch_dir = f"{config.download_base_path}/torrents/watch"
                os.makedirs(watch_dir, exist_ok=True)
                filepath = os.path.join(watch_dir, filename)

                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, _write_file, filepath, content)

                # Add to qBittorrent
                torrents_dir = f"{config.download_base_path}/torrents"
                added = await qb_client.add_torrent_file(filepath, save_path=torrents_dir)

                if added:
                    await notifier.send(
                        f"✅ *种子已添加到 qBittorrent*\n📄 `{filename}`"
                    )
                else:
                    await notifier.send("❌ *种子添加失败*")
    except asyncio.TimeoutError:
        logger.error("Timeout downloading torrent URL: %s", url)
        await notifier.send("❌ *种子下载超时*")
    except Exception as e:
        logger.error("Failed to process torrent URL %s: %s", url, e, exc_info=True)
        await notifier.send("❌ *种子处理失败*")


def _write_file(filepath: str, content: bytes) -> None:
    """Synchronous file write, intended for run_in_executor."""
    with open(filepath, "wb") as f:
        f.write(content)


