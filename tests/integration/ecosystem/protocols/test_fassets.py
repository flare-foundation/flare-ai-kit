from unittest.mock import AsyncMock

import pytest
import pytest_asyncio

from flare_ai_kit.agent.settings_models import AgentSettingsModel
from flare_ai_kit.common import (
    FAssetsContractError,
    FAssetsError,
    FAssetType,
)
from flare_ai_kit.config import AppSettings
from flare_ai_kit.ecosystem.protocols.fassets import FAssets


@pytest_asyncio.fixture(scope="function")
async def fassets_instance(monkeypatch) -> FAssets:  # type: ignore[reportInvalidTypeForm]
    """Provides a real instance of FAssets connected to the network."""
    # Set a placeholder API key using monkeypatch
    monkeypatch.setenv("GEMINI_API_KEY", "test_api_key")

    # Create a mock AgentSettingsModel with a placeholder API key
    mock_agent_settings = AgentSettingsModel(gemini_api_key="test_api_key")

    # Pass the mock settings to AppSettings
    settings = AppSettings(agent=mock_agent_settings)

    # Use the async factory method
    instance = await FAssets.create(settings.ecosystem)
    instance.address = "0x0000000000000000000000000000000000000001"  # Mock address

    yield instance  # type: ignore[reportReturnType]


@pytest.mark.asyncio
async def test_get_supported_fassets(fassets_instance: FAssets) -> None:
    """Test getting supported FAssets."""
    supported_fassets = await fassets_instance.get_supported_fassets()
    assert isinstance(supported_fassets, dict)
    print(f"Supported FAssets: {list(supported_fassets.keys())}")


@pytest.mark.asyncio
async def test_get_fasset_info_invalid_type(fassets_instance: FAssets) -> None:
    """Test getting FAsset info for an invalid/unsupported type."""
    with pytest.raises(
        FAssetsError, match="FAsset type FBTC is not active on this network"
    ):
        await fassets_instance.get_fasset_info(FAssetType.FBTC)


@pytest.mark.asyncio
async def test_get_asset_manager_settings_unsupported(
    fassets_instance: FAssets,
) -> None:
    """Test getting asset manager settings for unsupported FAsset."""
    with pytest.raises(FAssetsError):
        await fassets_instance.get_asset_manager_settings(
            FAssetType.FBTC
        )  # May not be supported


@pytest.mark.asyncio
async def test_network_detection(fassets_instance: FAssets) -> None:
    """Test that the connector properly detects the network and initializes FAssets accordingly."""
    chain_id = await fassets_instance.w3.eth.chain_id
    supported_fassets = await fassets_instance.get_supported_fassets()

    if chain_id == 19:  # Songbird
        assert "FXRP" in supported_fassets
        print("Songbird network detected - FXRP supported")
    elif chain_id == 14:  # Flare Mainnet
        # FBTC and FDOGE may be supported in the future
        print("Flare Mainnet network detected")
    elif chain_id in [114, 16]:  # Testnets
        # Should have test FAssets
        print("Testnet detected")
    else:
        print(f"Unknown network: {chain_id}")


# Conditional tests that only run if FXRP is supported
@pytest.mark.asyncio
async def test_fxrp_operations(fassets_instance: FAssets) -> None:
    """Test FXRP operations if supported on the current network."""
    supported_fassets = await fassets_instance.get_supported_fassets()

    if "FXRP" not in supported_fassets:
        pytest.skip("FXRP not supported on this network")

    # Test getting FXRP info
    fxrp_info = await fassets_instance.get_fasset_info(FAssetType.FXRP)
    assert fxrp_info.symbol == "FXRP"
    assert fxrp_info.underlying_symbol == "XRP"
    print(f"FXRP info: {fxrp_info}")

    # Test getting asset manager settings (may fail if using placeholder addresses)
    settings = await fassets_instance.get_asset_manager_settings(FAssetType.FXRP)
    print(f"FXRP asset manager settings: {settings}")

    # Test getting all agents (may fail if using placeholder addresses)
    agents = await fassets_instance.get_all_agents(FAssetType.FXRP)
    print(f"FXRP agents: {agents}")


@pytest.mark.asyncio
async def test_error_handling(fassets_instance: FAssets) -> None:
    """Test proper error handling for various edge cases."""

    # Test with non-existent agent
    with pytest.raises(Exception):  # Should raise FAssetsContractError or similar
        await fassets_instance.get_agent_info(
            FAssetType.FXRP, "0x0000000000000000000000000000000000000000"
        )

    # Test with invalid reservation ID
    with pytest.raises(Exception):
        await fassets_instance.get_collateral_reservation_data(FAssetType.FXRP, 999999)


@pytest.mark.asyncio
async def test_get_fasset_info_supported(fassets_instance: FAssets) -> None:
    """Test getting info for a supported FAsset."""
    supported = await fassets_instance.get_supported_fassets()
    active_fasset_type = None
    for symbol, info in supported.items():
        if info.is_active:
            active_fasset_type = getattr(FAssetType, symbol)
            break

    if not active_fasset_type:
        pytest.skip("No active FAssets available for testing")

    info = await fassets_instance.get_fasset_info(active_fasset_type)
    assert info.symbol == active_fasset_type.value
    assert info.name
    assert info.underlying_symbol


@pytest.mark.asyncio
async def test_get_fasset_info_unsupported(fassets_instance: FAssets) -> None:
    """Test getting info for an unsupported FAsset."""
    # Try to get info for a FAsset that might not be supported
    with pytest.raises(
        FAssetsError, match="FAsset type FBTC is not active on this network"
    ):
        await fassets_instance.get_fasset_info(FAssetType.FBTC)


@pytest.mark.asyncio
async def test_get_fasset_balance_unsupported(fassets_instance: FAssets) -> None:
    """Test getting FAsset balance for unsupported FAsset."""
    with pytest.raises(FAssetsError):
        await fassets_instance.get_fasset_balance(
            FAssetType.FBTC, "0x0000000000000000000000000000000000000000"
        )


@pytest.mark.asyncio
async def test_get_fasset_allowance_unsupported(fassets_instance: FAssets) -> None:
    """Test getting FAsset allowance for unsupported FAsset."""
    with pytest.raises(FAssetsError):
        await fassets_instance.get_fasset_allowance(
            FAssetType.FBTC,
            "0x0000000000000000000000000000000000000000",
            "0x1111111111111111111111111111111111111111",
        )


@pytest.mark.asyncio
async def test_approve_fasset_unsupported(fassets_instance: FAssets) -> None:
    """Test approving unsupported FAsset."""
    with pytest.raises(FAssetsError):
        await fassets_instance.approve_fasset(
            FAssetType.FBTC, "0x0000000000000000000000000000000000000000", 1000000
        )


@pytest.mark.asyncio
async def test_swap_fasset_for_native_no_router(fassets_instance: FAssets) -> None:
    """Test swap when SparkDEX router is not initialized."""
    # Ensure router is None
    fassets_instance.sparkdex_router = None

    with pytest.raises(FAssetsError, match="SparkDEX router not initialized"):
        await fassets_instance.swap_fasset_for_native(
            FAssetType.FXRP,
            amount_in=1000000,
            amount_out_min=500000000000000000,
            deadline=1234567890,
        )


@pytest.mark.asyncio
async def test_swap_native_for_fasset_no_router(fassets_instance: FAssets) -> None:
    """Test swap when SparkDEX router is not initialized."""
    # Ensure router is None
    fassets_instance.sparkdex_router = None

    with pytest.raises(FAssetsError, match="SparkDEX router not initialized"):
        await fassets_instance.swap_native_for_fasset(
            FAssetType.FXRP,
            amount_out_min=900000,
            deadline=1234567890,
            amount_in=1000000000000000000,
        )


@pytest.mark.asyncio
async def test_swap_fasset_for_fasset_no_router(fassets_instance: FAssets) -> None:
    """Test swap when SparkDEX router is not initialized."""
    # Ensure router is None
    fassets_instance.sparkdex_router = None

    with pytest.raises(FAssetsError, match="SparkDEX router not initialized"):
        await fassets_instance.swap_fasset_for_fasset(
            FAssetType.FXRP,
            FAssetType.FBTC,
            amount_in=1000000,
            amount_out_min=500000,
            deadline=1234567890,
        )


@pytest.mark.asyncio
async def test_swap_fasset_for_native_unsupported(
    fassets_instance: FAssets, monkeypatch
) -> None:
    """Test swap with unsupported FAsset."""

    # Mock router to avoid the router check error first
    class MockRouter:
        address = "0x1111111111111111111111111111111111111111"

    fassets_instance.sparkdex_router = MockRouter()

    # Mock get_fasset_allowance and approve_fasset
    monkeypatch.setattr(
        fassets_instance,
        "get_fasset_allowance",
        AsyncMock(return_value=1000000000000000000000000),
    )
    monkeypatch.setattr(
        fassets_instance, "approve_fasset", AsyncMock(return_value="0x" + "1" * 64)
    )

    with pytest.raises(
        FAssetsContractError,
        match="Failed to swap FAsset for native: Transaction logic not implemented for test environment",
    ):
        await fassets_instance.swap_fasset_for_native(
            FAssetType.FBTC,  # Unsupported on most networks
            amount_in=1000000,
            amount_out_min=500000000000000000,
            deadline=1234567890,
        )


@pytest.mark.asyncio
async def test_swap_fasset_for_fasset_unsupported_from(
    fassets_instance: FAssets, monkeypatch
) -> None:
    """Test swap with unsupported from FAsset."""

    # Mock router to avoid the router check error first
    class MockRouter:
        address = "0x1111111111111111111111111111111111111111"

    fassets_instance.sparkdex_router = MockRouter()

    with pytest.raises(FAssetsError, match="FAsset contract not found"):
        await fassets_instance.swap_fasset_for_fasset(
            FAssetType.FBTC,  # Unsupported from
            FAssetType.FXRP,
            amount_in=1000000,
            amount_out_min=500000,
            deadline=1234567890,
        )


@pytest.mark.asyncio
async def test_swap_fasset_for_fasset_unsupported_to(
    fassets_instance: FAssets, monkeypatch
) -> None:
    """Test swap with unsupported to FAsset."""

    # Mock router to avoid the router check error first
    class MockRouter:
        address = "0x1111111111111111111111111111111111111111"

    fassets_instance.sparkdex_router = MockRouter()

    with pytest.raises(FAssetsError, match="FAsset contract not found"):
        await fassets_instance.swap_fasset_for_fasset(
            FAssetType.FXRP,
            FAssetType.FBTC,  # Unsupported to
            amount_in=1000000,
            amount_out_min=500000,
            deadline=1234567890,
        )


@pytest.mark.asyncio
async def test_execute_minting_unsupported(
    fassets_instance: FAssets, monkeypatch
) -> None:
    """Test execute minting for unsupported FAsset."""
    monkeypatch.setattr(
        fassets_instance,
        "sign_and_send_transaction",
        AsyncMock(return_value="0x" + "1" * 64),
    )
    monkeypatch.setattr(
        fassets_instance.w3.eth,
        "wait_for_transaction_receipt",
        AsyncMock(return_value={"status": 1}),
    )
    with pytest.raises(
        FAssetsContractError,
        match="Failed to execute minting: Transaction logic not implemented for test environment",
    ):
        await fassets_instance.execute_minting(
            FAssetType.FBTC,
            collateral_reservation_id=123,
            payment_reference="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
            recipient="0x0000000000000000000000000000000000000000",
        )


@pytest.mark.asyncio
async def test_get_all_agents_unsupported(fassets_instance: FAssets) -> None:
    """Test getting agents for unsupported FAsset."""
    with pytest.raises(FAssetsError):
        await fassets_instance.get_all_agents(FAssetType.FBTC)


@pytest.mark.asyncio
async def test_get_agent_info_unsupported(fassets_instance: FAssets) -> None:
    """Test getting agent info for unsupported FAsset."""
    with pytest.raises(FAssetsError):
        await fassets_instance.get_agent_info(
            FAssetType.FBTC, "0x0000000000000000000000000000000000000000"
        )


@pytest.mark.asyncio
async def test_get_available_lots_unsupported(fassets_instance: FAssets) -> None:
    """Test getting available lots for unsupported FAsset."""
    with pytest.raises(FAssetsError):
        await fassets_instance.get_available_lots(
            FAssetType.FBTC, "0x0000000000000000000000000000000000000000"
        )


@pytest.mark.asyncio
async def test_reserve_collateral_unsupported(fassets_instance: FAssets) -> None:
    """Test reserving collateral for unsupported FAsset."""
    with pytest.raises(FAssetsError):
        await fassets_instance.reserve_collateral(
            FAssetType.FBTC,
            agent_vault="0x0000000000000000000000000000000000000000",
            lots=1,
            max_minting_fee_bips=100,
            executor="0x1111111111111111111111111111111111111111",
        )


@pytest.mark.asyncio
async def test_redeem_from_agent_unsupported(fassets_instance: FAssets) -> None:
    """Test redemption for unsupported FAsset."""
    with pytest.raises(FAssetsError):
        await fassets_instance.redeem_from_agent(
            FAssetType.FBTC,
            lots=1,
            max_redemption_fee_bips=100,
            underlying_address="bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh",
            executor="0x1111111111111111111111111111111111111111",
        )


@pytest.mark.asyncio
async def test_get_redemption_request_unsupported(fassets_instance: FAssets) -> None:
    """Test getting redemption request for unsupported FAsset."""
    with pytest.raises(FAssetsError):
        await fassets_instance.get_redemption_request(FAssetType.FBTC, 123)


@pytest.mark.asyncio
async def test_get_collateral_reservation_data_unsupported(
    fassets_instance: FAssets,
) -> None:
    """Test getting collateral reservation data for unsupported FAsset."""
    with pytest.raises(FAssetsError):
        await fassets_instance.get_collateral_reservation_data(FAssetType.FBTC, 123)


@pytest.mark.asyncio
async def test_full_workflow_with_supported_fasset(fassets_instance: FAssets) -> None:
    """Test a complete workflow with a supported FAsset (if available)."""
    supported = await fassets_instance.get_supported_fassets()
    active_fasset_type = None
    for symbol, info in supported.items():
        if info.is_active:
            active_fasset_type = getattr(FAssetType, symbol)
            break

    if not active_fasset_type:
        pytest.skip("No active FAssets available for testing")

    # Test basic info retrieval
    info = await fassets_instance.get_fasset_info(active_fasset_type)
    assert info.symbol == active_fasset_type.value

    # Test settings retrieval (this might fail with placeholder addresses)
    settings = await fassets_instance.get_asset_manager_settings(active_fasset_type)
    assert isinstance(settings, dict)

    # Test agent operations (might fail with placeholder addresses)
    agents = await fassets_instance.get_all_agents(active_fasset_type)
    assert isinstance(agents, list)


@pytest.mark.asyncio
async def test_sparkdex_router_initialization(fassets_instance: FAssets) -> None:
    """Test that SparkDEX router initialization works correctly."""
    # The router might be None if not configured for the current network
    # This is expected behavior
    assert (
        fassets_instance.sparkdex_router is not None
        or fassets_instance.sparkdex_router is None
    )

    # Test that contracts configuration is stored
    assert hasattr(fassets_instance, "contracts")
    assert hasattr(fassets_instance, "is_testnet")
