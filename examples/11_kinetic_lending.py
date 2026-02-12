"""Example: Using Kinetic lending protocol on Flare."""

import asyncio

from flare_ai_kit.ecosystem import Kinetic
from flare_ai_kit.ecosystem.settings import EcosystemSettings


async def kinetic_lending_example() -> None:  # noqa: PLR0915
    """
    Demonstrate Kinetic lending protocol operations.

    This example shows how to:
    1. Initialize the Kinetic connector
    2. Check balances (ksFLR and underlying sFLR)
    3. Get exchange rate and supply APY
    4. Supply sFLR to earn interest
    5. Redeem ksFLR back to sFLR
    """
    # Initialize settings
    settings = EcosystemSettings(
        wallet_address="YOUR_WALLET_ADDRESS",
        private_key="YOUR_PRIVATE_KEY",
    )

    # Create Kinetic connector
    print("Initializing Kinetic connector for ksFLR market...")
    kinetic = await Kinetic.create(settings)
    print("✓ Kinetic connector initialized\n")

    # Get user address
    user_address = settings.wallet_address

    # --- 1. Check Current Balances ---
    print("=" * 60)
    print("1. CHECKING BALANCES")
    print("=" * 60)

    ksflr_balance = await kinetic.get_balance(user_address)
    print(f"Your ksFLR balance: {ksflr_balance / 10**18:.6f} ksFLR")

    underlying_balance = await kinetic.get_underlying_balance(user_address)
    print(f"Underlying sFLR: {underlying_balance / 10**18:.6f} sFLR")
    print()

    # --- 2. Get Market Info ---
    print("=" * 60)
    print("2. MARKET INFORMATION")
    print("=" * 60)

    exchange_rate = await kinetic.get_exchange_rate()
    print(f"Exchange Rate: 1 ksFLR = {exchange_rate / 10**18:.6f} sFLR")

    supply_rate = await kinetic.get_supply_rate()
    # Convert to APY (assuming ~15,768,000 blocks per year on Flare)
    blocks_per_year = 15768000
    supply_apy = (supply_rate / 10**18) * blocks_per_year * 100
    print(f"Supply APY: {supply_apy:.4f}%")
    print()

    # --- 3. Supply sFLR ---
    print("=" * 60)
    print("3. SUPPLYING SFLR")
    print("=" * 60)

    # IMPORTANT: Before calling supply(), you need to:
    # 1. Have sFLR tokens (stake FLR on Sceptre first)
    # 2. Approve Kinetic ksFLR market to spend your sFLR
    # Example (not shown here):
    #   sflr_contract.approve(kinetic.KSFLR_MARKET, amount)  # noqa: ERA001

    supply_amount = 10 * 10**18  # Supply 10 sFLR
    print(f"Supplying {supply_amount / 10**18} sFLR to Kinetic...")
    print("Note: Make sure you've approved the ksFLR market to spend your sFLR!")

    # Uncomment to actually supply:
    # tx_hash = await kinetic.supply(supply_amount)  # noqa: ERA001
    # print(f"✓ Supply successful!")  # noqa: ERA001
    # print(f"  Transaction: {tx_hash}")  # noqa: ERA001

    print("(Skipped in example - uncomment to execute)")
    print()

    # --- 4. Check Updated Balances ---
    print("=" * 60)
    print("4. CHECKING UPDATED BALANCES")
    print("=" * 60)

    ksflr_balance_after = await kinetic.get_balance(user_address)
    print(f"Your ksFLR balance: {ksflr_balance_after / 10**18:.6f} ksFLR")

    underlying_balance_after = await kinetic.get_underlying_balance(user_address)
    print(f"Underlying sFLR: {underlying_balance_after / 10**18:.6f} sFLR")
    print()

    # --- 5. Redeem ksFLR ---
    print("=" * 60)
    print("5. REDEEMING KSFLR")
    print("=" * 60)

    redeem_amount = 5 * 10**18  # Redeem 5 ksFLR
    print(f"Redeeming {redeem_amount / 10**18} ksFLR...")

    # Uncomment to actually redeem:
    # tx_hash = await kinetic.redeem(redeem_amount)  # noqa: ERA001
    # print(f"✓ Redeem successful!")  # noqa: ERA001
    # print(f"  Transaction: {tx_hash}")  # noqa: ERA001

    print("(Skipped in example - uncomment to execute)")
    print()

    # --- 6. Final Summary ---
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print("Kinetic Lending:")
    print("  • Supply sFLR to ksFLR market to earn interest")
    print("  • Your sFLR balance grows over time (increasing exchange rate)")
    print("  • Redeem ksFLR anytime to withdraw your sFLR + interest")
    print("  • No lockup period - fully liquid")
    print()


if __name__ == "__main__":
    asyncio.run(kinetic_lending_example())
