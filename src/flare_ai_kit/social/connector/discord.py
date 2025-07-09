"""Discord Connector for Flare AI Kit."""

import asyncio
import os
from typing import Any

from discord import Client, Intents, Message

from flare_ai_kit.social.connector import SocialConnector


class DiscordConnector(SocialConnector):
    """Discord connector implementation."""

    def __init__(self) -> None:
        self.token: str = os.getenv("SOCIAL__DISCORD_BOT_TOKEN") or ""
        self.channel_id: int = int(os.getenv("SOCIAL__DISCORD_CHANNEL_ID") or 0)
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

        self._messages.append({
            "platform": "discord",
            "content": message.content,
            "author_id": str(message.author.id),
            "timestamp": str(message.created_at),
        })

    @property
    def platform(self) -> str:
        """Return the platform name."""
        return "discord"

    async def _start_if_needed(self) -> None:
        if not self.client.is_ready():
            asyncio.create_task(self.client.start(self.token))
            await self._ready_event.wait()

    async def fetch_mentions(self, query: str = "", limit: int = 10) -> list[dict[str, Any]]:
        await self._start_if_needed()
        await asyncio.sleep(1)  # let messages collect

        results: list[dict[str, Any]] = []
        for msg in self._messages:
            if query.lower() in msg["content"].lower():
                results.append(msg)
                if len(results) >= limit:
                    break
        return results
