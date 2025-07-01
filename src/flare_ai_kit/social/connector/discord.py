"""# Discord Connector for Flare AI Kit."""

import asyncio
import os

import discord
from dotenv import load_dotenv

from flare_ai_kit.social.connector import SocialConnector

load_dotenv()


class DiscordConnector(SocialConnector):
    """Discord Connector for Flare AI Kit."""

    def __init__(self) -> None:
        self.token = os.getenv("DISCORD_BOT_TOKEN")
        self.guild_id = int(os.getenv("DISCORD_GUILD_ID"))
        self.channel_id = int(os.getenv("DISCORD_CHANNEL_ID"))

        self._messages: list[dict] = []
        self._client_task: asyncio.Task | None = None
        self._ready_event = asyncio.Event()

        intents = discord.Intents.default()
        intents.messages = True
        intents.guilds = True
        self.client = discord.Client(intents=intents)

        @self.client.event
        async def on_ready() -> None:
            self._ready_event.set()

        @self.client.event
        async def on_message(message: discord.Message) -> None:
            await self._on_message(message)

    async def _on_message(self, message: discord.Message) -> None:
        if message.channel.id == self.channel_id and not message.author.bot:
            self._messages.append(
                {
                    "platform": "discord",
                    "content": message.content,
                    "author_id": str(message.author.id),
                    "timestamp": message.created_at.isoformat(),
                }
            )

    @property
    def platform(self) -> str:
        """Return the platform name."""
        return "discord"

    async def fetch_mentions(self, query: str = "", limit: int = 10) -> list[dict]:
        """Fetch messages from Discord channel that match the query."""
        await self._start_if_needed()
        await asyncio.sleep(1)
        results = [
            msg for msg in self._messages if query.lower() in msg["content"].lower()
        ]
        return results[-limit:]

    async def _start_if_needed(self) -> None:
        if not self.client.is_ready():
            self._client_task = asyncio.create_task(self.client.start(self.token))
            await self._ready_event.wait()
