"""Discord Connector for Flare AI Kit."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from discord import Message

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
        # Initialize client attributes without importing discord
        self.client = None
        self._ready_event: asyncio.Event = asyncio.Event()
        self._messages: list[dict[str, Any]] = []

    def _initialize_client(self) -> None:
        """Initialize Discord client with lazy import."""
        if self.client is None:
            # Lazy import and initialization of Discord client
            from discord import Client, Intents

            self.client = Client(intents=Intents.default())

            # Explicitly register event handlers
            self.client.event(self._on_ready)
            self.client.event(self._on_message)

    async def _on_ready(self) -> None:
        """Handle bot ready event."""
        self._ready_event.set()

    async def _on_message(self, message: Message) -> None:
        """Handle new messages."""
        self._initialize_client()
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
        self._initialize_client()
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
        # Check if channel is a TextChannel (lazy import)
        if channel and hasattr(channel, "send"):
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
