import asyncio
import time
from typing import Any

from web3 import Web3

from flare_ai_kit import FlareAIKit
from flare_ai_kit.common import FAssetType
from flare_ai_kit.common.schemas import FAssetInfo
from flare_ai_kit.ecosystem.protocols.fassets import FAssets


async def print_supported_fassets(fassets: FAssets) -> None:
    """Print information about supported FAssets."""
    print("=== Supported FAssets ===")
    supported_fassets = await fassets.get_supported_fassets()

    for symbol, info in supported_fassets.items():
        print(f"{symbol}: {info.name}")
        print(f"  Underlying: {info.underlying_symbol}")
        print(f"  Decimals: {info.decimals}")
        print(f"  Active: {info.is_active}")
        print(f"  Asset Manager: {info.asset_manager_address}")
        print(f"  FAsset Token: {info.f_asset_address}")
        print()


async def check_balance_and_allowance(fassets: FAssets) -> None:
    """Check FXRP balance and SparkDEX allowance."""
    print("=== Balance & Allowance Operations ===")
    if not fassets.address:
        print("No account address configured - skipping balance checks")
        return

    try:
        # Check FXRP balance
        balance = await fassets.get_fasset_balance(FAssetType.FXRP, fassets.address)
        print(f"FXRP Balance: {balance} wei")

        # Check allowance for SparkDEX router (if configured)
        if fassets.sparkdex_router:
            allowance = await fassets.get_fasset_allowance(
                FAssetType.FXRP,
                fassets.address,
                fassets.sparkdex_router.address,
            )
            print(f"FXRP Allowance for SparkDEX: {allowance} wei")
        else:
            print("SparkDEX router not configured - skipping allowance check")
    except Exception as e:
        print(f"Balance/allowance check failed (expected with placeholders): {e}")


async def perform_swap_operations(
    fassets: FAssets, supported_fassets: dict[str, FAssetInfo]
) -> None:
    """Demonstrate various swap operations."""
    print("=== Swap Operations (SparkDEX Integration) ===")
    try:
        # Example swap parameters
        swap_amount = 1000000  # 1 FXRP (6 decimals)
        min_native_out = 500000000000000000  # 0.5 FLR/SGB
        deadline = int(time.time()) + 3600  # 1 hour from now

        print("1. Swap FXRP for Native Token (FLR/SGB)")
        tx_hash = await fassets.swap_fasset_for_native(
            FAssetType.FXRP,
            swap_amount,
            min_native_out,
            deadline,
        )
        print(f"   Transaction: {tx_hash}")

        print("2. Swap Native Token for FXRP")
        native_amount = 1000000000000000000  # 1 FLR/SGB
        min_fxrp_out = 900000  # 0.9 FXRP
        tx_hash = await fassets.swap_native_for_fasset(
            FAssetType.FXRP,
            min_fxrp_out,
            deadline,
            native_amount,
        )
        print(f"   Transaction: {tx_hash}")

        # Cross-FAsset swap (if multiple FAssets available)
        if len(supported_fassets) > 1:
            other_fassets = [k for k in supported_fassets if k != "FXRP"]
            if other_fassets:
                other_fasset = getattr(FAssetType, other_fassets[0])
                print(f"3. Swap FXRP for {other_fassets[0]}")
                tx_hash = await fassets.swap_fasset_for_fasset(
                    FAssetType.FXRP,
                    other_fasset,
                    swap_amount,
                    500000,  # Adjust based on decimals
                    deadline,
                )
                print(f"   Transaction: {tx_hash}")

    except Exception as e:
        print(f"Swap operations failed (expected with placeholders): {e}")


async def demonstrate_minting_workflow(fassets: FAssets) -> None:
    """Demonstrate the complete minting workflow."""
    print("=== Complete Minting Workflow ===")
    try:
        # Get all agents
        agents = await fassets.get_all_agents(FAssetType.FXRP)
        print(f"Available Agents: {len(agents)}")

        if not agents:
            print("No agents available")
            return

        agent_address = agents[0]
        # Get available lots
        available_lots: dict[str, Any] = await fassets.get_available_lots(
            FAssetType.FXRP, agent_address
        )
        print(f"Available lots from {agent_address}: {available_lots}")

        # Step 1: Reserve collateral for minting
        print("Step 1: Reserve Collateral")
        executor = fassets.address or Web3.to_checksum_address(
            "0x0000000000000000000000000000000000000000"
        )
        reservation_id = await fassets.reserve_collateral(
            FAssetType.FXRP,
            agent_address,
            1,
            100,  # 1%
            executor,
        )
        print(f"Collateral Reservation ID: {reservation_id}")

        # Step 2: Execute minting (after underlying payment)
        print("Step 2: Execute Minting")
        payment_reference = (
            "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        )
        minted_amount = await fassets.execute_minting(
            FAssetType.FXRP,
            int(reservation_id.get("reservation_id", 0)),
            payment_reference,
            executor,
        )
        print(f"Minted Amount: {minted_amount} wei")

    except Exception as e:
        print(f"Minting workflow failed (expected with placeholders): {e}")


async def perform_redemption_operations(fassets: FAssets) -> None:
    """Demonstrate redemption operations."""
    print("=== Redemption Operations ===")
    try:
        executor = fassets.address or Web3.to_checksum_address(
            "0x0000000000000000000000000000000000000000"
        )
        # Redeem FAssets back to underlying
        redemption_id = await fassets.redeem_from_agent(
            FAssetType.FXRP,
            1,
            100,  # 1%
            "rXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",  # XRP address
            executor,
        )
        print(f"Redemption Request ID: {redemption_id}")

        # Get redemption request details
        request_id = int(redemption_id.get("request_id", 0))
        if request_id > 0:
            redemption_details: dict[str, Any] = await fassets.get_redemption_request(
                FAssetType.FXRP, request_id
            )
            print("Redemption Details:")
            print(f"  Agent Vault: {redemption_details['agent_vault']}")
            print(f"  Value UBA: {redemption_details['value_uba']}")
            print(f"  Fee UBA: {redemption_details['fee_uba']}")
            print(f"  Payment Address: {redemption_details['payment_address']}")

    except Exception as e:
        print(f"Redemption operations failed (expected with placeholders): {e}")


async def check_other_fassets(
    fassets: FAssets, supported_fassets: dict[str, FAssetInfo]
) -> None:
    """Check status of other FAssets like FBTC and FDOGE."""
    # Check for FBTC on Flare Mainnet
    if "FBTC" in supported_fassets:
        print("=== FBTC Operations ===")
        try:
            fbtc_info = await fassets.get_fasset_info(FAssetType.FBTC)
            print(f"FBTC Info: {fbtc_info}")
            status = "Coming Soon" if not fbtc_info.is_active else "Active"
            print(f"Status: {status}")
        except Exception as e:
            print(f"Error with FBTC operations: {e}")
        print()

    # Check for FDOGE on Flare Mainnet
    if "FDOGE" in supported_fassets:
        print("=== FDOGE Operations ===")
        try:
            fdoge_info = await fassets.get_fasset_info(FAssetType.FDOGE)
            print(f"FDOGE Info: {fdoge_info}")
            status = "Coming Soon" if not fdoge_info.is_active else "Active"
            print(f"Status: {status}")
        except Exception as e:
            print(f"Error with FDOGE operations: {e}")
        print()


async def demonstrate_fxrp_operations(
    fassets: FAssets, supported_fassets: dict[str, FAssetInfo]
) -> None:
    """Demonstrate comprehensive FXRP operations."""
    print("=== FXRP Operations ===")
    try:
        # Get FXRP specific information
        fxrp_info = await fassets.get_fasset_info(FAssetType.FXRP)
        print(f"FXRP Info: {fxrp_info}")

        # Get asset manager settings
        settings = await fassets.get_asset_manager_settings(FAssetType.FXRP)
        print("Asset Manager Settings:")
        print(f"  Asset Name: {settings.get('asset_name')}")
        print(f"  Asset Symbol: {settings.get('asset_symbol')}")
        print(f"  Lot Size: {settings.get('lot_size_amg')}")
        cr_value = settings.get("minting_vault_collateral_ratio")
        print(f"  Minting Vault CR: {cr_value}")
        print()

        await check_balance_and_allowance(fassets)
        print()

        await perform_swap_operations(fassets, supported_fassets)
        print()

        await demonstrate_minting_workflow(fassets)
        print()

        await perform_redemption_operations(fassets)
        print()

    except Exception as e:
        msg = "Error with FXRP operations (expected with placeholder addresses)"
        print(f"{msg}: {e}")


async def main() -> None:
    """
    Comprehensive FAssets operations example - including swaps and redemptions.

    This example demonstrates:
    1. Querying supported assets and agent information
    2. Balance and allowance checks
    3. FAsset swap operations using SparkDEX
    4. Minting and redemption workflows

    Note: This example uses placeholder contract addresses. For real usage,
    update the contract addresses in the FAssets connector with actual
    deployed addresses.
    """
    # Initialize the Flare AI Kit with default settings
    kit = FlareAIKit(None)

    try:
        # Get the FAssets connector
        fassets = await kit.fassets

        # Get and display supported FAssets
        supported_fassets = await fassets.get_supported_fassets()
        await print_supported_fassets(fassets)

        # If FXRP is supported, demonstrate comprehensive operations
        if "FXRP" in supported_fassets:
            await demonstrate_fxrp_operations(fassets, supported_fassets)

        # Check other FAssets
        await check_other_fassets(fassets, supported_fassets)

    except Exception as e:
        print(f"Fatal error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
