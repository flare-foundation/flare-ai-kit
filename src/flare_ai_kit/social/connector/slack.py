"""Slack Connector for Flare AI Kit."""

import logging
from typing import Any

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from flare_ai_kit.config import AppSettings
from flare_ai_kit.social.connector import SocialConnector

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class SlackConnector(SocialConnector):
    """Slack Connector for Flare AI Kit."""

    def __init__(self, client: WebClient | None) -> None:
        """Initialize the SlackConnector with API token and channel ID."""
        settings = AppSettings().social
        self.token = (
            settings.slack_bot_token.get_secret_value()
            if settings.slack_bot_token
            else ""
        )
        self.channel_id = (
            settings.slack_channel_id.get_secret_value()
            if settings.slack_channel_id
            else ""
        )
        self.client: WebClient = client or WebClient(token=self.token)

    @property
    def platform(self) -> str:
        """Return the platform name."""
        return "slack"

    async def fetch_mentions(
        self, query: str = "", limit: int = 10
    ) -> list[dict[str, Any]]:
        """Fetch messages from Slack channel that match the query."""
        if not self.token or not self.channel_id:
            return []

        try:
            response = self.client.conversations_history(  # type: ignore[reportUnknownMemberType]
                channel=self.channel_id,
                limit=100,
            )
            messages = response.get("messages", [])

            results = [
                {
                    "platform": self.platform,
                    "content": msg.get("text", ""),
                    "author_id": msg.get("user", ""),
                    "timestamp": msg.get("ts", ""),
                }
                for msg in messages
                if query.lower() in msg.get("text", "").lower()
            ]

            return results[-limit:]
        except SlackApiError:
            logger.exception("Slack connector error: %s")
            return []

    def post_message(self, content: str) -> dict[str, Any]:
        """Post a message to the Slack channel."""
        try:
            result = self.client.chat_postMessage(  # type: ignore[reportUnknownMemberType]
                channel=self.channel_id, text=content
            )
            return {
                "platform": "slack",
                "message_ts": result["ts"],
                "content": content,
            }
        except SlackApiError as e:
            return {"error": str(e)}
