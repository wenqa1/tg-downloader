"""
Abstract base class for notification sending.
Supports both Bot API and Telethon user-account notification.
"""

from abc import ABC, abstractmethod


class BaseNotifier(ABC):
    """Abstract notifier interface."""

    @abstractmethod
    async def send(self, text: str, parse_mode: str = "markdown") -> None:
        """Send a notification to the owner."""
        ...

    @abstractmethod
    async def send_to_chat(self, chat_id: int, text: str, parse_mode: str = "markdown") -> None:
        """Send a message to a specific chat."""
        ...
