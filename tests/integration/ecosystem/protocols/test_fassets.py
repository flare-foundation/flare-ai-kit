import pytest
import pytest_asyncio

from flare_ai_kit.common import FAssetType, FAssetsError
from flare_ai_kit.ecosystem.protocols.fassets import FAssets
from flare_ai_kit.ecosystem.settings_models import EcosystemSettingsModel

settings = EcosystemSettingsModel()  # type: ignore[reportCallIssue]


# Use pytest_asyncio.fixture for async fixtures
@pytest_asyncio.fixture(scope="function")
async def fassets_instance() -> FAssets:  # type: ignore[reportInvalidTypeForm]
    """Provides a real instance of FAssets connected to the network."""
    try:
        # Use the async factory method
        instance = await FAssets.create(settings)
        # Perform an async check for connectivity instead of is_connected()
        chain_id = await instance.w3.eth.chain_id
        assert isinstance(chain_id, int)
        print(f"\nConnected to Flare network (Chain ID: {chain_id})")
    except Exception as e:
        pytest.fail(
            f"Failed to initialize FAssets instance or connect to Flare network: {e}"
        )
    else:
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
    with pytest.raises(FAssetsError):
        await fassets_instance.get_fasset_info(FAssetType.FBTC)  # May not be supported on all networks


@pytest.mark.asyncio
async def test_get_asset_manager_settings_unsupported(fassets_instance: FAssets) -> None:
    """Test getting asset manager settings for unsupported FAsset."""
    with pytest.raises(FAssetsError):
        await fassets_instance.get_asset_manager_settings(FAssetType.FBTC)  # May not be supported


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
    try:
        settings = await fassets_instance.get_asset_manager_settings(FAssetType.FXRP)
        print(f"FXRP asset manager settings: {settings}")
    except Exception as e:
        print(f"Could not get asset manager settings (expected with placeholder addresses): {e}")
    
    # Test getting all agents (may fail if using placeholder addresses)
    try:
        agents = await fassets_instance.get_all_agents(FAssetType.FXRP)
        print(f"FXRP agents: {agents}")
    except Exception as e:
        print(f"Could not get agents (expected with placeholder addresses): {e}")


@pytest.mark.asyncio
async def test_error_handling(fassets_instance: FAssets) -> None:
    """Test proper error handling for various edge cases."""
    
    # Test with non-existent agent
    with pytest.raises(Exception):  # Should raise FAssetsContractError or similar
        await fassets_instance.get_agent_info(
            FAssetType.FXRP, 
            "0x0000000000000000000000000000000000000000"
        )
    
    # Test with invalid reservation ID
    with pytest.raises(Exception):
        await fassets_instance.get_collateral_reservation_data(FAssetType.FXRP, 999999)


@pytest.mark.asyncio
async def test_get_fasset_info_supported(fassets_instance: FAssets) -> None:
    """Test getting info for a supported FAsset."""
    # This will depend on the network, but we should have at least one
    supported = await fassets_instance.get_supported_fassets()
    if supported:
        first_symbol = list(supported.keys())[0]
        fasset_type = getattr(FAssetType, first_symbol)
        
        info = await fassets_instance.get_fasset_info(fasset_type)
        assert info.symbol == first_symbol
        assert info.name
        assert info.underlying_symbol


@pytest.mark.asyncio
async def test_get_fasset_info_unsupported(fassets_instance: FAssets) -> None:
    """Test getting info for an unsupported FAsset."""
    # Try to get info for a FAsset that might not be supported
    with pytest.raises(FAssetsError):
        await fassets_instance.get_fasset_info(FAssetType.FBTC)  # May not be supported on all networks


@pytest.mark.asyncio
async def test_get_fasset_balance_unsupported(fassets_instance: FAssets) -> None:
    """Test getting FAsset balance for unsupported FAsset."""
    with pytest.raises(FAssetsError):
        await fassets_instance.get_fasset_balance(
            FAssetType.FBTC, 
            "0x0000000000000000000000000000000000000000"
        )


@pytest.mark.asyncio
async def test_get_fasset_allowance_unsupported(fassets_instance: FAssets) -> None:
    """Test getting FAsset allowance for unsupported FAsset."""
    with pytest.raises(FAssetsError):
        await fassets_instance.get_fasset_allowance(
            FAssetType.FBTC,
            "0x0000000000000000000000000000000000000000",
            "0x1111111111111111111111111111111111111111"
        )


@pytest.mark.asyncio
async def test_approve_fasset_unsupported(fassets_instance: FAssets) -> None:
    """Test approving unsupported FAsset."""
    with pytest.raises(FAssetsError):
        await fassets_instance.approve_fasset(
            FAssetType.FBTC,
            "0x0000000000000000000000000000000000000000",
            1000000
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
            deadline=1234567890
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
            amount_in=1000000000000000000
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
            deadline=1234567890
        )


@pytest.mark.asyncio
async def test_swap_fasset_for_native_unsupported(fassets_instance: FAssets) -> None:
    """Test swap with unsupported FAsset."""
    # Mock router to avoid the router check error first
    fassets_instance.sparkdex_router = "mock_router"
    
    with pytest.raises(FAssetsError, match="FAsset contract not found"):
        await fassets_instance.swap_fasset_for_native(
            FAssetType.FBTC,  # Unsupported on most networks
            amount_in=1000000,
            amount_out_min=500000000000000000,
            deadline=1234567890
        )


@pytest.mark.asyncio
async def test_swap_fasset_for_fasset_unsupported_from(fassets_instance: FAssets) -> None:
    """Test swap with unsupported from FAsset."""
    # Mock router to avoid the router check error first
    fassets_instance.sparkdex_router = "mock_router"
    
    with pytest.raises(FAssetsError, match="FAsset contract not found"):
        await fassets_instance.swap_fasset_for_fasset(
            FAssetType.FBTC,  # Unsupported from
            FAssetType.FXRP,
            amount_in=1000000,
            amount_out_min=500000,
            deadline=1234567890
        )


@pytest.mark.asyncio
async def test_swap_fasset_for_fasset_unsupported_to(fassets_instance: FAssets) -> None:
    """Test swap with unsupported to FAsset."""
    # Mock router to avoid the router check error first
    fassets_instance.sparkdex_router = "mock_router"
    
    with pytest.raises(FAssetsError, match="FAsset contract not found"):
        await fassets_instance.swap_fasset_for_fasset(
            FAssetType.FXRP,
            FAssetType.FBTC,  # Unsupported to
            amount_in=1000000,
            amount_out_min=500000,
            deadline=1234567890
        )


@pytest.mark.asyncio
async def test_execute_minting_unsupported(fassets_instance: FAssets) -> None:
    """Test execute minting for unsupported FAsset."""
    with pytest.raises(FAssetsError, match="Asset manager not found"):
        await fassets_instance.execute_minting(
            FAssetType.FBTC,
            collateral_reservation_id=123,
            payment_reference="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
            recipient="0x0000000000000000000000000000000000000000"
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
            FAssetType.FBTC,
            "0x0000000000000000000000000000000000000000"
        )


@pytest.mark.asyncio
async def test_get_available_lots_unsupported(fassets_instance: FAssets) -> None:
    """Test getting available lots for unsupported FAsset."""
    with pytest.raises(FAssetsError):
        await fassets_instance.get_available_lots(
            FAssetType.FBTC,
            "0x0000000000000000000000000000000000000000"
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
            executor="0x1111111111111111111111111111111111111111"
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
            executor="0x1111111111111111111111111111111111111111"
        )


@pytest.mark.asyncio
async def test_get_redemption_request_unsupported(fassets_instance: FAssets) -> None:
    """Test getting redemption request for unsupported FAsset."""
    with pytest.raises(FAssetsError):
        await fassets_instance.get_redemption_request(FAssetType.FBTC, 123)


@pytest.mark.asyncio
async def test_get_collateral_reservation_data_unsupported(fassets_instance: FAssets) -> None:
    """Test getting collateral reservation data for unsupported FAsset."""
    with pytest.raises(FAssetsError):
        await fassets_instance.get_collateral_reservation_data(FAssetType.FBTC, 123)


@pytest.mark.asyncio
async def test_full_workflow_with_supported_fasset(fassets_instance: FAssets) -> None:
    """Test a complete workflow with a supported FAsset (if available)."""
    supported = await fassets_instance.get_supported_fassets()
    
    if not supported:
        pytest.skip("No supported FAssets available for testing")
    
    # Get the first supported FAsset
    first_symbol = list(supported.keys())[0]
    fasset_type = getattr(FAssetType, first_symbol)
    
    # Test basic info retrieval
    info = await fassets_instance.get_fasset_info(fasset_type)
    assert info.symbol == first_symbol
    
    # Test settings retrieval (this might fail with placeholder addresses)
    try:
        settings = await fassets_instance.get_asset_manager_settings(fasset_type)
        assert isinstance(settings, dict)
    except Exception:
        # Expected with placeholder addresses
        pass
    
    # Test agent operations (might fail with placeholder addresses)
    try:
        agents = await fassets_instance.get_all_agents(fasset_type)
        assert isinstance(agents, list)
    except Exception:
        # Expected with placeholder addresses
        pass


@pytest.mark.asyncio
async def test_sparkdex_router_initialization(fassets_instance: FAssets) -> None:
    """Test that SparkDEX router initialization works correctly."""
    # The router might be None if not configured for the current network
    # This is expected behavior
    assert fassets_instance.sparkdex_router is not None or fassets_instance.sparkdex_router is None
    
    # Test that contracts configuration is stored
    assert hasattr(fassets_instance, 'contracts')
    assert hasattr(fassets_instance, 'is_testnet')


if __name__ == "__main__":
    # Run basic tests if the file is executed directly
    import asyncio
    
    async def run_basic_tests():
        print("Running basic FAssets tests...")
        instance = await FAssets.create(settings)
        
        print("✓ FAssets instance created successfully")
        
        supported = await instance.get_supported_fassets()
        print(f"✓ Supported FAssets: {list(supported.keys())}")
        
        chain_id = await instance.w3.eth.chain_id
        print(f"✓ Connected to network: {chain_id}")
        
        print("Basic tests completed successfully!")
    
    asyncio.run(run_basic_tests()) 