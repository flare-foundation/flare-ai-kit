"""Telegram Connector for Flare AI Kit."""

import logging
from typing import Any

import structlog
from telegram import Update
from telegram.ext import Application, ContextTypes, MessageHandler, filters

from flare_ai_kit.config import AppSettings
from flare_ai_kit.social.connector import SocialConnector

logging.getLogger("httpx").setLevel(logging.WARNING)
logger = structlog.get_logger(__name__)


class TelegramConnector(SocialConnector):
    """Telegram Connector for Flare AI Kit."""

    def __init__(self) -> None:
        """Initialize the TelegramConnector with API token and chat ID."""
        settings = AppSettings().social
        self.token = (
            settings.telegram_bot_token.get_secret_value()
            if settings.telegram_bot_token
            else ""
        )
        self.chat_id = (
            settings.telegram_chat_id.get_secret_value()
            if settings.telegram_chat_id
            else ""
        )

        self.is_configured = False
        self._messages: list[dict[str, Any]] = []
        self.app = Application

        if self.token:
            try:
                self.app = Application.builder().token(self.token).build()
                self.is_configured = True
                self.app.add_handler(
                    MessageHandler(filters.TEXT & (~filters.COMMAND), self._on_message)
                )
                logger.info("TelegramClient initialized and configured.")
            except Exception as e:
                logger.exception("Failed to initialize Telegram Application", error=e)
        else:
            logger.warning(
                "TelegramClient is not configured due to missing API token. "
                "API calls will be simulated."
            )

    @property
    def platform(self) -> str:
        """Return the platform name."""
        return "telegram"

    async def fetch_mentions(
        self, query: str = "", limit: int = 10
    ) -> list[dict[str, Any]]:
        """Method to fetch mentions."""
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
