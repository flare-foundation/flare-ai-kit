"""Telegram Connector for Flare AI Kit."""

import asyncio
import logging
import os
from typing import Any

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, ContextTypes, MessageHandler, filters

from flare_ai_kit.social.connector import SocialConnector

load_dotenv()

logging.getLogger("httpx").setLevel(logging.WARNING)


class TelegramConnector(SocialConnector):
    """Telegram Connector for Flare AI Kit."""

    def __init__(self) -> None:
        self.token = os.getenv("SOCIAL__TELEGRAM_BOT_TOKEN")
        self.chat_id = os.getenv("SOCIAL__TELEGRAM_CHAT_ID")

        if not self.token or not self.chat_id:
            raise ValueError("Telegram token or chat ID not provided")

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
        await asyncio.sleep(1)  # brief period to collect messages
        await self.app.stop()
        await self.app.shutdown()

        filtered = [
            msg for msg in self._messages if query.lower() in msg["content"].lower()
        ]
        return filtered[-limit:]

    async def _on_message(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
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
