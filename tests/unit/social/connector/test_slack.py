from unittest.mock import patch

import pytest

from flare_ai_kit.social.connector import SocialConnector
from flare_ai_kit.social.connector.slack import SlackConnector


@pytest.fixture(autouse=True)
def mock_env(monkeypatch):
    monkeypatch.setenv("SLACK_BOT_TOKEN", "fake-token")
    monkeypatch.setenv("SLACK_CHANNEL_ID", "C12345678")


def test_inherits_base_class():
    connector = SlackConnector()
    assert isinstance(connector, SocialConnector)
    assert connector.platform == "slack"


@patch("flare_ai_kit.social.connector.slack.WebClient")
@pytest.mark.asyncio
async def test_fetch_mentions_returns_matching_messages(mock_client):
    mock_client = mock_client.return_value
    mock_client.conversations_history.return_value = {
        "messages": [
            {"text": "Flare is awesome", "user": "U1", "ts": "123.45"},
            {"text": "Unrelated message", "user": "U2", "ts": "124.56"},
            {"text": "More about Flare", "user": "U3", "ts": "125.67"},
        ]
    }

    connector = SlackConnector()
    connector.client = mock_client

    results = await connector.fetch_mentions("flare")
    assert len(results) == 2
    assert results[0]["content"].lower().find("flare") >= 0


@patch("flare_ai_kit.social.connector.slack.WebClient")
@pytest.mark.asyncio
async def test_fetch_mentions_handles_error(mock_client):
    mock_client = mock_client.return_value
    mock_client.conversations_history.side_effect = Exception("Slack failure")

    connector = SlackConnector()
    connector.client = mock_client

    results = await connector.fetch_mentions("flare")
    assert results == []
