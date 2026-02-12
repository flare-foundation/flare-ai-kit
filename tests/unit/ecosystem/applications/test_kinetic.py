"""Unit tests for Kinetic connector."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from flare_ai_kit.ecosystem.applications.kinetic import Kinetic
from flare_ai_kit.ecosystem.settings import EcosystemSettings


@pytest.fixture
def settings():
    """Create a valid EcosystemSettings for testing."""
    return EcosystemSettings(
        wallet_address="0x1234567890123456789012345678901234567890",
        private_key="0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
        web3_provider_url="https://flare-api.flare.network/ext/C/rpc",
        max_retries=3,
    )


@pytest.mark.asyncio
async def test_kinetic_initialization(settings):
    """Test successful initialization of Kinetic connector."""
    with (
        patch("flare_ai_kit.ecosystem.applications.kinetic.load_abi"),
        patch("flare_ai_kit.ecosystem.flare.AsyncWeb3") as mock_async_web3,
    ):
        mock_w3 = MagicMock()
        mock_w3.eth.contract = MagicMock(return_value=MagicMock())
        mock_w3.to_checksum_address = lambda x: x
        mock_async_web3.return_value = mock_w3

        kinetic = await Kinetic.create(settings)

        assert kinetic.ksflr_contract is not None


@pytest.mark.asyncio
async def test_get_balance(settings):
    """Test getting ksFLR balance."""
    with (
        patch("flare_ai_kit.ecosystem.applications.kinetic.load_abi"),
        patch("flare_ai_kit.ecosystem.flare.AsyncWeb3") as mock_async_web3,
    ):
        mock_w3 = MagicMock()
        mock_w3.eth.contract = MagicMock(return_value=MagicMock())
        mock_w3.to_checksum_address = lambda x: x
        mock_async_web3.return_value = mock_w3

        kinetic = await Kinetic.create(settings)

    # Mock balance query
    mock_balance = 5 * 10**18
    kinetic.ksflr_contract.functions.balanceOf = MagicMock(
        return_value=MagicMock(call=AsyncMock(return_value=mock_balance))
    )

    # Get balance
    balance = await kinetic.get_balance("0x123")

    # Verify
    assert balance == mock_balance


@pytest.mark.asyncio
async def test_get_underlying_balance(settings):
    """Test getting underlying sFLR balance."""
    with (
        patch("flare_ai_kit.ecosystem.applications.kinetic.load_abi"),
        patch("flare_ai_kit.ecosystem.flare.AsyncWeb3") as mock_async_web3,
    ):
        mock_w3 = MagicMock()
        mock_w3.eth.contract = MagicMock(return_value=MagicMock())
        mock_w3.to_checksum_address = lambda x: x
        mock_async_web3.return_value = mock_w3

        kinetic = await Kinetic.create(settings)

    # Mock underlying balance
    mock_balance = 5 * 10**18
    kinetic.ksflr_contract.functions.balanceOfUnderlying = MagicMock(
        return_value=MagicMock(call=AsyncMock(return_value=mock_balance))
    )

    # Get balance
    balance = await kinetic.get_underlying_balance("0x123")

    # Verify
    assert balance == mock_balance


@pytest.mark.asyncio
async def test_get_exchange_rate(settings):
    """Test getting exchange rate."""
    with (
        patch("flare_ai_kit.ecosystem.applications.kinetic.load_abi"),
        patch("flare_ai_kit.ecosystem.flare.AsyncWeb3") as mock_async_web3,
    ):
        mock_w3 = MagicMock()
        mock_w3.eth.contract = MagicMock(return_value=MagicMock())
        mock_w3.to_checksum_address = lambda x: x
        mock_async_web3.return_value = mock_w3

        kinetic = await Kinetic.create(settings)

    # Mock exchange rate (e.g., 1 ksFLR = 1.05 sFLR)
    mock_rate = int(1.05 * 10**18)
    kinetic.ksflr_contract.functions.exchangeRateCurrent = MagicMock(
        return_value=MagicMock(call=AsyncMock(return_value=mock_rate))
    )

    # Get rate
    rate = await kinetic.get_exchange_rate()

    # Verify
    assert rate == mock_rate


@pytest.mark.asyncio
async def test_get_supply_rate(settings):
    """Test getting supply rate."""
    with (
        patch("flare_ai_kit.ecosystem.applications.kinetic.load_abi"),
        patch("flare_ai_kit.ecosystem.flare.AsyncWeb3") as mock_async_web3,
    ):
        mock_w3 = MagicMock()
        mock_w3.eth.contract = MagicMock(return_value=MagicMock())
        mock_w3.to_checksum_address = lambda x: x
        mock_async_web3.return_value = mock_w3

        kinetic = await Kinetic.create(settings)

    # Mock supply rate - need to mock the actual functions attribute
    mock_rate = 12345
    mock_functions = MagicMock()
    mock_functions.supplyRatePerTimestamp = MagicMock(
        return_value=MagicMock(call=AsyncMock(return_value=mock_rate))
    )
    kinetic.ksflr_contract.functions = mock_functions

    # Get rate
    rate = await kinetic.get_supply_rate()

    # Verify
    assert rate == mock_rate
