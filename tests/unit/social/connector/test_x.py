from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from flare_ai_kit.social.connector.x import XConnector


@pytest.mark.asyncio
async def test_fetch_mentions_success():
    connector = XConnector()

    mock_tweet = MagicMock()
    mock_tweet.text = "Hello Twitter!"
    mock_tweet.author_id = 123
    mock_tweet.id = 456
    mock_tweet.created_at = MagicMock()
    mock_tweet.created_at.isoformat.return_value = "2024-01-01T00:00:00"

    mock_response = MagicMock()
    mock_response.data = [mock_tweet]

    with patch.object(
        connector.client,
        "search_recent_tweets",
        new=AsyncMock(return_value=mock_response),
    ):
        results = await connector.fetch_mentions("Hello")

    assert len(results) == 1
    assert results[0]["platform"] == "x"
    assert results[0]["content"] == "Hello Twitter!"
    assert results[0]["author_id"] == "123"
    assert results[0]["tweet_id"] == "456"
    assert results[0]["timestamp"] == "2024-01-01T00:00:00"


def test_post_tweet_success():
    connector = XConnector()

    mock_tweet = MagicMock()
    mock_tweet.id = 123
    mock_tweet.text = "Test tweet"
    mock_tweet.created_at.isoformat.return_value = "2024-01-01T00:00:00"

    with patch.object(connector.sync_client, "update_status", return_value=mock_tweet):
        result = connector.post_tweet("Test tweet")

    assert result["tweet_id"] == "123"
    assert result["content"] == "Test tweet"
    assert result["created_at"] == "2024-01-01T00:00:00"
