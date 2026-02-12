"""Unit tests for Cyclo connector."""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from flare_ai_kit.common import CycloError
from flare_ai_kit.ecosystem.applications.cyclo import Cyclo
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


@pytest_asyncio.fixture
async def cyclo_connector(settings, mock_w3):
    """Create Cyclo connector with mocked dependencies."""
    with (
        patch("flare_ai_kit.ecosystem.applications.cyclo.load_abi") as mock_load_abi,
        patch("flare_ai_kit.ecosystem.flare.AsyncWeb3") as mock_async_web3,
    ):
        # Setup Web3 mock
        mock_async_web3.return_value = mock_w3
        mock_load_abi.return_value = []

        # Create connector
        connector = await Cyclo.create(settings)
        return connector


@pytest.mark.asyncio
async def test_cyclo_initialization(settings, mock_w3):
    """Test Cyclo connector initialization."""
    with (
        patch("flare_ai_kit.ecosystem.applications.cyclo.load_abi") as mock_load_abi,
        patch("flare_ai_kit.ecosystem.flare.AsyncWeb3") as mock_async_web3,
    ):
        mock_async_web3.return_value = mock_w3
        mock_load_abi.return_value = []

        connector = await Cyclo.create(settings)

        assert connector is not None
        assert connector.vault_contract is not None
        assert connector.receipt_contract is not None
        assert mock_load_abi.call_count == 2  # Vault + Receipt ABIs


@pytest.mark.asyncio
async def test_deposit_sflr_success(cyclo_connector, mock_w3):
    """Test successful sFLR deposit."""
    # Setup mocks
    mock_function = MagicMock()
    cyclo_connector.vault_contract.functions.deposit = MagicMock(
        return_value=mock_function
    )
    mock_tx_hash = "0xabc123def456"

    with (
        patch.object(
            cyclo_connector, "build_transaction", new_callable=AsyncMock
        ) as mock_build,
        patch.object(
            cyclo_connector, "sign_and_send_transaction", new_callable=AsyncMock
        ) as mock_sign_send,
    ):
        mock_build.return_value = {"from": "0x123"}
        mock_sign_send.return_value = mock_tx_hash

        # Execute
        result = await cyclo_connector.deposit_sflr(
            assets=1000000000000000000,  # 1 sFLR
            recipient="0x742d35Cc6634C0532925a3b844Bc454e4438f44e",
            min_share_ratio=0,
        )

        # Verify
        assert result == mock_tx_hash
        cyclo_connector.vault_contract.functions.deposit.assert_called_once()
        mock_build.assert_awaited_once()
        mock_sign_send.assert_awaited_once()


@pytest.mark.asyncio
async def test_deposit_sflr_no_vault_contract(cyclo_connector):
    """Test deposit fails when vault contract not initialized."""
    cyclo_connector.vault_contract = None

    with pytest.raises(CycloError, match="vault contract not initialized"):
        await cyclo_connector.deposit_sflr(
            assets=1000000000000000000,
            recipient="0x742d35Cc6634C0532925a3b844Bc454e4438f44e",
        )


@pytest.mark.asyncio
async def test_redeem_sflr_success(cyclo_connector, mock_w3):
    """Test successful sFLR redemption."""
    # Setup mocks
    mock_function = MagicMock()
    cyclo_connector.vault_contract.functions.redeem = MagicMock(
        return_value=mock_function
    )
    mock_tx_hash = "0xdef789ghi012"

    with (
        patch.object(
            cyclo_connector, "build_transaction", new_callable=AsyncMock
        ) as mock_build,
        patch.object(
            cyclo_connector, "sign_and_send_transaction", new_callable=AsyncMock
        ) as mock_sign_send,
    ):
        mock_build.return_value = {"from": "0x123"}
        mock_sign_send.return_value = mock_tx_hash

        # Execute
        result = await cyclo_connector.redeem_sflr(
            shares=1000000000000000000,  # 1 cysFLR
            recipient="0x742d35Cc6634C0532925a3b844Bc454e4438f44e",
            owner="0x742d35Cc6634C0532925a3b844Bc454e4438f44e",
            receipt_id=int(time.time()),
        )

        # Verify
        assert result == mock_tx_hash
        cyclo_connector.vault_contract.functions.redeem.assert_called_once()
        mock_build.assert_awaited_once()
        mock_sign_send.assert_awaited_once()


@pytest.mark.asyncio
async def test_redeem_sflr_no_vault_contract(cyclo_connector):
    """Test redeem fails when vault contract not initialized."""
    cyclo_connector.vault_contract = None

    with pytest.raises(CycloError, match="vault contract not initialized"):
        await cyclo_connector.redeem_sflr(
            shares=1000000000000000000,
            recipient="0x742d35Cc6634C0532925a3b844Bc454e4438f44e",
            owner="0x742d35Cc6634C0532925a3b844Bc454e4438f44e",
            receipt_id=12345,
        )


@pytest.mark.asyncio
async def test_get_cysflr_balance(cyclo_connector):
    """Test getting cysFLR balance."""
    # Setup mock
    mock_balance = 5000000000000000000  # 5 cysFLR
    mock_function = MagicMock()
    mock_function.call = AsyncMock(return_value=mock_balance)
    cyclo_connector.vault_contract.functions.balanceOf = MagicMock(
        return_value=mock_function
    )

    # Execute
    result = await cyclo_connector.get_cysflr_balance(
        "0x742d35Cc6634C0532925a3b844Bc454e4438f44e"
    )

    # Verify
    assert result == mock_balance
    cyclo_connector.vault_contract.functions.balanceOf.assert_called_once()


@pytest.mark.asyncio
async def test_get_cysflr_balance_no_vault_contract(cyclo_connector):
    """Test balance query fails when vault contract not initialized."""
    cyclo_connector.vault_contract = None

    with pytest.raises(CycloError, match="vault contract not initialized"):
        await cyclo_connector.get_cysflr_balance(
            "0x742d35Cc6634C0532925a3b844Bc454e4438f44e"
        )


@pytest.mark.asyncio
async def test_get_receipt_balance(cyclo_connector):
    """Test getting receipt NFT balance."""
    # Setup mock
    mock_balance = 10  # 10 receipt NFTs
    mock_function = MagicMock()
    mock_function.call = AsyncMock(return_value=mock_balance)
    cyclo_connector.receipt_contract.functions.balanceOf = MagicMock(
        return_value=mock_function
    )

    # Execute
    result = await cyclo_connector.get_receipt_balance(
        "0x742d35Cc6634C0532925a3b844Bc454e4438f44e", receipt_id=12345
    )

    # Verify
    assert result == mock_balance
    cyclo_connector.receipt_contract.functions.balanceOf.assert_called_once()


@pytest.mark.asyncio
async def test_get_receipt_balance_no_receipt_contract(cyclo_connector):
    """Test receipt balance query fails when receipt contract not initialized."""
    cyclo_connector.receipt_contract = None

    with pytest.raises(CycloError, match="receipt contract not initialized"):
        await cyclo_connector.get_receipt_balance(
            "0x742d35Cc6634C0532925a3b844Bc454e4438f44e", receipt_id=12345
        )


@pytest.mark.asyncio
async def test_get_vault_asset(cyclo_connector):
    """Test getting vault asset address."""
    # Setup mock
    mock_asset = "0x12D54339D4f2926f5d3D3b18B47E1B94F83C58B0"  # sFLR address
    mock_function = MagicMock()
    mock_function.call = AsyncMock(return_value=mock_asset)
    cyclo_connector.vault_contract.functions.asset = MagicMock(
        return_value=mock_function
    )

    # Execute
    result = await cyclo_connector.get_vault_asset()

    # Verify
    assert result == mock_asset
    cyclo_connector.vault_contract.functions.asset.assert_called_once()


@pytest.mark.asyncio
async def test_get_vault_asset_no_vault_contract(cyclo_connector):
    """Test asset query fails when vault contract not initialized."""
    cyclo_connector.vault_contract = None

    with pytest.raises(CycloError, match="vault contract not initialized"):
        await cyclo_connector.get_vault_asset()
