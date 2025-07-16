from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from flare_ai_kit.social.connector import SocialConnector
from flare_ai_kit.social.connector.farcaster import FarcasterConnector


def test_inherits_base_class(monkeypatch):
    monkeypatch.setenv("SOCIAL__FARCASTER_API_KEY", "fake-key")
    connector = FarcasterConnector()
    assert isinstance(connector, SocialConnector)
    assert connector.platform == "farcaster"


@pytest.mark.asyncio
async def test_fetch_mentions_returns_results(monkeypatch):
    monkeypatch.setenv("SOCIAL__FARCASTER_API_KEY", "fake-key")

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json = MagicMock(
        return_value={
            "casts": [
                {
                    "text": "flare alpha",
                    "author": {"fid": "123"},
                    "timestamp": "2025-07-01T12:00:00Z",
                },
                {
                    "text": "flare beta",
                    "author": {"fid": "456"},
                    "timestamp": "2025-07-01T13:00:00Z",
                },
            ]
        }
    )

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get.return_value = mock_response

    connector = FarcasterConnector(client=mock_client)
    results = await connector.fetch_mentions("flare")

    assert len(results) == 2
    assert results[0]["content"] == "flare alpha"
    assert results[0]["author_id"] == "123"
    assert results[0]["platform"] == "farcaster"


@pytest.mark.asyncio
async def test_fetch_mentions_handles_http_error(monkeypatch):
    monkeypatch.setenv("SOCIAL__FARCASTER_API_KEY", "fake-key")

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get.side_effect = httpx.HTTPError("API failed")

    connector = FarcasterConnector(client=mock_client)
    results = await connector.fetch_mentions("flare")

    assert results == []


@pytest.mark.asyncio
async def test_fetch_mentions_no_api_key(monkeypatch):
    monkeypatch.delenv("SOCIAL__FARCASTER_API_KEY", raising=False)

    connector = FarcasterConnector()
    results = await connector.fetch_mentions("flare")

    assert results == []


@pytest.mark.asyncio
async def test_post_message_success(monkeypatch):
    monkeypatch.setenv("SOCIAL__FARCASTER_API_KEY", "fake-key")
    monkeypatch.setenv("SOCIAL__FARCASTER_SIGNER_UUID", "erty57687898765-key")
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    connector = FarcasterConnector(client=mock_client)
    results = await connector.post_message("Hello Farcaster")
    assert results["platform"] == "farcaster"
    assert results["content"] == "Hello Farcaster"
