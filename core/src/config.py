"""
Configuration module for TG Downloader Bot.

Settings priority (high → low):
  1. settings.json (Web UI) — primary, user edits via browser
  2. .env file / env vars — optional fallback for initial setup
  3. Code defaults — last resort

The Web UI settings page is the recommended way to configure everything.
Editing .env directly is only needed for the very first deployment.
"""

import json
import logging
import os
from dataclasses import dataclass, field
from typing import Optional

from dotenv import load_dotenv

logger = logging.getLogger("tg-downloader.config")

# Path to runtime settings file (persistent volume, writable via Web UI)
SETTINGS_FILE = "/app/settings/settings.json"

# Map: settings.json key → (Config field, env var name, type)
_SETTINGS_MAP = {
    "run_mode": ("run_mode", "RUN_MODE", str),
    "telegram_api_id": ("api_id", "TELEGRAM_API_ID", int),
    "telegram_api_hash": ("api_hash", "TELEGRAM_API_HASH", str),
    "phone_number": ("phone_number", "PHONE_NUMBER", str),
    "bot_token": ("bot_token", "BOT_TOKEN", str),
    "owner_user_id": ("owner_user_id", "OWNER_USER_ID", int),
    "target_group_chat_id": ("target_group_chat_id", "TARGET_GROUP_CHAT_ID", int),
    "qb_url": ("qb_url", "QBITTORRENT_URL", str),
    "qb_username": ("qb_username", "QBITTORRENT_USERNAME", str),
    "qb_password": ("qb_password", "QBITTORRENT_PASSWORD", str),
}


@dataclass
class Config:
    """Application configuration, loaded from settings.json + env vars."""

    # Runtime mode: "user" | "bot"
    run_mode: str = "user"

    # Telegram API credentials (required)
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

    # qBittorrent Web API (user provides their own)
    qb_url: str = ""
    qb_username: str = ""
    qb_password: str = ""

    # Session file path
    session_path: str = "/app/sessions/user"


# ---------------------------------------------------------------------------
# Settings file I/O (shared with web server)
# ---------------------------------------------------------------------------

def read_settings_file() -> dict:
    """Read settings from JSON file. Returns empty dict if not exists/corrupt."""
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Failed to read %s: %s", SETTINGS_FILE, e)
    return {}


def write_settings_file(data: dict) -> bool:
    """Write settings to JSON file. Returns True on success."""
    try:
        os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except OSError as e:
        logger.error("Failed to write settings: %s", e)
        return False


# ---------------------------------------------------------------------------
# Config building
# ---------------------------------------------------------------------------

def _coerce(value, target_type):
    """Coerce a value to the target type."""
    if value is None or value == "":
        return None
    if target_type == int:
        try:
            return int(value)
        except (ValueError, TypeError):
            return None
    return str(value)


def load_config() -> Config:
    """
    Load configuration.

    Priority (high → low):
      1. settings.json (Web UI) — primary config source
      2. .env file — optional override / initial bootstrap
      3. Code defaults
    """
    load_dotenv()

    # Start with defaults
    cfg = Config()

    # Layer 1: settings.json (highest priority for UI-managed fields)
    file_settings = read_settings_file()
    for file_key, (field_name, env_key, val_type) in _SETTINGS_MAP.items():
        # settings.json value
        file_val = file_settings.get(file_key)

        # env var override (for initial bootstrap)
        env_val = os.getenv(env_key)

        # Use env var if set, otherwise file value
        raw = env_val if env_val else file_val
        if raw is not None and raw != "":
            coerced = _coerce(raw, val_type)
            if coerced is not None:
                setattr(cfg, field_name, coerced)

    # Non-configurable paths (always from fixed locations)
    cfg.download_base_path = os.getenv("DOWNLOAD_BASE_PATH", "/downloads")
    cfg.session_path = "/app/sessions/user"

    return cfg
