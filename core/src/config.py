"""
Configuration module for TG Downloader Bot.

Loads settings from environment variables (via .env file)
and provides a typed Config dataclass.
"""

import json
import logging
import os
from dataclasses import dataclass, field
from typing import Optional

from dotenv import load_dotenv

logger = logging.getLogger("tg-downloader.config")

# Path to runtime settings file (mounted volume, writable via Web UI)
SETTINGS_FILE = "/app/settings/settings.json"


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
    # ⚠️ 务必修改密码，不要使用默认值
    qb_url: str = "http://qbittorrent:8080"
    qb_username: str = "admin"
    qb_password: str = ""  # 无默认值，强制用户配置

    # Session file path
    session_path: str = "/app/sessions/user"


def load_settings_file() -> dict:
    """
    Load runtime settings from settings.json (if it exists).

    Returns a dict that can override Config fields.
    The file is written by the Web UI settings page.
    """
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            logger.info("Loaded runtime settings from %s", SETTINGS_FILE)
            return data
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Failed to load %s: %s", SETTINGS_FILE, e)
    return {}


def build_config_from_env() -> Config:
    """Build Config from environment variables (highest priority)."""
    return Config(
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


def apply_file_overrides(cfg: Config, overrides: dict) -> Config:
    """
    Apply settings from file to Config, only for fields that are
    NOT set via environment variables.

    This ensures .env always takes priority over the web UI settings.
    """
    # Map of settings.json keys → Config field names
    key_map = {
        "telegram_api_id": "api_id",
        "telegram_api_hash": "api_hash",
        "phone_number": "phone_number",
        "owner_user_id": "owner_user_id",
        "target_group_chat_id": "target_group_chat_id",
        "qb_url": "qb_url",
        "qb_username": "qb_username",
        "qb_password": "qb_password",
    }

    for file_key, field_name in key_map.items():
        if file_key not in overrides:
            continue
        file_value = overrides[file_key]

        # Only apply if env var is NOT set (empty / default)
        env_key = {
            "api_id": "TELEGRAM_API_ID",
            "api_hash": "TELEGRAM_API_HASH",
            "phone_number": "PHONE_NUMBER",
            "owner_user_id": "OWNER_USER_ID",
            "target_group_chat_id": "TARGET_GROUP_CHAT_ID",
            "qb_url": "QBITTORRENT_URL",
            "qb_username": "QBITTORRENT_USERNAME",
            "qb_password": "QBITTORRENT_PASSWORD",
        }.get(field_name)

        # Skip if env var is explicitly set
        if env_key and os.getenv(env_key):
            continue

        # Apply the file value
        current = getattr(cfg, field_name)
        if file_value is not None and file_value != "" and file_value != 0 and file_value != current:
            # Convert type to match the field
            target_type = type(getattr(Config, field_name, type(file_value)))
            if target_type == int and not isinstance(file_value, int):
                try:
                    file_value = int(file_value)
                except (ValueError, TypeError):
                    continue
            setattr(cfg, field_name, file_value)

    return cfg


def load_config() -> Config:
    """Load configuration from env vars (highest priority) with file overrides."""
    load_dotenv()

    cfg = build_config_from_env()

    # Apply settings from file (lower priority than env vars)
    file_settings = load_settings_file()
    if file_settings:
        cfg = apply_file_overrides(cfg, file_settings)

    # Warn if qBittorrent password is missing
    if not cfg.qb_password:
        logger.warning(
            "QBITTORRENT_PASSWORD is not set! qBittorrent login may fail. "
            "Set it in .env or via Web UI settings page."
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
