"""
TG Downloader Bot - Main Entry Point

Starts the Telegram download bot and the web management interface
in the same process. The web server runs in a background asyncio task.

Usage:
    python src/main.py                  # Normal start
    python src/main.py --web-only       # Web server only (debug)
    python src/main.py --bot-only       # Bot only (debug)
"""

import asyncio
import logging
import os
import signal
import sys
from logging.handlers import RotatingFileHandler
from typing import Optional

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
async def _run_user_mode(config: Config) -> bool:
    """
    Start the bot in user mode (Telethon user account).

    Returns True if the bot ran successfully, False if config is missing.
    Does NOT exit the process — the web server continues running.
    """
    logger.info("Starting in USER mode (Telethon user account)...")

    # Validate required config — log error but DON'T exit (web UI must stay up)
    if not config.api_id or not config.api_hash:
        logger.error(
            "TELEGRAM_API_ID and TELEGRAM_API_HASH are not configured.\n"
            "  Go to the Web UI → Settings to configure them.\n"
            "  Bot will retry on next restart."
        )
        return False

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

    # Handle graceful shutdown — signal handler directly disconnects
    # the client, which causes run_until_disconnected() to return.
    shutdown_task: Optional[asyncio.Task] = None

    def _signal_handler():
        nonlocal shutdown_task
        logger.info("Shutdown signal received, closing gracefully...")
        # Schedule disconnect on the event loop to unblock run_until_disconnected
        if shutdown_task is None or shutdown_task.done():
            shutdown_task = asyncio.create_task(client.disconnect())

    # Set up signal handlers (works on Unix; on Windows we handle Ctrl+C)
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _signal_handler)
        except (NotImplementedError, RuntimeError):
            pass  # Windows or not in main loop

    try:
        # Start listening (blocks until disconnected)
        await receiver.start()
    except asyncio.CancelledError:
        logger.info("Task cancelled, shutting down...")
    finally:
        await qb_client.close()
        await client.disconnect()
        logger.info("Shutdown complete")

    return True


async def _run_bot_mode(config: Config) -> bool:
    """Start the bot in bot mode (aiogram + Telethon). Not yet implemented."""
    logger.error(
        "Bot mode is not yet implemented. "
        "Go to Web UI → Settings and switch to User mode."
    )
    return False


async def _start_web_server(host: str = "0.0.0.0", port: int = 8081) -> None:
    """Start the FastAPI web server in a background asyncio task."""
    import uvicorn
    from web.server import app

    cfg = uvicorn.Config(
        app,
        host=host,
        port=port,
        log_level="info",
        # Suppress uvicorn's own startup logs for cleaner output
        access_log=False,
    )
    server = uvicorn.Server(cfg)
    logger.info("🌐 Web management interface starting on http://%s:%s", host, port)
    await server.serve()


async def _main() -> None:
    """Parse config, start web server first, then start bot if configured."""
    _setup_logging()

    logger.info("=" * 50)
    logger.info("TG Downloader Bot starting...")
    logger.info("=" * 50)

    config = load_config()

    logger.info("Run mode: %s", config.run_mode)
    logger.info("Session path: %s", config.session_path)
    logger.info("Download path: %s", config.download_base_path)

    # Parse CLI flags for debug modes
    cli_args = set(sys.argv[1:])
    web_only = "--web-only" in cli_args
    bot_only = "--bot-only" in cli_args

    web_port = int(os.getenv("WEB_PORT", "8081"))
    web_host = os.getenv("WEB_HOST", "0.0.0.0")

    # ═══════════════════════════════════════════════════════════════
    # Step 1: Start web server FIRST (always, even if bot fails)
    # ═══════════════════════════════════════════════════════════════
    if not bot_only:
        web_task = asyncio.create_task(_start_web_server(web_host, web_port))
        # Give web server a moment to start
        await asyncio.sleep(0.5)
    else:
        web_task = None

    if web_only:
        # Web server only mode — wait forever
        await web_task
        return

    # ═══════════════════════════════════════════════════════════════
    # Step 2: Start bot (non-fatal if config is missing)
    # ═══════════════════════════════════════════════════════════════
    if config.run_mode == "user":
        bot_ok = await _run_user_mode(config)
    elif config.run_mode == "bot":
        bot_ok = await _run_bot_mode(config)
    else:
        logger.error("Unknown RUN_MODE: %s. Must be 'user' or 'bot'.", config.run_mode)
        bot_ok = False

    # ═══════════════════════════════════════════════════════════════
    # Step 3: Bot finished — keep web server running
    # ═══════════════════════════════════════════════════════════════
    if web_task is not None and not web_task.done():
        if not bot_ok:
            logger.info(
                "Bot is not running (config may be incomplete).\n"
                "  Web UI is still available at http://localhost:%s\n"
                "  Go to Settings to configure API credentials, then restart.",
                web_port,
            )
        else:
            logger.info("Bot has stopped. Web UI remains available.")

        # Keep the process alive for the web server
        await web_task


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
