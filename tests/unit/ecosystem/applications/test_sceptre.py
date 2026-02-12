"""Unit tests for Sceptre connector."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from flare_ai_kit.ecosystem.applications.sceptre import Sceptre
from flare_ai_kit.ecosystem.settings import EcosystemSettings


@pytest.fixture
def settings():
    """Create test settings."""
    return EcosystemSettings()


@pytest.mark.asyncio
async def test_sceptre_initialization(settings):
    """Test Sceptre connector initialization."""
    with (
        patch("flare_ai_kit.ecosystem.applications.sceptre.load_abi") as mock_load_abi,
        patch("flare_ai_kit.ecosystem.flare.AsyncWeb3") as mock_async_web3,
    ):
        mock_w3 = MagicMock()
        mock_w3.eth.contract = MagicMock(return_value=MagicMock())
        mock_w3.to_checksum_address = lambda x: x
        mock_w3.eth.get_transaction_count = MagicMock(return_value=0)
        mock_async_web3.return_value = mock_w3
        mock_load_abi.return_value = []

        sceptre = await Sceptre.create(settings)
        assert sceptre is not None
        assert sceptre.sflr_contract is not None


@pytest.mark.asyncio
async def test_get_sflr_balance(settings):
    """Test getting sFLR balance."""
    with (
        patch("flare_ai_kit.ecosystem.applications.sceptre.load_abi"),
        patch("flare_ai_kit.ecosystem.flare.AsyncWeb3") as mock_async_web3,
    ):
        mock_w3 = MagicMock()
        mock_w3.eth.contract = MagicMock(return_value=MagicMock())
        mock_w3.to_checksum_address = lambda x: x
        mock_async_web3.return_value = mock_w3

        sceptre = await Sceptre.create(settings)

    # Mock balance query
    mock_balance = 5 * 10**18
    sceptre.sflr_contract.functions.balanceOf = MagicMock(
        return_value=MagicMock(call=AsyncMock(return_value=mock_balance))
    )

    # Get balance
    balance = await sceptre.get_sflr_balance("0x123")

    # Verify
    assert balance == mock_balance


@pytest.mark.asyncio
async def test_get_total_pooled_flr(settings):
    """Test getting total pooled FLR."""
    with (
        patch("flare_ai_kit.ecosystem.applications.sceptre.load_abi"),
        patch("flare_ai_kit.ecosystem.flare.AsyncWeb3") as mock_async_web3,
    ):
        mock_w3 = MagicMock()
        mock_w3.eth.contract = MagicMock(return_value=MagicMock())
        mock_w3.to_checksum_address = lambda x: x
        mock_async_web3.return_value = mock_w3

        sceptre = await Sceptre.create(settings)

    # Mock total pooled FLR
    mock_total = 1000000 * 10**18
    sceptre.sflr_contract.functions.getTotalPooledFlr = MagicMock(
        return_value=MagicMock(call=AsyncMock(return_value=mock_total))
    )

    # Get total
    total = await sceptre.get_total_pooled_flr()

    # Verify
    assert total == mock_total


@pytest.mark.asyncio
async def test_get_flr_by_shares(settings):
    """Test converting sFLR shares to FLR."""
    with (
        patch("flare_ai_kit.ecosystem.applications.sceptre.load_abi"),
        patch("flare_ai_kit.ecosystem.flare.AsyncWeb3") as mock_async_web3,
    ):
        mock_w3 = MagicMock()
        mock_w3.eth.contract = MagicMock(return_value=MagicMock())
        mock_w3.to_checksum_address = lambda x: x
        mock_async_web3.return_value = mock_w3

        sceptre = await Sceptre.create(settings)

    # Mock conversion (1 sFLR = 1.05 FLR due to rewards)
    shares = 10 * 10**18
    flr_amount = int(10.5 * 10**18)
    sceptre.sflr_contract.functions.getPooledFlrByShares = MagicMock(
        return_value=MagicMock(call=AsyncMock(return_value=flr_amount))
    )

    # Convert
    result = await sceptre.get_flr_by_shares(shares)

    # Verify
    assert result == flr_amount


@pytest.mark.asyncio
async def test_get_shares_by_flr(settings):
    """Test converting FLR to sFLR shares."""
    with (
        patch("flare_ai_kit.ecosystem.applications.sceptre.load_abi"),
        patch("flare_ai_kit.ecosystem.flare.AsyncWeb3") as mock_async_web3,
    ):
        mock_w3 = MagicMock()
        mock_w3.eth.contract = MagicMock(return_value=MagicMock())
        mock_w3.to_checksum_address = lambda x: x
        mock_async_web3.return_value = mock_w3

        sceptre = await Sceptre.create(settings)

    # Mock conversion (10 FLR = 9.52 sFLR due to rewards)
    flr_amount = 10 * 10**18
    shares = int(9.52 * 10**18)
    sceptre.sflr_contract.functions.getSharesByPooledFlr = MagicMock(
        return_value=MagicMock(call=AsyncMock(return_value=shares))
    )

    # Convert
    result = await sceptre.get_shares_by_flr(flr_amount)

    # Verify
    assert result == shares
