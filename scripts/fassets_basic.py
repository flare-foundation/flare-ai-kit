#!/usr/bin/env python3
"""
FAssets Basic Operations Script.

This script demonstrates comprehensive FAssets operations including minting,
redemption, and swap operations using SparkDEX integration.
Requires: fassets extras (core dependencies only)

Usage:
    python scripts/fassets_basic.py

Environment Variables:
    ECOSYSTEM__FLARE_RPC_URL: Flare network RPC URL
    ECOSYSTEM__COSTON2_RPC_URL: Coston2 testnet RPC URL (optional)
"""

import asyncio
import sys
import time
from pathlib import Path

# Add src to path for local development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from web3 import Web3

from flare_ai_kit import FlareAIKit
from flare_ai_kit.common import FAssetType
from flare_ai_kit.common.schemas import FAssetInfo
from flare_ai_kit.ecosystem.protocols.fassets import FAssets


async def print_supported_fassets(fassets: FAssets) -> None:
    """Print information about supported FAssets."""
    supported_fassets = await fassets.get_supported_fassets()

    for _info in supported_fassets.values():
        pass


async def check_balance_and_allowance(fassets: FAssets) -> None:
    """Check FXRP balance and SparkDEX allowance."""
    if not fassets.address:
        return

    try:
        # Check FXRP balance
        await fassets.get_fasset_balance(FAssetType.FXRP, fassets.address)

        # Check allowance for SparkDEX router (if configured)
        if fassets.sparkdex_router:
            await fassets.get_fasset_allowance(
                FAssetType.FXRP,
                fassets.address,
                fassets.sparkdex_router.address,
            )
        else:
            pass
    except Exception:
        pass


async def perform_swap_operations(
    fassets: FAssets, supported_fassets: dict[str, FAssetInfo]
) -> None:
    """Demonstrate various swap operations."""
    try:
        # Example swap parameters
        swap_amount = 1000000  # 1 FXRP (6 decimals)
        min_native_out = 500000000000000000  # 0.5 FLR/SGB
        deadline = int(time.time()) + 3600  # 1 hour from now

        await fassets.swap_fasset_for_native(
            FAssetType.FXRP,
            amount_in=swap_amount,
            amount_out_min=min_native_out,
            deadline=deadline,
        )

        native_amount = 1000000000000000000  # 1 FLR/SGB
        min_fxrp_out = 900000  # 0.9 FXRP
        await fassets.swap_native_for_fasset(
            FAssetType.FXRP,
            amount_out_min=min_fxrp_out,
            deadline=deadline,
            amount_in=native_amount,
        )

        # Cross-FAsset swap (if multiple FAssets available)
        if len(supported_fassets) > 1:
            other_fassets = [k for k in supported_fassets if k != "FXRP"]
            if other_fassets:
                other_fasset = getattr(FAssetType, other_fassets[0])
                await fassets.swap_fasset_for_fasset(
                    FAssetType.FXRP,
                    other_fasset,
                    amount_in=swap_amount,
                    amount_out_min=500000,  # Adjust based on decimals
                    deadline=deadline,
                )

    except Exception:
        pass


async def demonstrate_minting_workflow(fassets: FAssets) -> None:
    """Demonstrate the complete minting workflow."""
    try:
        # Get all agents
        agents = await fassets.get_all_agents(FAssetType.FXRP)

        if not agents:
            return

        agent_address = agents[0]
        # Get available lots
        await fassets.get_available_lots(FAssetType.FXRP, agent_address)

        # Step 1: Reserve collateral for minting
        executor = fassets.address or Web3.to_checksum_address(
            "0x0000000000000000000000000000000000000000"
        )
        reservation_id = await fassets.reserve_collateral(
            FAssetType.FXRP,
            agent_vault=agent_address,
            lots=1,
            max_minting_fee_bips=100,  # 1%
            executor=executor,
            executor_fee_nat=0,
        )

        # Step 2: Execute minting (after underlying payment)
        payment_reference = (
            "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        )
        await fassets.execute_minting(
            FAssetType.FXRP,
            collateral_reservation_id=int(reservation_id),
            payment_reference=payment_reference,
            recipient=executor,
        )

    except Exception:
        pass


async def perform_redemption_operations(fassets: FAssets) -> None:
    """Demonstrate redemption operations."""
    try:
        executor = fassets.address or Web3.to_checksum_address(
            "0x0000000000000000000000000000000000000000"
        )
        # Redeem FAssets back to underlying
        redemption_id = await fassets.redeem_from_agent(
            FAssetType.FXRP,
            lots=1,
            max_redemption_fee_bips=100,  # 1%
            underlying_address="rXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",  # XRP address
            executor=executor,
            executor_fee_nat=0,
        )

        # Get redemption request details
        request_id = int(redemption_id)
        if request_id > 0:
            await fassets.get_redemption_request(FAssetType.FXRP, request_id)

    except Exception:
        pass


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
    # Initialize the Flare AI Kit
    kit = FlareAIKit(config=None)

    try:
        # Get the FAssets connector
        fassets = await kit.fassets

        # Get and display supported FAssets
        supported_fassets = await fassets.get_supported_fassets()
        await print_supported_fassets(fassets)

        # If FXRP is supported, demonstrate comprehensive operations
        if "FXRP" in supported_fassets:
            try:
                # Get FXRP specific information
                await fassets.get_fasset_info(FAssetType.FXRP)

                # Get asset manager settings
                settings = await fassets.get_asset_manager_settings(FAssetType.FXRP)
                settings.get("minting_vault_collateral_ratio")

                await check_balance_and_allowance(fassets)

                await perform_swap_operations(fassets, supported_fassets)

                await demonstrate_minting_workflow(fassets)

                await perform_redemption_operations(fassets)

            except Exception:
                pass

    except Exception:
        pass


if __name__ == "__main__":
    asyncio.run(main())
