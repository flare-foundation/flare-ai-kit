from unittest.mock import MagicMock, patch

import pytest
from slack_sdk.errors import SlackApiError

from flare_ai_kit.social.connector import SocialConnector
from flare_ai_kit.social.connector.slack import SlackConnector


def test_inherits_base_class(monkeypatch):
    monkeypatch.setenv("SLACK_BOT_TOKEN", "fake-token")
    monkeypatch.setenv("SLACK_CHANNEL_ID", "fake-channel")
    mock_client = MagicMock()
    connector = SlackConnector(client=mock_client)
    assert isinstance(connector, SocialConnector)
    assert connector.platform == "slack"


@pytest.mark.asyncio
async def test_fetch_mentions_returns_matching_messages(monkeypatch):
    monkeypatch.setenv("SLACK_BOT_TOKEN", "fake-token")
    monkeypatch.setenv("SLACK_CHANNEL_ID", "fake-channel")

    mock_client = MagicMock()
    mock_client.conversations_history.return_value = {
        "messages": [
            {"text": "Flare alpha", "user": "U1", "ts": "111"},
            {"text": "Random text", "user": "U2", "ts": "112"},
            {"text": "Flare beta", "user": "U3", "ts": "113"},
        ]
    }

    connector = SlackConnector(client=mock_client)
    results = await connector.fetch_mentions("flare", limit=2)

    assert all("flare" in msg["content"].lower() for msg in results)


@pytest.mark.asyncio
async def test_fetch_mentions_handles_error(monkeypatch):
    monkeypatch.setenv("SLACK_BOT_TOKEN", "fake-token")
    monkeypatch.setenv("SLACK_CHANNEL_ID", "fake-channel")

    mock_client = MagicMock()
    mock_client.conversations_history.side_effect = SlackApiError("fail", response={})

    connector = SlackConnector(client=mock_client)
    results = await connector.fetch_mentions("flare")

    assert results == []


@pytest.mark.asyncio
async def test_fetch_mentions_no_env(monkeypatch):
    monkeypatch.delenv("SLACK_BOT_TOKEN", raising=False)
    monkeypatch.delenv("SLACK_CHANNEL_ID", raising=False)
    mock_client = MagicMock()
    connector = SlackConnector(client=mock_client)
    results = await connector.fetch_mentions("flare")

    assert results == []


@pytest.mark.asyncio
async def test_post_message_success(monkeypatch):
    mock_client = MagicMock()
    connector = SlackConnector(client=mock_client)
    mock_response = {
        "ts": "123456.7890",
        "message": {"text": "Hello from Slack"},
    }

    with patch.object(connector.client, "chat_postMessage", return_value=mock_response):
        result = connector.post_message("Hello from Slack")
        assert result["platform"] == "slack"
        assert result["content"] == "Hello from Slack"
