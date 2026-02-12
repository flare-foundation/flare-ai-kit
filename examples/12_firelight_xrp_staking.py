"""Example: Using Firelight XRP staking protocol on Flare."""

import asyncio

from flare_ai_kit.ecosystem import Firelight
from flare_ai_kit.ecosystem.settings import EcosystemSettings


async def firelight_staking_example() -> None:  # noqa: PLR0915
    """
    Demonstrate Firelight XRP staking operations.

    This example shows how to:
    1. Initialize the Firelight connector
    2. Check stXRP balance and total staked
    3. Stake FXRP to receive stXRP
    4. Request withdrawal (with period cooldown)
    5. Claim withdrawal after period ends
    """
    # Initialize settings
    settings = EcosystemSettings(
        wallet_address="YOUR_WALLET_ADDRESS",
        private_key="YOUR_PRIVATE_KEY",
    )

    # Create Firelight connector
    print("Initializing Firelight connector...")
    firelight = await Firelight.create(settings)
    print("✓ Firelight connector initialized\n")

    # Get user address
    user_address = settings.wallet_address

    # --- 1. Check Current Balances ---
    print("=" * 60)
    print("1. CHECKING BALANCES")
    print("=" * 60)

    stxrp_balance = await firelight.get_stxrp_balance(user_address)
    print(f"Your stXRP balance: {stxrp_balance / 10**18:.6f} stXRP")

    total_staked = await firelight.get_total_assets()
    print(f"Total FXRP staked in vault: {total_staked / 10**18:.2f} FXRP")
    print()

    # --- 2. Get Current Period Info ---
    print("=" * 60)
    print("2. WITHDRAWAL PERIOD INFO")
    print("=" * 60)

    current_period = await firelight.get_current_period()
    print(f"Current withdrawal period: {current_period}")
    print()

    # --- 3. Stake FXRP ---
    print("=" * 60)
    print("3. STAKING FXRP (XRP)")
    print("=" * 60)

    # IMPORTANT: Before staking, you need FXRP (wrapped XRP on Flare)
    # Get FXRP from Flare's FAssets bridge or DEXes

    stake_amount = 100 * 10**18  # Stake 100 FXRP
    print(f"Staking {stake_amount / 10**18} FXRP...")
    print("Note: Make sure you've approved the vault to spend your FXRP!")

    # Uncomment to actually stake:
    # tx_hash = await firelight.stake_xrp(stake_amount)  # noqa: ERA001
    # print(f"✓ Staked successfully!")  # noqa: ERA001
    # print(f"  Transaction: {tx_hash}")  # noqa: ERA001

    print("(Skipped in example - uncomment to execute)")
    print()

    # --- 4. Request Withdrawal ---
    print("=" * 60)
    print("4. REQUESTING WITHDRAWAL")
    print("=" * 60)

    withdrawal_amount = 50 * 10**18  # Request 50 FXRP
    print(f"Requesting withdrawal of {withdrawal_amount / 10**18} FXRP...")
    print("Note: Withdrawal will be available in the next period!")

    # Uncomment to actually request withdrawal:
    # tx_hash = await firelight.request_withdrawal(withdrawal_amount)  # noqa: ERA001
    # print(f"✓ Withdrawal requested!")  # noqa: ERA001
    # print(f"  Transaction: {tx_hash}")  # noqa: ERA001

    print("(Skipped in example - uncomment to execute)")
    print()

    # --- 5. Check Pending Withdrawals ---
    print("=" * 60)
    print("5. CHECKING PENDING WITHDRAWALS")
    print("=" * 60)

    # Check if we have any pending withdrawals in previous period
    if current_period > 0:
        pending = await firelight.get_pending_withdrawal(
            current_period - 1, user_address
        )
        if pending > 0:
            print(
                f"Pending withdrawal in period {current_period - 1}: "
                f"{pending / 10**18} FXRP"
            )
            print("Ready to claim!")
        else:
            print("No pending withdrawals in the previous period.")
    print()

    # --- 6. Claim Withdrawal ---
    print("=" * 60)
    print("6. CLAIMING WITHDRAWAL")
    print("=" * 60)

    claim_period = current_period - 1  # Claim from previous period
    print(f"Claiming withdrawal from period {claim_period}...")

    # Uncomment to actually claim:
    # tx_hash = await firelight.claim_withdrawal(claim_period)  # noqa: ERA001
    # print(f"✓ Withdrawal claimed!")  # noqa: ERA001
    # print(f"  Transaction: {tx_hash}")  # noqa: ERA001

    print("(Skipped in example - uncomment to execute)")
    print()

    # --- 7. Final Summary ---
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print("Firelight XRP Staking:")
    print("  • Stake FXRP (wrapped XRP) to earn rewards and provide DeFi cover")
    print("  • Receive stXRP (liquid staking token)")
    print("  • Use stXRP in DeFi while still earning rewards")
    print("  • Request withdrawal → wait 1 period → claim")
    print("  • Supports Flare's DeFi ecosystem with risk coverage")
    print()
    print("XRP TO THE MOON! 🚀")


if __name__ == "__main__":
    asyncio.run(firelight_staking_example())
