"""Telegram Connector for Flare AI Kit."""

import logging
import os
import asyncio

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, MessageHandler, filters

from flare_ai_kit.social.connector import SocialConnector

load_dotenv()

logging.getLogger("httpx").setLevel(logging.WARNING)


class TelegramConnector(SocialConnector):
    """Telegram Connector for Flare AI Kit."""

    def __init__(self) -> None:
        self.token = os.getenv("SOCIAL__TELEGRAM_BOT_TOKEN")
        self.chat_id = os.getenv("SOCIAL__TELEGRAM_CHAT_ID")

        self._messages: list[dict] = []

        self.app = Application.builder().token(self.token).build()

        self.app.add_handler(
            MessageHandler(filters.TEXT & (~filters.COMMAND), self._on_message)
        )

    @property
    def platform(self) -> str:
        """Return the platform name."""
        return "telegram"

    async def fetch_mentions(self, query: str = "", limit: int = 10) -> list[dict]:
        """Starts polling and filters collected messages by query."""

        await self.app.initialize()
        await self.app.start()
        await asyncio.sleep(1)  # collect messages
        await self.app.stop()
        await self.app.shutdown()

        filtered = [
            msg for msg in self._messages if query.lower() in msg["content"].lower()
        ]
        return filtered[-limit:]

    async def _on_message(self, update: Update) -> None:
        message = update.message
        if message and message.chat and str(message.chat.id) == str(self.chat_id):
            self._messages.append(
                {
                    "platform": "telegram",
                    "content": message.text,
                    "author_id": str(message.from_user.id),
                    "timestamp": message.date.isoformat(),
                }
            )
