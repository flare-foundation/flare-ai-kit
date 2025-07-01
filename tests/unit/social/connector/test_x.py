from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from flare_ai_kit.social.connector import SocialConnector
from flare_ai_kit.social.connector.x import XConnector


@pytest.fixture(autouse=True)
def set_env(monkeypatch):
    monkeypatch.setenv("SOCIAL__X_API_KEY", "fake-key")
    monkeypatch.setenv("SOCIAL__X_API_KEY_SECRET", "fake-secret")
    monkeypatch.setenv("SOCIAL__X_ACCESS_TOKEN", "fake-token")
    monkeypatch.setenv("SOCIAL__X_ACCESS_TOKEN_SECRET", "fake-token-secret")


@pytest.mark.asyncio
async def test_inherits_base_class():
    connector = XConnector()
    assert isinstance(connector, SocialConnector)
    assert connector.platform == "x"


@pytest.mark.asyncio
@patch("flare_ai_kit.social.connector.x.AsyncClient")
async def test_fetch_mentions_returns_list(mock_async_client):
    mock_client = mock_async_client.return_value
    mock_response = MagicMock()
    mock_response.data = [
        MagicMock(
            text="Test tweet",
            author_id="12345",
            id=1,
            created_at=None,
        )
    ]
    mock_client.search_recent_tweets = AsyncMock(return_value=mock_response)

    connector = XConnector()
    connector.client = mock_client

    results = await connector.fetch_mentions("flare")
    assert isinstance(results, list)
    assert results[0]["content"] == "Test tweet"
    assert results[0]["author_id"] == "12345"


@patch("flare_ai_kit.social.connector.x.API")
def test_post_tweet_success(mock_api):
    mock_api = mock_api.return_value
    mock_api.update_status.return_value = MagicMock(
        id=1, text="hello", created_at="now"
    )

    connector = XConnector()
    connector.sync_client = mock_api

    result = connector.post_tweet("hello")
    assert result["content"] == "hello"
    assert result["tweet_id"] == 1


@patch("flare_ai_kit.social.connector.x.API")
def test_reply_to_tweet_success(mock_api):
    mock_api = mock_api.return_value
    mock_api.update_status.return_value = MagicMock(
        id=2, text="thanks!", created_at="now"
    )

    connector = XConnector()
    connector.sync_client = mock_api

    result = connector.reply_to_tweet(tweet_id=1, reply_text="thanks!")
    assert result["reply_id"] == 2
    assert result["content"] == "thanks!"
