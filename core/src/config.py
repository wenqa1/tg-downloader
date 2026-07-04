"""
Configuration module for TG Downloader Bot.

Loads settings from environment variables (via .env file)
and provides a typed Config dataclass.
"""

import logging
import os
from dataclasses import dataclass, field
from typing import Optional

from dotenv import load_dotenv

logger = logging.getLogger("tg-downloader.config")


@dataclass
class Config:
    """Application configuration, loaded from environment."""

    # Runtime mode: "user" | "bot"
    run_mode: str = "user"

    # Telegram API credentials (required for both modes)
    # Get from https://my.telegram.org
    api_id: int = 0
    api_hash: str = ""

    # User mode: phone number for Telethon login
    phone_number: str = ""

    # Bot mode: bot token from @BotFather
    bot_token: Optional[str] = None

    # Owner's Telegram user ID (whitelist + notifications)
    owner_user_id: int = 0

    # Target group chat ID (all interactions happen here)
    target_group_chat_id: int = 0

    # Base download path inside container
    download_base_path: str = "/downloads"

    # qBittorrent Web API
    # ⚠️ 务必在 .env 中修改密码，不要使用默认值
    qb_url: str = "http://qbittorrent:8080"
    qb_username: str = "admin"
    qb_password: str = ""  # 无默认值，强制用户配置

    # Session file path
    session_path: str = "/app/sessions/user"


def load_config() -> Config:
    """Load configuration from .env file and environment variables."""
    load_dotenv()

    cfg = Config(
        run_mode=os.getenv("RUN_MODE", "user"),
        api_id=_get_int("TELEGRAM_API_ID", 0),
        api_hash=os.getenv("TELEGRAM_API_HASH", ""),
        phone_number=os.getenv("PHONE_NUMBER", ""),
        bot_token=os.getenv("BOT_TOKEN"),
        owner_user_id=_get_int("OWNER_USER_ID", 0),
        target_group_chat_id=_get_int("TARGET_GROUP_CHAT_ID", 0),
        download_base_path=os.getenv("DOWNLOAD_BASE_PATH", "/downloads"),
        qb_url=os.getenv("QBITTORRENT_URL", "http://qbittorrent:8080"),
        qb_username=os.getenv("QBITTORRENT_USERNAME", "admin"),
        qb_password=os.getenv("QBITTORRENT_PASSWORD", ""),
    )

    # Warn if qBittorrent password uses the default
    if not cfg.qb_password:
        logger.warning(
            "QBITTORRENT_PASSWORD is not set! qBittorrent login may fail. "
            "Set it in your .env file."
        )

    return cfg


def _get_int(key: str, default: int) -> int:
    """Get an environment variable as an integer."""
    val = os.getenv(key)
    if val is None or val.strip() == "":
        return default
    try:
        return int(val.strip())
    except ValueError:
        logger.warning("Invalid integer value for %s='%s', falling back to %s", key, val, default)
        return default
