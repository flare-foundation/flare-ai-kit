"""Example: Sceptre liquid staking for sFLR."""

import asyncio

from flare_ai_kit import FlareAIKit
from flare_ai_kit.ecosystem.applications.sceptre import Sceptre


async def sceptre_staking_example() -> None:  # noqa: PLR0915
    """
    Demonstrate FLR liquid staking using Sceptre.

    Sceptre allows you to:
    1. Stake FLR → Receive sFLR (liquid staked FLR)
    2. Use sFLR in DeFi while earning staking rewards
    3. Unstake sFLR → Request withdrawal → Wait 14.5 days → Claim FLR

    Note: This uses real contract addresses on Flare mainnet.
    """
    # Initialize FlareAIKit
    kit = FlareAIKit(None)  # Loads from .env

    # Create Sceptre connector
    sceptre: Sceptre = await Sceptre.create(kit.settings.ecosystem)

    print("=== Sceptre Liquid Staking Example ===\n")

    # Example 1: Stake FLR to receive sFLR
    print("1. Staking 10 FLR to receive sFLR...")
    try:
        stake_amount = 10 * 10**18  # 10 FLR (18 decimals)

        tx_hash = await sceptre.stake_flr(stake_amount)
        print(f"   ✅ Staked! TX: {tx_hash}")
        print("   📝 You now have sFLR tokens")
        print("   💰 sFLR earns staking rewards automatically")

    except Exception as e:
        print(f"   ❌ Staking failed: {e}")

    # Example 2: Check sFLR balance
    print("\n2. Checking sFLR balance...")
    try:
        address = kit.settings.ecosystem.account_address
        balance = await sceptre.get_sflr_balance(address)
        print(f"   sFLR balance: {balance / 10**18:.4f} sFLR")

    except Exception as e:
        print(f"   ❌ Balance query failed: {e}")

    # Example 3: Get conversion rates
    print("\n3. Checking FLR ↔ sFLR conversion rates...")
    try:
        # How much FLR is 1 sFLR worth?
        flr_per_sflr = await sceptre.get_flr_by_shares(1 * 10**18)
        print(f"   1 sFLR = {flr_per_sflr / 10**18:.6f} FLR")

        # How much sFLR would 1 FLR get you?
        sflr_per_flr = await sceptre.get_shares_by_flr(1 * 10**18)
        print(f"   1 FLR = {sflr_per_flr / 10**18:.6f} sFLR")

        # Total FLR staked in Sceptre
        total_pooled = await sceptre.get_total_pooled_flr()
        print(f"   Total staked: {total_pooled / 10**18:,.0f} FLR")

    except Exception as e:
        print(f"   ❌ Conversion query failed: {e}")

    # Example 4: Request withdrawal (starts cooldown)
    print("\n4. Requesting withdrawal (starts 14.5 day cooldown)...")
    try:
        withdraw_amount = 5 * 10**18  # 5 sFLR

        tx_hash = await sceptre.request_withdrawal(withdraw_amount)
        print(f"   ✅ Withdrawal requested! TX: {tx_hash}")
        print("   ⏳ Cooldown: ~14.5 days")
        print("   📝 Track your request ID from the transaction event")

    except Exception as e:
        print(f"   ❌ Withdrawal request failed: {e}")

    # Example 5: Claim withdrawal (after cooldown)
    print("\n5. Claiming withdrawal (after cooldown period)...")
    try:
        request_id = 0  # Get this from your withdrawal request event

        tx_hash = await sceptre.claim_withdrawal(request_id)
        print(f"   ✅ Claimed! TX: {tx_hash}")
        print("   📤 FLR sent to your wallet")

    except Exception as e:
        print(f"   ❌ Claim failed: {e}")

    print("\n=== Example Complete ===")
    print("\nNote: In a real scenario, you would:")
    print("  1. Have FLR balance for staking + gas")
    print("  2. Track withdrawal request IDs from events")
    print("  3. Wait 14.5 days between request and claim")
    print("  4. Use sFLR in DeFi (Kinetic, Cyclo, etc.)")


async def main() -> None:
    """Run the example."""
    await sceptre_staking_example()


if __name__ == "__main__":
    asyncio.run(main())
