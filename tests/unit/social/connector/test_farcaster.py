from unittest.mock import AsyncMock, patch

import pytest
from httpx import HTTPError

from flare_ai_kit.social.connector import SocialConnector
from flare_ai_kit.social.connector.farcaster import FarcasterConnector


@pytest.fixture(autouse=True)
def mock_env(monkeypatch):
    monkeypatch.setenv("FARCASTER_API_KEY", "test-api-key")


def test_inherits_base_class():
    connector = FarcasterConnector()
    assert isinstance(connector, SocialConnector)
    assert connector.platform == "farcaster"


@pytest.mark.asyncio
@patch("flare_ai_kit.social.connector.farcaster.httpx.AsyncClient.get")
async def test_fetch_mentions_success(mock_get):
    # Prepare async .json() response
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json = AsyncMock(
        return_value={
            "casts": [
                {
                    "text": "Flare Network update",
                    "author": {"fid": "123"},
                    "timestamp": "2025-06-30T12:00:00Z",
                },
                {
                    "text": "Another cast",
                    "author": {"fid": "456"},
                    "timestamp": "2025-06-30T13:00:00Z",
                },
            ]
        }
    )
    mock_get.return_value = mock_response

    connector = FarcasterConnector()
    results = await connector.fetch_mentions("flare")
    assert len(results) == 2
    assert results[0]["platform"] == "farcaster"
    assert "flare" in results[0]["content"].lower()


@patch("flare_ai_kit.social.connector.farcaster.httpx.AsyncClient.get")
@pytest.mark.asyncio
async def test_fetch_mentions_handles_error(mock_get):
    mock_get.side_effect = HTTPError("API failed")
    connector = FarcasterConnector()
    results = await connector.fetch_mentions("flare")
    assert results == []
