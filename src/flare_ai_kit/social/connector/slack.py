"""Slack Connector for Flare AI Kit."""

import logging
import os
from typing import Any

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from flare_ai_kit.social.connector import SocialConnector

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class SlackConnector(SocialConnector):
    """Slack Connector for Flare AI Kit."""

    def __init__(self, client: WebClient | None = None) -> None:
        self.token = os.getenv("SLACK_BOT_TOKEN")
        self.channel_id = os.getenv("SLACK_CHANNEL_ID")
        self.client = client or WebClient(token=self.token)

    @property
    def platform(self) -> str:
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
        except SlackApiError as e:
            logger.exception("Slack connector error: %s", e)
            return []
