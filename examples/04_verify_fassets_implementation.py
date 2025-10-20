"""
Verification script for FAssets implementation.

This script tests the FAssets adapter to ensure it can:
1. Connect to the test network
2. Get supported FAssets
3. Handle unsupported assets properly
4. Validate error handling
"""

import asyncio
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypeVar

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

from eth_account import Account
from pydantic import HttpUrl
from web3 import Web3

from flare_ai_kit.common.exceptions import FAssetsError
from flare_ai_kit.common.schemas import (
    AgentInfo,
    FAssetType,
)
from flare_ai_kit.ecosystem.protocols.fassets import FAssets
from flare_ai_kit.ecosystem.settings import EcosystemSettings

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

logger = logging.getLogger(__name__)

T = TypeVar("T")


def create_test_settings() -> EcosystemSettings:
    """Create test settings for Coston2 network."""
    # Use a test account with no real value
    Account.enable_unaudited_hdwallet_features()
    account = Account.from_mnemonic(
        "test test test test test test test test test test test junk"
    )
    return EcosystemSettings(
        is_testnet=True,
        web3_provider_url=HttpUrl("https://coston-api.flare.network/ext/bc/C/rpc"),
        web3_provider_timeout=5,
        block_explorer_url=HttpUrl("https://coston-explorer.flare.network/api"),
        block_explorer_timeout=10,
        max_retries=3,
        retry_delay=5,
        account_private_key=account.key.hex(),
        account_address=account.address,
    )


async def test_connectivity(fassets: FAssets) -> bool:
    """Test basic connectivity to the network."""
    try:
        # Test connection by getting block number
        block_number = await fassets.w3.eth.block_number
        logger.info("Connected to network. Current block: %d", block_number)

        # Check account
        account = Account.from_key(fassets.private_key)
        balance_wei = await fassets.w3.eth.get_balance(account.address)
        balance_eth = Web3.from_wei(balance_wei, "ether")
        logger.info("Account address: %s", account.address)
        logger.info("Account balance: %f C2FLR", balance_eth)
    except (FAssetsError, Exception):
        logger.exception("Connectivity test failed")
        return False
    return True


async def test_supported_fassets(fassets: FAssets) -> bool:
    """Test getting supported FAssets."""
    try:
        supported = await fassets.get_supported_fassets()
        logger.info("Found %d supported FAsset(s):", len(supported))

        for asset_type, info in supported.items():
            logger.info("  - %s: %s (%s)", asset_type, info.name, info.symbol)

        _ = await fassets.get_supported_fassets()
    except FAssetsError:
        logger.exception("Failed to get supported FAssets")
        return False
    return True


async def test_asset_info(fassets: FAssets) -> bool:
    """Test getting asset information."""
    try:
        # Test supported asset
        supported = await fassets.get_supported_fassets()

        for asset_type in supported:
            try:
                fasset_type = FAssetType(asset_type)
                info = await fassets.get_fasset_info(fasset_type)
                logger.info("\n%s Asset Info:", fasset_type.value)
                logger.info("  - Name: %s", info.name)
                logger.info("  - Symbol: %s", info.symbol)
                logger.info("  - Decimals: %d", info.decimals)
                logger.info("  - Asset Manager: %s", info.asset_manager_address)
                logger.info("  - FAsset Token: %s", info.f_asset_address)
                logger.info("  - Active: %s", info.is_active)
            except FAssetsError:
                logger.exception("Failed to get info for %s", asset_type)

    except FAssetsError:
        logger.exception("Asset info test failed")
        return False
    return True


async def test_agent_operations(fassets: FAssets) -> bool:
    """Test agent-related operations."""
    try:
        supported = await fassets.get_supported_fassets()

        for asset_type in supported:
            try:
                fasset_type = FAssetType(asset_type)

                # Get all agents
                agents = await fassets.get_all_agents(fasset_type)
                logger.info(
                    "\nFound %d agent(s) for %s", len(agents), fasset_type.value
                )

                # Get info for first agent if available
                if agents:
                    agent_info: AgentInfo = await fassets.get_agent_info(
                        fasset_type, agents[0]
                    )
                    logger.info("  - Agent: %s...", agents[0][:10])
                    logger.info("  - Name: %s", agent_info.name)
                    logger.info("  - Description: %s", agent_info.description)
                    logger.info("  - Fee Share: %d", agent_info.fee_share)
                    logger.info("  - Mint Count: %d", agent_info.mint_count)
                    logger.info("  - Available Lots: %d", agent_info.available_lots)

                    # Get available lots
                    lots = await fassets.get_available_lots(fasset_type, agents[0])
                    if isinstance(lots, dict):
                        logger.info(
                            "  - Total available lots: %d", lots.get("total_lots", 0)
                        )
                    else:
                        logger.info("  - Total available lots: %d", lots.total_lots)
            except FAssetsError:
                logger.exception("Agent operations failed for %s", asset_type)

    except FAssetsError:
        logger.exception("Agent operations test failed")
        return False
    return True


async def test_error_handling(fassets: FAssets) -> bool:
    """Test error handling for edge cases."""
    logger.info("\nTesting error handling...")

    try:
        # Test unsupported asset (FBTC is marked as inactive)
        try:
            _ = await fassets.get_fasset_info(FAssetType.FBTC)
        except FAssetsError as e:
            if "not supported" not in str(e):
                logger.exception("Unexpected error for unsupported asset")
                return False
            logger.info("  - Correctly handles unsupported asset")
        else:
            logger.error("Expected error for unsupported asset not raised")
            return False

        # Test swap without router initialization
        try:
            _ = await fassets.swap_fasset_for_native(FAssetType.FXRP, 1000, 500, 123456)
        except FAssetsError as e:
            if "router not initialized" not in str(e):
                logger.exception("Unexpected error for uninitialized router")
                return False
            logger.info("  - Correctly handles uninitialized router")
        else:
            logger.error("Expected error for uninitialized router not raised")
            return False

    except Exception:
        logger.exception("Unexpected error in error handling test")
        return False
    return True


async def main() -> None:
    """Run all verification tests."""
    logger.info("=" * 60)
    logger.info("FAssets Implementation Verification")
    logger.info("=" * 60)
    logger.info("Start time: %s", datetime.now(UTC).isoformat())

    try:
        # Create test settings and FAssets instance
        settings = create_test_settings()
        fassets = await FAssets.create(settings)
        logger.info("\nFAssets instance created successfully")

        # Run tests
        tests: Sequence[tuple[str, Callable[[FAssets], Any]]] = [
            ("Connectivity", test_connectivity),
            ("Supported FAssets", test_supported_fassets),
            ("Asset Info", test_asset_info),
            ("Agent Operations", test_agent_operations),
            ("Error Handling", test_error_handling),
        ]

        results: list[tuple[str, bool]] = []
        for test_name, test_func in tests:
            logger.info("\n%s", "=" * 40)
            logger.info("Running test: %s", test_name)
            try:
                result = await test_func(fassets)
                results.append((test_name, result))
                logger.info("%s: %s", test_name, "PASS" if result else "FAIL")
            except Exception:
                logger.exception("Unexpected error in test %s", test_name)
                results.append((test_name, False))

        # Print summary
        logger.info("\n%s", "=" * 40)
        logger.info("Test Summary:")
        passed = sum(1 for _, result in results if result)
        logger.info(
            "Passed: %d/%d tests (%d%%)",
            passed,
            len(results),
            int(passed * 100 / len(results)),
        )

        for test_name, result in results:
            logger.info("  - %s: %s", test_name, "PASS" if result else "FAIL")

    except Exception:
        logger.exception("Test execution failed")
        sys.exit(1)

    if not all(result for _, result in results):
        sys.exit(1)


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )
    asyncio.run(main())
