"""
User-mode notifier - sends notifications via the Telethon user account.
"""

import logging

from telethon import TelegramClient

from notifiers.base import BaseNotifier

logger = logging.getLogger("tg-downloader.notifier")


class UserNotifier(BaseNotifier):
    """Sends notifications using the Telethon user client."""

    def __init__(self, client: TelegramClient, owner_id: int):
        self.client = client
        self.owner_id = owner_id

    async def send(self, text: str, parse_mode: str = "markdown") -> None:
        """Send a notification message to the owner's DM."""
        try:
            await self.client.send_message(
                self.owner_id,
                text,
                parse_mode=parse_mode,
            )
            logger.debug(f"Notification sent to {self.owner_id}")
        except Exception as e:
            logger.error(f"Failed to send notification to {self.owner_id}: {e}")

    async def send_to_chat(self, chat_id: int, text: str, parse_mode: str = "markdown") -> None:
        """Send a message to a specific chat (e.g. the download group)."""
        try:
            await self.client.send_message(
                chat_id,
                text,
                parse_mode=parse_mode,
            )
            logger.debug(f"Message sent to chat {chat_id}")
        except Exception as e:
            logger.error(f"Failed to send message to chat {chat_id}: {e}")
