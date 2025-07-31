from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from flare_ai_kit.social.connector import SocialConnector
from flare_ai_kit.social.connector.farcaster import FarcasterConnector


@pytest.fixture(autouse=True)
def set_api_key(monkeypatch):
    # default fake key; individual tests can remove it
    monkeypatch.setenv("SOCIAL__FARCASTER_API_KEY", "fake-key")


@pytest.fixture
def mock_client():
    # stand-in for httpx.AsyncClient
    return AsyncMock(spec=httpx.AsyncClient)


def test_inherits_base_class(mock_client):
    conn = FarcasterConnector(client=mock_client)
    assert isinstance(conn, SocialConnector)
    assert conn.platform == "farcaster"


@pytest.mark.asyncio
async def test_fetch_mentions_success(mock_client):
    # stub a single “cast” with a known timestamp
    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.json.return_value = {
        "casts": [
            {
                "text": "flare",
                "author": {"fid": "42"},
                "timestamp": "2025-07-01T12:00:00Z",
            }
        ]
    }
    mock_client.get.return_value = resp

    conn = FarcasterConnector(client=mock_client)
    out = await conn.fetch_mentions("flare")

    # now include the platform field too
    assert out == [
        {
            "platform": "farcaster",
            "content": "flare",
            "author_id": "42",
            "timestamp": "2025-07-01T12:00:00Z",
        }
    ]


@pytest.mark.asyncio
async def test_fetch_mentions_http_error(mock_client):
    mock_client.get.side_effect = httpx.HTTPError("API down")
    conn = FarcasterConnector(client=mock_client)
    assert await conn.fetch_mentions("flare") == []


@pytest.mark.asyncio
async def test_fetch_mentions_no_api_key(monkeypatch):
    monkeypatch.delenv("SOCIAL__FARCASTER_API_KEY", raising=False)
    conn = FarcasterConnector()
    assert await conn.fetch_mentions("flare") == []


@pytest.mark.asyncio
async def test_post_message_success(mock_client, monkeypatch):
    monkeypatch.setenv("SOCIAL__FARCASTER_SIGNER_UUID", "signer-id")

    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.json.return_value = {"signed_message": "signed"}
    mock_client.post.return_value = resp

    conn = FarcasterConnector(client=mock_client)
    result = await conn.post_message("Hello Farcaster")

    assert result["platform"] == "farcaster"
    assert result["content"] == "Hello Farcaster"
    mock_client.post.assert_awaited_once()
