"""Discord Connector for Flare AI Kit."""

import asyncio
from typing import Any

from discord import Client, Intents, Message, TextChannel

from flare_ai_kit.config import AppSettings
from flare_ai_kit.social.connector import SocialConnector


class DiscordConnector(SocialConnector):
    """Discord connector implementation."""

    def __init__(self) -> None:
        """Initialize the DiscordConnector with API token and channel ID."""
        settings = AppSettings().social
        self.token: str = (
            settings.discord_bot_token.get_secret_value()
            if settings.discord_bot_token
            else ""
        )
        self.channel_id: int = int(
            settings.discord_channel_id.get_secret_value()
            if settings.discord_channel_id
            else 0
        )
        self.client: Client = Client(intents=Intents.default())
        self._ready_event: asyncio.Event = asyncio.Event()
        self._messages: list[dict[str, Any]] = []

        # Explicitly register event handlers
        self.client.event(self._on_ready)
        self.client.event(self._on_message)

    async def _on_ready(self) -> None:
        """Handle bot ready event."""
        self._ready_event.set()

    async def _on_message(self, message: Message) -> None:
        """Handle new messages."""
        if message.author == self.client.user:
            return

        self._messages.append(
            {
                "platform": "discord",
                "content": message.content,
                "author_id": str(message.author.id),
                "timestamp": str(message.created_at),
            }
        )

    @property
    def platform(self) -> str:
        """Return the platform name."""
        return "discord"

    async def _start_if_needed(self) -> None:
        if not self.client.is_ready():
            self._client_task = asyncio.create_task(self.client.start(self.token))
            await self._ready_event.wait()

    async def fetch_mentions(
        self, query: str = "", limit: int = 10
    ) -> list[dict[str, Any]]:
        """Fetch messages that mention the query."""
        await self._start_if_needed()
        await asyncio.sleep(1)  # let messages collect

        results: list[dict[str, Any]] = []
        for msg in self._messages:
            if query.lower() in msg["content"].lower():
                results.append(msg)
                if len(results) >= limit:
                    break
        return results

    async def post_message(self, content: str) -> dict[str, Any]:
        """Post a message to the Discord channel."""
        await self._start_if_needed()
        channel = self.client.get_channel(self.channel_id)
        if isinstance(channel, TextChannel):
            message = await channel.send(content)
            return {
                "platform": "discord",
                "message_id": message.id,
                "content": message.content,
            }
        return {
            "platform": "discord",
            "message_id": None,
            "error": "Channel not found or not a text channel.",
        }
