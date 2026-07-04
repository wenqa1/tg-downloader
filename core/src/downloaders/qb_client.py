"""
qBittorrent Web API client - add and monitor magnet/torrent downloads.

Uses qBittorrent v2 Web API.
Documentation: https://github.com/qbittorrent/qBittorrent/wiki/Web-API-Documentation
"""

import asyncio
import logging
import os
import re
import time
from typing import Any, Optional

import aiohttp

logger = logging.getLogger("tg-downloader.qbittorrent")


class QBittorrentClient:
    """Async client for qBittorrent Web API (v2)."""

    def __init__(self, base_url: str, username: str, password: str):
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self._session: Optional[aiohttp.ClientSession] = None
        self._cookie: Optional[str] = None
        self._session_lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------

    async def _get_session(self) -> aiohttp.ClientSession:
        async with self._session_lock:
            if self._session is None or self._session.closed:
                self._session = aiohttp.ClientSession()
                self._cookie = None  # Reset cookie if we make a new session
            return self._session

    async def _login(self) -> bool:
        """Authenticate with qBittorrent and store session cookie."""
        session = await self._get_session()
        try:
            async with session.post(
                f"{self.base_url}/api/v2/auth/login",
                data={"username": self.username, "password": self.password},
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status == 200:
                    text = await resp.text()
                    if text.strip() == "Ok.":
                        # Store session cookie
                        raw_cookie = resp.headers.get("Set-Cookie", "")
                        self._cookie = raw_cookie.split(";")[0] if raw_cookie else None
                        logger.info("qBittorrent login successful")
                        return True
                logger.warning(f"qBittorrent login failed: HTTP {resp.status}")
                return False
        except (aiohttp.ClientError, asyncio.TimeoutError, OSError) as e:
            logger.error(f"qBittorrent connection error: {e}")
            return False

    async def _ensure_auth(self) -> bool:
        """Make sure we have a valid session, logging in if needed."""
        if self._cookie:
            return True
        return await self._login()

    # ------------------------------------------------------------------
    # Core request helpers
    # ------------------------------------------------------------------

    async def _get_json(self, path: str, params: Optional[dict] = None) -> Any:
        """GET a JSON endpoint. Returns parsed JSON or None on failure."""
        session = await self._get_session()
        if not await self._ensure_auth():
            return None

        headers = {"Cookie": self._cookie or ""}
        try:
            async with session.get(
                f"{self.base_url}{path}",
                params=params,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status == 403:
                    # Session expired, re-login and retry once
                    self._cookie = None
                    if await self._login():
                        headers = {"Cookie": self._cookie or ""}
                        async with session.get(
                            f"{self.base_url}{path}",
                            params=params,
                            headers=headers,
                            timeout=aiohttp.ClientTimeout(total=15),
                        ) as retry_resp:
                            if retry_resp.status == 200:
                                return await retry_resp.json()
                    return None
                if resp.status == 200:
                    return await resp.json()
                logger.warning(f"GET {path} returned HTTP {resp.status}")
                return None
        except (aiohttp.ClientError, asyncio.TimeoutError, OSError) as e:
            logger.error(f"qBittorrent GET error: {e}")
            return None

    async def _post_form(
        self, path: str, data: dict,
    ) -> tuple[bool, str]:
        """POST form data. Returns (success, response_text_or_error)."""
        session = await self._get_session()
        if not await self._ensure_auth():
            return False, "Authentication failed"

        headers = {"Cookie": self._cookie or ""}
        try:
            async with session.post(
                f"{self.base_url}{path}",
                data=data,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                if resp.status == 403:
                    self._cookie = None
                    if await self._login():
                        headers = {"Cookie": self._cookie or ""}
                        async with session.post(
                            f"{self.base_url}{path}",
                            data=data,
                            headers=headers,
                            timeout=aiohttp.ClientTimeout(total=30),
                        ) as retry_resp:
                            if retry_resp.status in (200, 201, 202):
                                return True, await retry_resp.text()
                            return False, f"HTTP {retry_resp.status}"
                    return False, "Re-login failed"
                if resp.status in (200, 201, 202):
                    return True, await resp.text()
                return False, f"HTTP {resp.status}"
        except (aiohttp.ClientError, asyncio.TimeoutError, OSError) as e:
            logger.error(f"qBittorrent POST error: {e}")
            return False, str(e)

    async def _post_multipart(
        self, path: str, form_data: aiohttp.FormData,
    ) -> tuple[bool, str]:
        """POST multipart data (for torrent file uploads)."""
        session = await self._get_session()
        if not await self._ensure_auth():
            return False, "Authentication failed"

        headers = {"Cookie": self._cookie or ""}
        try:
            async with session.post(
                f"{self.base_url}{path}",
                data=form_data,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=60),
            ) as resp:
                if resp.status == 403:
                    self._cookie = None
                    if await self._login():
                        headers = {"Cookie": self._cookie or ""}
                        async with session.post(
                            f"{self.base_url}{path}",
                            data=form_data,
                            headers=headers,
                            timeout=aiohttp.ClientTimeout(total=60),
                        ) as retry_resp:
                            if retry_resp.status in (200, 201, 202):
                                return True, await retry_resp.text()
                            return False, f"HTTP {retry_resp.status}"
                    return False, "Re-login failed"
                if resp.status in (200, 201, 202):
                    return True, await resp.text()
                return False, f"HTTP {resp.status}"
        except (aiohttp.ClientError, asyncio.TimeoutError, OSError) as e:
            logger.error(f"qBittorrent multipart POST error: {e}")
            return False, str(e)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def add_magnet(self, magnet_link: str, save_path: str = "") -> Optional[str]:
        """
        Add a magnet link to qBittorrent.

        Returns the info hash on success, None on failure.
        """
        success, msg = await self._post_form(
            "/api/v2/torrents/add",
            data={"urls": magnet_link, "savepath": save_path},
        )
        if success:
            logger.info(f"Magnet added: {magnet_link[:80]}...")
            return self._extract_info_hash(magnet_link)
        logger.error(f"Failed to add magnet: {msg}")
        return None

    async def add_torrent_file(self, file_path: str, save_path: str = "") -> bool:
        """Add a .torrent file from disk to qBittorrent. Returns True on success."""
        try:
            # Read file content into memory first so retries don't get an empty file
            with open(file_path, "rb") as f:
                file_content = f.read()

            data = aiohttp.FormData()
            data.add_field("torrents", file_content, filename=os.path.basename(file_path))
            if save_path:
                data.add_field("savepath", save_path)

            success, msg = await self._post_multipart(
                "/api/v2/torrents/add", data,
            )
            if success:
                logger.info(f"Torrent file added: {file_path}")
                return True
            logger.error(f"Failed to add torrent file: {msg}")
            return False
        except FileNotFoundError:
            logger.error(f"Torrent file not found: {file_path}")
            return False
        except Exception as e:
            logger.error(f"Error adding torrent file: {e}")
            return False

    async def get_torrent_info(self, info_hash: str) -> Optional[dict]:
        """Get information about a specific torrent by info hash."""
        data = await self._get_json(
            "/api/v2/torrents/info",
            params={"hashes": info_hash},
        )
        if data and isinstance(data, list) and len(data) > 0:
            return data[0]
        return None

    async def list_torrents(self) -> list:
        """List all torrents in qBittorrent."""
        data = await self._get_json("/api/v2/torrents/info")
        return data if isinstance(data, list) else []

    async def is_alive(self) -> bool:
        """Check if qBittorrent Web API is accessible."""
        try:
            session = await self._get_session()
            async with session.get(
                f"{self.base_url}/api/v2/app/version",
                timeout=aiohttp.ClientTimeout(total=5),
            ) as resp:
                return resp.status == 200
        except Exception:
            return False

    async def check_and_login(self) -> bool:
        """Explicitly check connectivity and log in. Returns True on success."""
        try:
            session = await self._get_session()
            async with session.get(
                f"{self.base_url}/api/v2/app/version",
                timeout=aiohttp.ClientTimeout(total=5),
            ) as resp:
                if resp.status == 200:
                    # Login to establish session
                    return await self._login()
                return False
        except Exception:
            return False

    async def close(self):
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
        self._session = None
        self._cookie = None

    @staticmethod
    def _extract_info_hash(magnet: str) -> Optional[str]:
        """Extract lowercased info hash from a magnet link."""
        match = re.search(r"btih:([a-fA-F0-9]{40})", magnet)
        if match:
            return match.group(1).lower()
        return None
