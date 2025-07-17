"""Client for interacting with the Telegram Bot API using python-telegram-bot."""

import structlog
from telegram.error import TelegramError
from telegram.ext import Application

from flare_ai_kit.social.settings import SocialSettings

logger = structlog.get_logger(__name__)


class TelegramClient:
    """A client to interact with the Telegram Bot API."""

    def __init__(self, settings: SocialSettings) -> None:
        """
        Initializes the TelegramClient.

        This sets up the application instance required to interact with the bot API.
        If the API token is missing, the client will not be configured.

        Args:
            settings: The social settings model containing the Telegram API token.

        """
        token = settings.telegram_api_token
        self.application: Application | None = None  # pyright: ignore[reportMissingTypeArgument]
        self.is_configured = False

        if token:
            try:
                self.application = (
                    Application.builder().token(token.get_secret_value()).build()
                )
                self.is_configured = True
                logger.info("TelegramClient initialized and configured.")
            except Exception as e:
                logger.exception("Failed to initialize Telegram Application", error=e)
        else:
            logger.warning(
                "TelegramClient is not configured due to missing API token. "
                "API calls will be simulated."
            )

    async def send_message(self, chat_id: str, text: str) -> bool:
        """
        Sends a message to a Telegram chat.

        This is an asynchronous operation.

        Args:
            chat_id: The unique identifier for the target chat
                (e.g., '@channelname' or a user ID).
            text: The text of the message to send.

        Returns:
            True if the message was sent successfully, False otherwise.

        """
        if not self.is_configured or not self.application:  # pyright: ignore[reportUnknownMemberType]
            logger.info(
                "Simulating Telegram message because client is not configured.",
                text=text,
            )
            return True  # Simulate success

        if not chat_id or not text:
            logger.error("chat_id and text must be non-empty strings.")
            return False

        logger.info("Sending message", chat_id=chat_id)
        try:
            await self.application.bot.send_message(chat_id=chat_id, text=text)  # pyright: ignore[reportUnknownMemberType]
        except TelegramError as e:
            logger.exception(
                "Failed to send Telegram message due to an API error.",
                chat_id=chat_id,
                error=e,
            )
            return False
        except Exception as e:
            logger.exception(
                "An unexpected error occurred while sending a Telegram message.",
                chat_id=chat_id,
                error=e,
            )
            return False
        else:
            logger.info("Message sent successfully.", chat_id=chat_id)
            return True
