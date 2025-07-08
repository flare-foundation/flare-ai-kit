from unittest.mock import AsyncMock

import pytest
from dotenv import load_dotenv

from flare_ai_kit.social.connector import SocialConnector
from flare_ai_kit.social.connector.telegram_connector import TelegramConnector

load_dotenv()


@pytest.fixture(autouse=True)
def mock_env(monkeypatch):
    monkeypatch.setenv("SOCIAL__TELEGRAM_BOT_TOKEN", "fake-token")
    monkeypatch.setenv("SOCIAL__TELEGRAM_CHAT_ID", "123456")


def test_inherits_base_class():
    connector = TelegramConnector()
    assert isinstance(connector, SocialConnector)
    assert connector.platform == "telegram"


@pytest.mark.asyncio
async def test_fetch_mentions_filters_and_limits(monkeypatch):
    connector = TelegramConnector()

    connector._messages = [
        {
            "platform": "telegram",
            "content": "Flare update",
            "author_id": "1",
            "timestamp": "t1",
        },
        {
            "platform": "telegram",
            "content": "Other content",
            "author_id": "2",
            "timestamp": "t2",
        },
        {
            "platform": "telegram",
            "content": "Flare again",
            "author_id": "3",
            "timestamp": "t3",
        },
    ]

    monkeypatch.setattr(connector.app, "initialize", AsyncMock())
    monkeypatch.setattr(connector.app, "start", AsyncMock())
    monkeypatch.setattr(connector.app, "stop", AsyncMock())
    monkeypatch.setattr(connector.app, "shutdown", AsyncMock())

    results = await connector.fetch_mentions("flare", limit=2)
    assert len(results) == 2
    assert all("flare" in msg["content"].lower() for msg in results)
