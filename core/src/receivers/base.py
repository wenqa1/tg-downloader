"""
Abstract base class for message receivers.
Supports both Bot API (aiogram) and user-mode (Telethon) receiving.
"""

from abc import ABC, abstractmethod
from typing import Callable, List


class BaseReceiver(ABC):
    """Abstract receiver interface for incoming Telegram messages."""

    @abstractmethod
    def register_handler(self, handler: Callable) -> None:
        """Register a handler function for incoming messages."""
        ...

    @abstractmethod
    async def start(self) -> None:
        """Start listening for messages (blocks until interrupted)."""
        ...
