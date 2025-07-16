from unittest.mock import AsyncMock

import pytest

from flare_ai_kit.social.connector import SocialConnector
from flare_ai_kit.social.connector.discord import DiscordConnector


def test_inherits_base_class():
    connector = DiscordConnector()
    assert isinstance(connector, SocialConnector)
    assert connector.platform == "discord"


@pytest.mark.asyncio
async def test_fetch_mentions_filters_query(monkeypatch):
    connector = DiscordConnector()
    connector._messages = [
        {
            "platform": "discord",
            "content": "Flare is awesome",
            "author_id": "123",
            "timestamp": "2025-07-01T12:00:00Z",
        },
        {
            "platform": "discord",
            "content": "Other topic",
            "author_id": "456",
            "timestamp": "2025-07-01T13:00:00Z",
        },
    ]

    # Patch client.is_ready to return True
    monkeypatch.setattr(connector.client, "is_ready", lambda: True)

    results = await connector.fetch_mentions(query="flare")
    assert len(results) == 1
    assert results[0]["content"] == "Flare is awesome"


@pytest.mark.asyncio
async def test_fetch_mentions_limit(monkeypatch):
    connector = DiscordConnector()
    connector._messages = [
        {
            "platform": "discord",
            "content": "flare 1",
            "author_id": "1",
            "timestamp": "t1",
        },
        {
            "platform": "discord",
            "content": "flare 2",
            "author_id": "2",
            "timestamp": "t2",
        },
        {
            "platform": "discord",
            "content": "flare 3",
            "author_id": "3",
            "timestamp": "t3",
        },
    ]

    monkeypatch.setattr(connector.client, "is_ready", lambda: True)

    results = await connector.fetch_mentions(query="flare", limit=2)
    assert len(results) == 2


@pytest.mark.asyncio
async def test_start_if_needed_triggers_client(monkeypatch):
    connector = DiscordConnector()
    monkeypatch.setattr(connector.client, "is_ready", lambda: False)
    monkeypatch.setattr(connector.client, "start", AsyncMock())
    monkeypatch.setattr(connector._ready_event, "wait", AsyncMock())

    await connector._start_if_needed()
    connector.client.start.assert_called_once_with(connector.token)


@pytest.mark.asyncio
async def test_post_message_wrong_channel_id(monkeypatch):
    connector = DiscordConnector()
    connector._messages = []
    monkeypatch.setattr(connector.client, "is_ready", lambda: True)

    results = await connector.post_message(content="hello flare")
    assert results == {
        "platform": "discord",
        "message_id": None,
        "error": "Channel not found or not a text channel.",
    }
