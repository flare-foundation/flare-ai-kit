from unittest.mock import AsyncMock, MagicMock

import pytest

from flare_ai_kit.social.connector import SocialConnector
from flare_ai_kit.social.connector.discord import DiscordConnector


@pytest.fixture(autouse=True)
def set_env(monkeypatch):
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "fake-token")
    monkeypatch.setenv("DISCORD_GUILD_ID", "123456")
    monkeypatch.setenv("DISCORD_CHANNEL_ID", "654321")


def test_inherits_base_class():
    connector = DiscordConnector()
    connector.client.start = AsyncMock(return_value=None)

    assert isinstance(connector, SocialConnector)
    assert connector.platform == "discord"


@pytest.mark.asyncio
async def test_fetch_mentions_filters_query(monkeypatch):
    connector = DiscordConnector()
    connector.client.start = AsyncMock(return_value=None)

    connector._ready_event.set()  # simulate client ready

    # Inject fake messages
    connector._messages = [
        {
            "content": "Flare rocks!",
            "platform": "discord",
            "author_id": "1",
            "timestamp": "now",
        },
        {
            "content": "Totally unrelated",
            "platform": "discord",
            "author_id": "2",
            "timestamp": "now",
        },
    ]

    results = await connector.fetch_mentions("flare")
    assert len(results) == 1
    assert "Flare rocks" in results[0]["content"]


@pytest.mark.asyncio
async def test_fetch_mentions_limit(monkeypatch):
    connector = DiscordConnector()
    connector.client.start = AsyncMock(return_value=None)

    connector._ready_event.set()

    connector._messages = [
        {
            "content": f"msg {i}",
            "platform": "discord",
            "author_id": f"{i}",
            "timestamp": "now",
        }
        for i in range(15)
    ]

    results = await connector.fetch_mentions("msg", limit=5)
    assert len(results) == 5
    assert results[-1]["content"] == "msg 14"


@pytest.mark.asyncio
async def test_on_message_stores_message():
    connector = DiscordConnector()
    connector.client.start = AsyncMock(return_value=None)

    connector._ready_event.set()

    mock_message = MagicMock()
    mock_message.channel.id = connector.channel_id
    mock_message.author.bot = False
    mock_message.author.id = 999
    mock_message.content = "Hello from test"
    mock_message.created_at.isoformat.return_value = "now"

    await connector._on_message(mock_message)

    assert any("Hello from test" in m["content"] for m in connector._messages)
    await connector.client.close()
