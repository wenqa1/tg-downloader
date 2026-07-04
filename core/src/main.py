"""
TG Downloader Bot - Main Entry Point

Starts the Telegram download bot in either "user" or "bot" mode.
For now, only "user" mode is implemented.

Usage:
    python -m src.main              # Uses .env file in CWD
    RUN_MODE=user python -m src.main
"""

import asyncio
import logging
import os
import signal
import sys
from logging.handlers import RotatingFileHandler

from telethon import TelegramClient

from config import load_config
from config import Config
from handlers.command_handler import handle_command
from handlers.file_handler import handle_file
from handlers.magnet_handler import handle_magnet
from notifiers.user_notifier import UserNotifier
from receivers.user_receiver import UserReceiver
from downloaders.qb_client import QBittorrentClient

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
_LOG_DIR = "/app/logs"
_LOG_FILE = os.path.join(_LOG_DIR, "bot.log")
_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"


def _setup_logging() -> None:
    """Configure logging to both file (rotating) and stdout."""
    os.makedirs(_LOG_DIR, exist_ok=True)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # File handler with rotation (10 MB per file, keep 5)
    file_handler = RotatingFileHandler(
        _LOG_FILE, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(logging.Formatter(_LOG_FORMAT))
    root_logger.addHandler(file_handler)

    # Stdout handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter(_LOG_FORMAT))
    root_logger.addHandler(console_handler)

    # Quieter logs from third-party libs
    logging.getLogger("telethon").setLevel(logging.WARNING)


logger = logging.getLogger("tg-downloader")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
async def _run_user_mode(config: Config) -> None:
    """Start the bot in user mode (Telethon user account)."""
    logger.info("Starting in USER mode (Telethon user account)...")

    # Validate required config
    if not config.api_id or not config.api_hash:
        logger.error(
            "TELEGRAM_API_ID and TELEGRAM_API_HASH are required.\n"
            "Get them from https://my.telegram.org"
        )
        sys.exit(1)

    # Create shared Telethon client
    client = TelegramClient(
        session=config.session_path,
        api_id=config.api_id,
        api_hash=config.api_hash,
        # Retry on connection issues
        connection_retries=5,
        # Timeout settings
        timeout=30,
    )

    # Initialize services
    notifier = UserNotifier(client, config.owner_user_id)

    qb_client = QBittorrentClient(
        base_url=config.qb_url,
        username=config.qb_username,
        password=config.qb_password,
    )

    # Check qBittorrent connectivity (non-blocking, log warning if unavailable)
    try:
        qb_alive = await qb_client.is_alive()
        if qb_alive:
            logger.info("✅ qBittorrent Web API is accessible")
        else:
            logger.warning("⚠️ qBittorrent Web API is not accessible yet (will retry)")
    except Exception:
        logger.warning("⚠️ qBittorrent check failed (will retry on first use)")

    # Create receiver and register handlers
    receiver = UserReceiver(
        client=client,
        config=config,
        notifier=notifier,
        qb_client=qb_client,
    )

    # Register handlers (order matters: file before magnet for .torrent files)
    receiver.register_handler(handle_file)
    receiver.register_handler(handle_magnet)
    receiver.register_handler(handle_command)

    # Handle graceful shutdown
    shutdown_event = asyncio.Event()

    def _signal_handler():
        logger.info("Shutdown signal received, closing gracefully...")
        shutdown_event.set()

    # Set up signal handlers (works on Unix; on Windows we handle Ctrl+C)
    try:
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, _signal_handler)
            except NotImplementedError:
                pass  # Windows doesn't support add_signal_handler
    except Exception:
        pass

    try:
        # Start listening (blocks until disconnected)
        await receiver.start()
    except asyncio.CancelledError:
        logger.info("Task cancelled, shutting down...")
    finally:
        await qb_client.close()
        await client.disconnect()
        logger.info("Shutdown complete")


async def _run_bot_mode(config: Config) -> None:
    """Start the bot in bot mode (aiogram + Telethon)."""
    logger.error("Bot mode is not yet implemented. Set RUN_MODE=user or wait for future updates.")
    sys.exit(1)


async def _main() -> None:
    """Parse config and dispatch to the appropriate mode."""
    _setup_logging()

    logger.info("=" * 50)
    logger.info("TG Downloader Bot starting...")
    logger.info("=" * 50)

    config = load_config()

    logger.info(f"Run mode: {config.run_mode}")
    logger.info(f"Session path: {config.session_path}")
    logger.info(f"Download path: {config.download_base_path}")

    if config.run_mode == "user":
        await _run_user_mode(config)
    elif config.run_mode == "bot":
        await _run_bot_mode(config)
    else:
        logger.error(f"Unknown RUN_MODE: {config.run_mode}. Must be 'user' or 'bot'.")
        sys.exit(1)


def main() -> None:
    """Entry point with asyncio handling."""
    try:
        asyncio.run(_main())
    except KeyboardInterrupt:
        logger.info("Received KeyboardInterrupt, exiting...")
    except Exception as e:
        logger.critical(f"Unhandled exception: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
