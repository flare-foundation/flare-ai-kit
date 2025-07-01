""""# Slack Connector for Flare AI Kit."""

import logging
import os

from dotenv import load_dotenv
from slack_sdk import WebClient

from flare_ai_kit.social.connector import SocialConnector

load_dotenv()

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)


class SlackConnector(SocialConnector):
    """Slack Connector for Flare AI Kit."""

    def __init__(self) -> None:
        self.token = os.getenv("SLACK_BOT_TOKEN")
        self.channel_id = os.getenv("SLACK_CHANNEL_ID")
        self.client = WebClient(token=self.token)

    @property
    def platform(self) -> str:
        """Return the platform name."""
        return "slack"

    async def fetch_mentions(self, query: str = "", limit: int = 10) -> list[dict]:
        """Fetch messages from Slack channel that match the query."""
        try:
            response = self.client.conversations_history(
                channel=self.channel_id, limit=100
            )
            messages = response.get("messages", [])

            results = [
                {
                    "platform": "slack",
                    "content": msg.get("text", ""),
                    "author_id": msg.get("user", ""),
                    "timestamp": msg.get("ts", ""),
                }
                for msg in messages
                if query.lower() in msg.get("text", "").lower()
            ]

            return results[-limit:]
        except Exception:
            logger.exception("Slack connector error")
            return []
