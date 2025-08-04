from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Enable async tests
pytestmark = pytest.mark.asyncio


@patch("flare_ai_kit.ecosystem.flare.Flare.check_balance", new_callable=AsyncMock)
@patch("flare_ai_kit.ecosystem.flare.Flare.__init__", return_value=None)
async def test_check_balance(mock_init, mock_check_balance):
    mock_check_balance.return_value = 123.45
    from flare_ai_kit.agent.ecosystem_tools_wrapper import check_balance

    result = await check_balance("0x123")
    assert result == 123.45
    mock_check_balance.assert_awaited_once()


@patch("flare_ai_kit.ecosystem.flare.Flare.check_connection", new_callable=AsyncMock)
@patch("flare_ai_kit.ecosystem.flare.Flare.__init__", return_value=None)
async def test_check_connection(mock_init, mock_check_connection):
    mock_check_connection.return_value = True
    from flare_ai_kit.agent.ecosystem_tools_wrapper import check_connection

    assert await check_connection() is True


@patch("flare_ai_kit.ecosystem.flare.Flare.build_transaction", new_callable=AsyncMock)
@patch("flare_ai_kit.ecosystem.flare.Flare.__init__", return_value=None)
async def test_build_transaction(mock_init, mock_build_transaction):
    mock_build_transaction.return_value = {"gas": 21000, "to": "0x123", "value": 100}
    from flare_ai_kit.agent.ecosystem_tools_wrapper import build_transaction

    function_call = AsyncMock()
    from_addr = "0x456"
    result = await build_transaction(function_call, from_addr)

    assert result == {"gas": 21000, "to": "0x123", "value": 100}
    mock_build_transaction.assert_awaited_once_with(function_call, from_addr)


@patch(
    "flare_ai_kit.ecosystem.flare.Flare.sign_and_send_transaction",
    new_callable=AsyncMock,
)
@patch("flare_ai_kit.ecosystem.flare.Flare.__init__", return_value=None)
async def test_sign_and_send_transaction(mock_init, mock_sign_and_send_transaction):
    mock_sign_and_send_transaction.return_value = "0xabc123"
    from flare_ai_kit.agent.ecosystem_tools_wrapper import sign_and_send_transaction

    tx = {"gas": 21000, "to": "0x123", "value": 100}
    result = await sign_and_send_transaction(tx)

    assert result == "0xabc123"
    mock_sign_and_send_transaction.assert_awaited_once_with(tx)


@patch("flare_ai_kit.ecosystem.flare.Flare.create_send_flr_tx", new_callable=AsyncMock)
@patch("flare_ai_kit.ecosystem.flare.Flare.__init__", return_value=None)
async def test_create_send_flr_tx(mock_init, mock_create_send_flr_tx):
    mock_create_send_flr_tx.return_value = {"gas": 21000, "to": "0x123", "value": 100}
    from flare_ai_kit.agent.ecosystem_tools_wrapper import create_send_flr_tx

    from_address = "0x456"
    to_address = "0x789"
    amount = 10.0
    result = await create_send_flr_tx(from_address, to_address, amount)

    assert result == {"gas": 21000, "to": "0x123", "value": 100}
    mock_create_send_flr_tx.assert_awaited_once_with(from_address, to_address, amount)


@patch("flare_ai_kit.ecosystem.protocols.ftsov2.FtsoV2.create", new_callable=AsyncMock)
async def test_get_ftso_latest_price(mock_create):
    mock_instance = AsyncMock()
    mock_instance.get_latest_price.return_value = 1.23
    mock_create.return_value = mock_instance

    from flare_ai_kit.agent.ecosystem_tools_wrapper import get_ftso_latest_price

    result = await get_ftso_latest_price("BTC/USD")
    assert result == 1.23
    mock_instance.get_latest_price.assert_awaited_once()


@patch("flare_ai_kit.ecosystem.protocols.ftsov2.FtsoV2.create", new_callable=AsyncMock)
async def test_get_ftso_latest_prices(mock_create):
    mock_instance = AsyncMock()
    mock_instance.get_latest_prices.return_value = [1.1, 2.2]
    mock_create.return_value = mock_instance

    from flare_ai_kit.agent.ecosystem_tools_wrapper import get_ftso_latest_prices

    result = await get_ftso_latest_prices(["BTC/USD", "ETH/USD"])
    assert result == [1.1, 2.2]
    mock_instance.get_latest_prices.assert_awaited_once()


@patch("flare_ai_kit.ecosystem.explorer.BlockExplorer.__init__", return_value=None)
async def test_get_contract_abi(mock_init):
    # Create mock instance and configure methods
    mock_explorer = MagicMock()
    mock_explorer.__aenter__ = AsyncMock(return_value=mock_explorer)
    mock_explorer.__aexit__ = AsyncMock()
    mock_explorer.get_contract_abi = AsyncMock(
        return_value=[{"type": "function", "name": "transfer"}]
    )
    mock_explorer.close = AsyncMock()

    # Patch constructor to return mock instance
    with patch(
        "flare_ai_kit.ecosystem.explorer.BlockExplorer", return_value=mock_explorer
    ):
        from flare_ai_kit.agent.ecosystem_tools_wrapper import get_contract_abi

        result = await get_contract_abi("0xabc")


@patch("flare_ai_kit.social.x.XClient.__init__", return_value=None)
@patch("flare_ai_kit.social.x.XClient.post_tweet", new_callable=AsyncMock)
async def test_post_to_x(mock_post_tweet, mock_init):
    # Create the mock instance
    mock_instance = MagicMock()
    mock_instance.is_configured = True
    mock_instance.post_tweet = AsyncMock(return_value=True)

    # Patch the XClient constructor to return the mock instance
    with patch("flare_ai_kit.social.x.XClient", return_value=mock_instance):
        from flare_ai_kit.agent.ecosystem_tools_wrapper import post_to_x

        result = await post_to_x("hello world")

        assert result is True
        mock_instance.post_tweet.assert_awaited_once_with("hello world")


@patch("flare_ai_kit.social.telegram.TelegramClient.__init__", return_value=None)
@patch(
    "flare_ai_kit.social.telegram.TelegramClient.send_message", new_callable=AsyncMock
)
async def test_send_telegram_message(mock_send, mock_init):
    mock_instance = MagicMock()
    mock_instance.is_configured = True
    mock_instance.send_message = AsyncMock(return_value=True)

    with patch(
        "flare_ai_kit.social.telegram.TelegramClient", return_value=mock_instance
    ):
        from flare_ai_kit.agent.ecosystem_tools_wrapper import send_telegram_message

        result = await send_telegram_message("@mychat", "hello telegram")
        assert result is True
        mock_instance.send_message.assert_awaited_once_with("@mychat", "hello telegram")
