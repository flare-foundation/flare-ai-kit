"""Telegram Connector for Flare AI Kit."""

import asyncio
import logging
from typing import Any

from telegram import Update
from telegram.ext import Application, ContextTypes, MessageHandler, filters

from flare_ai_kit.config import settings
from flare_ai_kit.social.connector import SocialConnector

logging.getLogger("httpx").setLevel(logging.WARNING)


class TelegramConnector(SocialConnector):
    """Telegram Connector for Flare AI Kit."""

    def __init__(self) -> None:
        """Initialize the TelegramConnector with API token and chat ID."""
        social_settings = settings.social
        self.token = (
            social_settings.telegram_bot_token.get_secret_value()
            if social_settings.telegram_bot_token
            else ""
        )
        self.chat_id = (
            social_settings.telegram_channel_id.get_secret_value()
            if social_settings.telegram_channel_id
            else ""
        )

        self._messages: list[dict[str, Any]] = []

        self.app = Application.builder().token(self.token).build()
        self.app.add_handler(
            MessageHandler(filters.TEXT & (~filters.COMMAND), self._on_message)
        )

    @property
    def platform(self) -> str:
        """Return the platform name."""
        return "telegram"

    async def fetch_mentions(
        self, query: str = "", limit: int = 10
    ) -> list[dict[str, Any]]:
        """Starts polling and filters collected messages by query."""
        await self.app.initialize()
        await self.app.start()
        await asyncio.sleep(1)
        await self.app.stop()
        await self.app.shutdown()

        filtered = [
            msg for msg in self._messages if query.lower() in msg["content"].lower()
        ]
        return filtered[-limit:]

    async def _on_message(self, update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle incoming messages."""
        message = update.message
        if (
            message
            and message.chat
            and message.text
            and message.from_user
            and str(message.chat.id) == str(self.chat_id)
        ):
            self._messages.append(
                {
                    "platform": "telegram",
                    "content": message.text,
                    "author_id": str(message.from_user.id),
                    "timestamp": message.date.isoformat(),
                }
            )
