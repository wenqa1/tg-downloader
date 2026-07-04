"""
User-mode receiver - listens for new messages in the target group
using the Telethon user account client.
"""

import getpass
import logging
import sys
from typing import Callable, List

from telethon import TelegramClient, events
from telethon.errors import (
    PhoneCodeInvalidError,
    SessionPasswordNeededError,
    FloodWaitError,
)

from config import Config
from notifiers.base import BaseNotifier
from receivers.base import BaseReceiver

logger = logging.getLogger("tg-downloader.receiver")

# Type alias for a message handler function
HandlerFunc = Callable


class UserReceiver(BaseReceiver):
    """
    Receives messages via Telethon user client in the target group.
    Routes incoming messages to registered handler functions.
    """

    def __init__(
        self,
        client: TelegramClient,
        config: Config,
        notifier: BaseNotifier,
        qb_client,
    ):
        self.client = client
        self.config = config
        self.notifier = notifier
        self.qb_client = qb_client
        self.handlers: List[HandlerFunc] = []
        self._me = None  # Cached self info (set during start)

    def register_handler(self, handler: HandlerFunc) -> None:
        """Register a message handler function."""
        self.handlers.append(handler)

    async def start(self) -> None:
        """Start the Telethon client and begin listening for messages."""
        # Step 1: Authenticate
        await self._authenticate()

        # Step 2: Get self info (cache for later use)
        self._me = await self.client.get_me()
        logger.info(f"✅ Logged in as: {self._me.first_name} (ID: {self._me.id})")
        if self._me.username:
            logger.info(f"   Username: @{self._me.username}")

        # Step 2b: Validate OWNER_USER_ID
        if not self.config.owner_user_id:
            logger.critical(
                "OWNER_USER_ID is not set! The bot will reject all messages.\n"
                "Get your User ID from @userinfobot and set it in .env"
            )
            sys.exit(1)

        # Step 3: Verify target group exists
        await self._verify_target_group()

        # Step 4: Notify owner that bot is online
        await self._notify_online()

        # Step 5: Register event handler (filter by chat ID manually for reliability)
        @self.client.on(events.NewMessage)
        async def message_handler(event) -> None:
            # Only process messages from the target group
            if event.chat_id != self.config.target_group_chat_id:
                return
            await self._on_message(event)

        logger.info(
            f"👂 Listening for messages in chat {self.config.target_group_chat_id}..."
        )
        logger.info("Waiting for messages... (Press Ctrl+C to stop)")

        # Step 6: Keep running
        await self.client.run_until_disconnected()

    async def _authenticate(self) -> None:
        """Handle Telethon authentication with session persistence.

        First run: prompts for verification code via stdin (works with docker attach).
        Subsequent runs: uses saved session file automatically.
        """
        client = self.client
        phone = self.config.phone_number or None

        # Custom code callback for better Docker-first-run UX
        def code_callback() -> str:
            try:
                if sys.stdin.isatty():
                    print("\n🔐 Enter the verification code: ", end="", flush=True)
                else:
                    logger.critical(
                        "❌ Verification code required but no interactive terminal.\n"
                        "  Run:  docker attach tg-downloader\n"
                        "  Then enter the code sent to your Telegram."
                    )
                return sys.stdin.readline().strip()
            except EOFError:
                logger.critical(
                    "❌ Cannot read verification code.\n"
                    "  Run: docker attach tg-downloader\n"
                    "  Then restart the container with: docker-compose restart tg-downloader"
                )
                raise

        try:
            await client.start(
                phone=phone,
                code_callback=code_callback,
            )
        except PhoneCodeInvalidError:
            logger.error("❌ Invalid verification code. Restart and try again.")
            sys.exit(1)
        except SessionPasswordNeededError:
            # 2FA enabled - prompt for password (no echo)
            if sys.stdin.isatty():
                password = getpass.getpass("🔐 Enter your 2FA password: ")
            else:
                logger.critical(
                    "❌ 2FA password required but no interactive terminal.\n"
                    "  Run: docker attach tg-downloader"
                )
                sys.exit(1)
            await client.sign_in(password=password)
        except FloodWaitError as e:
            logger.error(f"❌ Rate limited by Telegram. Wait {e.seconds} seconds before retrying.")
            sys.exit(1)

    async def _verify_target_group(self) -> None:
        """Verify the target group exists and log available chats."""
        chat_id = self.config.target_group_chat_id

        if not chat_id:
            logger.warning("⚠️ TARGET_GROUP_CHAT_ID not configured!")
            logger.info("Available chats (send a message here to find the ID you need):")
            await self._list_dialogs()
            return

        try:
            entity = await self.client.get_entity(chat_id)
            logger.info(f"📋 Monitoring group: {getattr(entity, 'title', 'Unknown')} (ID: {chat_id})")
        except ValueError:
            logger.warning(
                f"⚠️ Cannot find group with ID {chat_id}. "
                f"The account may not be a member, or the ID is wrong."
            )
            logger.info("Available chats:")
            await self._list_dialogs()

    async def _list_dialogs(self) -> None:
        """Print all dialogs (chats/groups) the account is in."""
        try:
            async for dialog in self.client.iter_dialogs(limit=30):
                logger.info(
                    f"  • {dialog.name}: ID = {dialog.id} "
                    f"(Type: {dialog.entity.__class__.__name__})"
                )
        except Exception as e:
            logger.error(f"Failed to list dialogs: {e}")

    async def _notify_online(self) -> None:
        """Send a startup notification to the owner."""
        try:
            name = self._me.first_name or "TG Downloader"
            await self.notifier.send(
                f"🟢 *{name} 已启动*\n"
                f"运行模式: `{self.config.run_mode}`\n"
                f"群组 ID: `{self.config.target_group_chat_id}`\n"
                f"发送 `help` 查看可用命令"
            )
        except Exception as e:
            logger.warning(f"Failed to send startup notification: {e}")

    async def _on_message(self, event) -> None:
        """Process an incoming message through all registered handlers."""
        msg = event.message
        sender_id = event.sender_id

        # Skip own messages to avoid loops
        if self._me and sender_id == self._me.id:
            return

        # Whitelist check
        if sender_id != self.config.owner_user_id:
            logger.warning(f"Unauthorized user {sender_id} sent a message, ignoring")
            await self.notifier.send(
                f"⚠️ 未授权的用户 (ID: `{sender_id}`) 尝试使用机器人\n"
                f"消息已忽略，如需授权请添加到 OWNER_USER_ID"
            )
            return

        logger.debug(f"Processing message {msg.id} from {sender_id}")

        # Run through all registered handlers
        for handler in self.handlers:
            try:
                await handler(
                    event,
                    self.client,
                    self.config,
                    self.notifier,
                    self.qb_client,
                )
            except Exception as e:
                logger.error(
                    f"Handler {handler.__name__} error on msg {msg.id}: {e}",
                    exc_info=True,
                )
                await self.notifier.send(
                    f"❌ *处理消息时出错*\n消息 ID: `{msg.id}`\n错误: {str(e)[:200]}"
                )
