"""Tests for SparkDEX connector."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from flare_ai_kit.common import FlareTxError
from flare_ai_kit.ecosystem.applications.sparkdex import (
    FEE_HIGH,
    FEE_LOW,
    FEE_MEDIUM,
    SparkDEX,
)
from flare_ai_kit.ecosystem.settings import EcosystemSettings


@pytest.fixture
def settings():
    """Create test settings."""
    return EcosystemSettings()


@pytest.fixture
def mock_w3():
    """Create a mock Web3 instance."""
    mock = MagicMock()
    mock.eth.contract = MagicMock()
    mock.to_checksum_address = lambda x: x
    return mock


@pytest.mark.asyncio
class TestSparkDEX:
    """Tests for SparkDEX class."""

    async def test_create_initializes_router(self, settings):
        """Test that create() initializes the swap router."""
        with patch(
            "flare_ai_kit.ecosystem.applications.sparkdex.load_abi"
        ) as mock_load_abi:
            mock_load_abi.return_value = []  # Return empty list for valid ABI
            sparkdex = await SparkDEX.create(settings)

            assert sparkdex.swap_router is not None

    async def test_create_fails_without_router_address(self):
        """Test that create() fails if router address is not configured."""
        settings = EcosystemSettings()
        settings.contracts.flare.sparkdex_swap_router = None

        with pytest.raises(FlareTxError, match="SwapRouter address not configured"):
            await SparkDEX.create(settings)

    async def test_swap_exact_input_single(self, settings, mock_w3):
        """Test exactInputSingle swap."""
        sparkdex = SparkDEX(settings)
        sparkdex.w3 = mock_w3
        sparkdex.address = "0x1234567890123456789012345678901234567890"

        # Mock the swap router contract
        mock_contract = MagicMock()
        mock_function = MagicMock()
        mock_function.return_value = mock_function
        mock_contract.functions.exactInputSingle = mock_function
        sparkdex.swap_router = mock_contract

        # Mock build and send transaction
        sparkdex.build_transaction = AsyncMock(return_value={"from": "0x123"})
        sparkdex.sign_and_send_transaction = AsyncMock(
            return_value="0xabcdef1234567890"
        )

        tx_hash = await sparkdex.swap_exact_input_single(
            token_in="0xTokenIn",
            token_out="0xTokenOut",
            fee=FEE_MEDIUM,
            recipient="0xRecipient",
            amount_in=1000000,
            amount_out_minimum=990000,
            deadline=1234567890,
        )

        assert tx_hash == "0xabcdef1234567890"
        mock_function.assert_called_once()
        sparkdex.build_transaction.assert_called_once()
        sparkdex.sign_and_send_transaction.assert_called_once()

    async def test_swap_exact_output_single(self, settings, mock_w3):
        """Test exactOutputSingle swap."""
        sparkdex = SparkDEX(settings)
        sparkdex.w3 = mock_w3
        sparkdex.address = "0x1234567890123456789012345678901234567890"

        mock_contract = MagicMock()
        mock_function = MagicMock()
        mock_function.return_value = mock_function
        mock_contract.functions.exactOutputSingle = mock_function
        sparkdex.swap_router = mock_contract

        sparkdex.build_transaction = AsyncMock(return_value={"from": "0x123"})
        sparkdex.sign_and_send_transaction = AsyncMock(
            return_value="0xabcdef1234567890"
        )

        tx_hash = await sparkdex.swap_exact_output_single(
            token_in="0xTokenIn",
            token_out="0xTokenOut",
            fee=FEE_LOW,
            recipient="0xRecipient",
            amount_out=1000000,
            amount_in_maximum=1010000,
            deadline=1234567890,
        )

        assert tx_hash == "0xabcdef1234567890"
        mock_function.assert_called_once()

    async def test_swap_without_initialization_fails(self, settings):
        """Test that swapping without initialization raises error."""
        sparkdex = SparkDEX(settings)

        with pytest.raises(AttributeError, match="not fully initialized"):
            await sparkdex.swap_exact_input_single(
                token_in="0xTokenIn",
                token_out="0xTokenOut",
                fee=FEE_MEDIUM,
                recipient="0xRecipient",
                amount_in=1000000,
                amount_out_minimum=990000,
                deadline=1234567890,
            )

    async def test_swap_without_account_fails(self, settings, mock_w3):
        """Test that swapping without an account raises error."""
        sparkdex = SparkDEX(settings)
        sparkdex.w3 = mock_w3
        sparkdex.swap_router = MagicMock()
        sparkdex.address = None

        with pytest.raises(ValueError, match="Account not initialized"):
            await sparkdex.swap_exact_input_single(
                token_in="0xTokenIn",
                token_out="0xTokenOut",
                fee=FEE_MEDIUM,
                recipient="0xRecipient",
                amount_in=1000000,
                amount_out_minimum=990000,
                deadline=1234567890,
            )

    async def test_get_factory_address(self, settings, mock_w3):
        """Test getting factory address."""
        sparkdex = SparkDEX(settings)
        sparkdex.w3 = mock_w3

        mock_contract = MagicMock()
        mock_factory = AsyncMock(return_value="0xFactoryAddress")
        mock_contract.functions.factory.return_value.call = mock_factory
        sparkdex.swap_router = mock_contract

        factory = await sparkdex.get_factory_address()

        assert factory == "0xFactoryAddress"
        mock_factory.assert_called_once()

    async def test_get_weth9_address(self, settings, mock_w3):
        """Test getting WETH9 address."""
        sparkdex = SparkDEX(settings)
        sparkdex.w3 = mock_w3

        mock_contract = MagicMock()
        mock_weth9 = AsyncMock(return_value="0xWETH9Address")
        mock_contract.functions.WETH9.return_value.call = mock_weth9
        sparkdex.swap_router = mock_contract

        weth9 = await sparkdex.get_weth9_address()

        assert weth9 == "0xWETH9Address"
        mock_weth9.assert_called_once()

    async def test_fee_constants(self):
        """Test that fee constants are defined correctly."""
        assert FEE_LOW == 500
        assert FEE_MEDIUM == 3000
        assert FEE_HIGH == 10000

    async def test_build_transaction_failure(self, settings, mock_w3):
        """Test handling of build transaction failure."""
        sparkdex = SparkDEX(settings)
        sparkdex.w3 = mock_w3
        sparkdex.address = "0x1234567890123456789012345678901234567890"

        mock_contract = MagicMock()
        mock_function = MagicMock()
        mock_function.return_value = mock_function
        mock_contract.functions.exactInputSingle = mock_function
        sparkdex.swap_router = mock_contract

        sparkdex.build_transaction = AsyncMock(return_value=None)

        with pytest.raises(FlareTxError, match="Failed to build swap transaction"):
            await sparkdex.swap_exact_input_single(
                token_in="0xTokenIn",
                token_out="0xTokenOut",
                fee=FEE_MEDIUM,
                recipient="0xRecipient",
                amount_in=1000000,
                amount_out_minimum=990000,
                deadline=1234567890,
            )

    async def test_send_transaction_failure(self, settings, mock_w3):
        """Test handling of send transaction failure."""
        sparkdex = SparkDEX(settings)
        sparkdex.w3 = mock_w3
        sparkdex.address = "0x1234567890123456789012345678901234567890"

        mock_contract = MagicMock()
        mock_function = MagicMock()
        mock_function.return_value = mock_function
        mock_contract.functions.exactInputSingle = mock_function
        sparkdex.swap_router = mock_contract

        sparkdex.build_transaction = AsyncMock(return_value={"from": "0x123"})
        sparkdex.sign_and_send_transaction = AsyncMock(return_value=None)

        with pytest.raises(FlareTxError, match="Failed to send swap transaction"):
            await sparkdex.swap_exact_input_single(
                token_in="0xTokenIn",
                token_out="0xTokenOut",
                fee=FEE_MEDIUM,
                recipient="0xRecipient",
                amount_in=1000000,
                amount_out_minimum=990000,
                deadline=1234567890,
            )
