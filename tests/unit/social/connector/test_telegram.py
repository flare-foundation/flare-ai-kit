from unittest.mock import AsyncMock

import pytest

from flare_ai_kit.social.connector import SocialConnector
from flare_ai_kit.social.connector.telegram_connector import TelegramConnector

monkeypatch = pytest.MonkeyPatch


@pytest.fixture(autouse=True)
def mock_env(monkeypatch):
    monkeypatch.setenv("SOCIAL__TELEGRAM_BOT_TOKEN", "fake-token")
    monkeypatch.setenv("SOCIAL__TELEGRAM_CHAT_ID", "123456")


def test_inherits_base_class(monkeypatch):
    connector = TelegramConnector()
    assert isinstance(connector, SocialConnector)
    assert connector.platform == "telegram"


@pytest.mark.asyncio
async def test_fetch_mentions_filters_and_limits(monkeypatch):
    connector = TelegramConnector()

    connector._messages = [
        {
            "platform": "telegram",
            "content": "Flare is rising fast",
            "author_id": "1",
            "timestamp": "2024-01-01T00:00:00",
        },
        {
            "platform": "telegram",
            "content": "Totally unrelated",
            "author_id": "2",
            "timestamp": "2024-01-01T01:00:00",
        },
        {
            "platform": "telegram",
            "content": "Flare news!",
            "author_id": "3",
            "timestamp": "2024-01-01T02:00:00",
        },
    ]

    # Mock methods to skip actual Telegram API calls
    monkeypatch.setattr(connector.app, "initialize", AsyncMock())
    monkeypatch.setattr(connector.app, "start", AsyncMock())
    monkeypatch.setattr(connector.app, "stop", AsyncMock())
    monkeypatch.setattr(connector.app, "shutdown", AsyncMock())

    results = await connector.fetch_mentions("flare", limit=2)
    assert len(results) == 2
    assert all("flare" in msg["content"].lower() for msg in results)
