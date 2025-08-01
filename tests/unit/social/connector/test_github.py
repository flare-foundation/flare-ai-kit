# tests/unit/social/connector/test_github.py
from unittest.mock import AsyncMock, Mock, patch

import pytest
from httpx import HTTPError

from flare_ai_kit.social.connector.github import GitHubConnector


@pytest.mark.asyncio
async def test_fetch_mentions_success():
    connector = GitHubConnector()
    mock_response = AsyncMock()
    mock_response.json = AsyncMock(
        return_value=[
            {
                "body": "This is a test comment about AI",
                "user": {"login": "user123"},
                "created_at": "2024-01-01T12:00:00Z",
            }
        ]
    )
    mock_response.raise_for_status = Mock(return_value=None)

    with patch.object(connector.client, "get", return_value=mock_response):
        results = await connector.fetch_mentions("AI")

    assert len(results) == 1
    assert results[0]["content"] == "This is a test comment about AI"
    assert results[0]["author_id"] == "user123"
    assert results[0]["timestamp"] == "2024-01-01T12:00:00Z"


@pytest.mark.asyncio
async def test_fetch_mentions_failure():
    connector = GitHubConnector()

    with patch.object(connector.client, "get", side_effect=HTTPError("API fail")):
        results = await connector.fetch_mentions("AI")
    assert results == []
