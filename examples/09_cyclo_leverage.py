"""Example: Cyclo non-liquidating leverage using sFLR."""

import asyncio

from flare_ai_kit import FlareAIKit
from flare_ai_kit.ecosystem.applications.cyclo import Cyclo


async def cyclo_leverage_example() -> None:
    """
    Demonstrate locking sFLR and minting cysFLR on Cyclo.

    This example shows how to use Cyclo for non-liquidating leverage.
    You'll need:
    - FLR balance for gas
    - sFLR balance to lock as collateral

    Cyclo allows you to:
    1. Lock sFLR → Mint cysFLR (trades $0-$1)
    2. Sell cysFLR for more sFLR (creates leverage)
    3. Buy back cysFLR + burn with receipt → Unlock sFLR

    Note: This is an example. Replace addresses with your own.
    """
    # Initialize FlareAIKit
    kit = FlareAIKit(None)  # Loads from .env

    # Create Cyclo connector
    cyclo: Cyclo = await Cyclo.create(kit.settings.ecosystem)

    print("=== Cyclo Leverage Example ===\n")

    # Example 1: Deposit sFLR to mint cysFLR
    print("1. Locking 10 sFLR to mint cysFLR...")
    try:
        deposit_amount = 10 * 10**18  # 10 sFLR (18 decimals)
        recipient = kit.settings.ecosystem.account_address

        tx_hash = await cyclo.deposit_sflr(
            assets=deposit_amount,
            recipient=recipient,
            min_share_ratio=0,  # No slippage protection for demo
            receipt_info=b"",  # Optional metadata
        )
        print(f"   ✅ Deposited! TX: {tx_hash}")
        print("   📝 You now have cysFLR tokens + a receipt NFT")
        print("   💡 Receipt ID = current sFLR/USD price")

    except Exception as e:
        print(f"   ❌ Deposit failed: {e}")

    # Example 2: Check balances
    print("\n2. Checking balances...")
    try:
        cysflr_balance = await cyclo.get_cysflr_balance(recipient)
        print(f"   cysFLR balance: {cysflr_balance / 10**18:.4f} cysFLR")

        # Check receipt balance for a specific ID (price at deposit time)
        # In reality, you'd track the receipt ID from the deposit event
        example_receipt_id = 15000000000000000000  # Example: 0.015 USD per sFLR
        receipt_balance = await cyclo.get_receipt_balance(recipient, example_receipt_id)
        print(f"   Receipt NFT balance (ID {example_receipt_id}): {receipt_balance}")

    except Exception as e:
        print(f"   ❌ Balance query failed: {e}")

    # Example 3: Redeem cysFLR to unlock sFLR
    print("\n3. Burning cysFLR + receipt to unlock sFLR...")
    try:
        redeem_amount = 5 * 10**18  # Redeem 5 cysFLR
        receipt_id_to_burn = 15000000000000000000  # Must match deposit price

        tx_hash = await cyclo.redeem_sflr(
            shares=redeem_amount,
            recipient=recipient,
            owner=recipient,
            receipt_id=receipt_id_to_burn,
            receipt_info=b"",
        )
        print(f"   ✅ Redeemed! TX: {tx_hash}")
        print(f"   📤 Unlocked sFLR sent to {recipient}")

    except Exception as e:
        print(f"   ❌ Redemption failed: {e}")

    # Example 4: Query vault asset
    print("\n4. Checking vault underlying asset...")
    try:
        asset_address = await cyclo.get_vault_asset()
        print(f"   Vault asset: {asset_address}")
        print("   (This should be the sFLR contract address)")

    except Exception as e:
        print(f"   ❌ Asset query failed: {e}")

    print("\n=== Example Complete ===")
    print("\nNote: In a real scenario, you would:")
    print("  1. Approve sFLR spending before deposit")
    print("  2. Approve cysFLR spending before redeem")
    print("  3. Track receipt IDs from deposit events")
    print("  4. Use actual market prices for leverage calculations")


async def main() -> None:
    """Run the example."""
    await cyclo_leverage_example()


if __name__ == "__main__":
    asyncio.run(main())
