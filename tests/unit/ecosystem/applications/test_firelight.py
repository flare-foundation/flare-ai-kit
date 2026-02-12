"""Unit tests for Firelight connector."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from flare_ai_kit.ecosystem.applications.firelight import Firelight
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
async def test_firelight_initialization(settings):
    """Test successful initialization of Firelight connector."""
    with (
        patch("flare_ai_kit.ecosystem.applications.firelight.load_abi"),
        patch("flare_ai_kit.ecosystem.flare.AsyncWeb3") as mock_async_web3,
    ):
        mock_w3 = MagicMock()
        mock_w3.eth.contract = MagicMock(return_value=MagicMock())
        mock_w3.to_checksum_address = lambda x: x
        mock_async_web3.return_value = mock_w3

        firelight = await Firelight.create(settings)

        assert firelight.vault_contract is not None


@pytest.mark.asyncio
async def test_get_stxrp_balance(settings):
    """Test getting stXRP balance."""
    with (
        patch("flare_ai_kit.ecosystem.applications.firelight.load_abi"),
        patch("flare_ai_kit.ecosystem.flare.AsyncWeb3") as mock_async_web3,
    ):
        mock_w3 = MagicMock()
        mock_w3.eth.contract = MagicMock(return_value=MagicMock())
        mock_w3.to_checksum_address = lambda x: x
        mock_async_web3.return_value = mock_w3

        firelight = await Firelight.create(settings)

    # Mock balance query
    mock_balance = 100 * 10**18
    firelight.vault_contract.functions.balanceOf = MagicMock(
        return_value=MagicMock(call=AsyncMock(return_value=mock_balance))
    )

    # Get balance
    balance = await firelight.get_stxrp_balance("0x123")

    # Verify
    assert balance == mock_balance


@pytest.mark.asyncio
async def test_get_total_assets(settings):
    """Test getting total assets in vault."""
    with (
        patch("flare_ai_kit.ecosystem.applications.firelight.load_abi"),
        patch("flare_ai_kit.ecosystem.flare.AsyncWeb3") as mock_async_web3,
    ):
        mock_w3 = MagicMock()
        mock_w3.eth.contract = MagicMock(return_value=MagicMock())
        mock_w3.to_checksum_address = lambda x: x
        mock_async_web3.return_value = mock_w3

        firelight = await Firelight.create(settings)

    # Mock total assets
    mock_total = 1000000 * 10**18
    firelight.vault_contract.functions.totalAssets = MagicMock(
        return_value=MagicMock(call=AsyncMock(return_value=mock_total))
    )

    # Get total
    total = await firelight.get_total_assets()

    # Verify
    assert total == mock_total


@pytest.mark.asyncio
async def test_get_current_period(settings):
    """Test getting current period."""
    with (
        patch("flare_ai_kit.ecosystem.applications.firelight.load_abi"),
        patch("flare_ai_kit.ecosystem.flare.AsyncWeb3") as mock_async_web3,
    ):
        mock_w3 = MagicMock()
        mock_w3.eth.contract = MagicMock(return_value=MagicMock())
        mock_w3.to_checksum_address = lambda x: x
        mock_async_web3.return_value = mock_w3

        firelight = await Firelight.create(settings)

    # Mock current period
    mock_period = 42
    firelight.vault_contract.functions.currentPeriod = MagicMock(
        return_value=MagicMock(call=AsyncMock(return_value=mock_period))
    )

    # Get period
    period = await firelight.get_current_period()

    # Verify
    assert period == mock_period


@pytest.mark.asyncio
async def test_get_pending_withdrawal(settings):
    """Test getting pending withdrawal amount."""
    with (
        patch("flare_ai_kit.ecosystem.applications.firelight.load_abi"),
        patch("flare_ai_kit.ecosystem.flare.AsyncWeb3") as mock_async_web3,
    ):
        mock_w3 = MagicMock()
        mock_w3.eth.contract = MagicMock(return_value=MagicMock())
        mock_w3.to_checksum_address = lambda x: x
        mock_async_web3.return_value = mock_w3

        firelight = await Firelight.create(settings)

    # Mock pending withdrawal
    mock_amount = 50 * 10**18
    firelight.vault_contract.functions.withdrawalsOf = MagicMock(
        return_value=MagicMock(call=AsyncMock(return_value=mock_amount))
    )

    # Get pending
    pending = await firelight.get_pending_withdrawal(10, "0x123")

    # Verify
    assert pending == mock_amount
