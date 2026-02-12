"""Example: SparkDEX token swap using the V3 router."""

import asyncio
import time

from flare_ai_kit import FlareAIKit
from flare_ai_kit.ecosystem.applications.sparkdex import FEE_MEDIUM, SparkDEX


async def swap_tokens_example() -> None:
    """
    Demonstrate a token swap on SparkDEX V3.

    This example shows how to swap tokens using the exactInputSingle function.
    You'll need:
    - FLR balance for gas
    - Token balance for the input token
    - Token approval for SparkDEX router

    Note: This uses MOCK addresses. Replace with real token addresses.
    """
    print("=== SparkDEX V3 Swap Example ===\n")

    # Initialize the Flare AI Kit
    kit = FlareAIKit(None)

    try:
        # Create SparkDEX connector
        sparkdex: SparkDEX = await SparkDEX.create(kit.settings.ecosystem)
        print("✅ SparkDEX initialized")

        # Get contract addresses
        factory_address = await sparkdex.get_factory_address()
        weth9_address = await sparkdex.get_weth9_address()
        print(f"Factory: {factory_address}")
        print(f"WETH9 (Wrapped FLR): {weth9_address}\n")

        # Example swap parameters
        # ⚠️ REPLACE THESE WITH REAL TOKEN ADDRESSES
        token_in = "0x0000000000000000000000000000000000000001"  # Example token A
        token_out = weth9_address  # Swap to Wrapped FLR
        fee = FEE_MEDIUM  # 0.3% fee tier
        amount_in = 1000000000000000000  # 1 token (assuming 18 decimals)
        amount_out_minimum = 900000000000000000  # Minimum 0.9 tokens out (10% slippage)
        deadline = int(time.time()) + 3600  # 1 hour from now

        print("Swap Parameters:")
        print(f"  Token In: {token_in}")
        print(f"  Token Out: {token_out}")
        print(f"  Fee Tier: {fee / 10000}%")
        print(f"  Amount In: {amount_in / 1e18} tokens")
        print(f"  Min Amount Out: {amount_out_minimum / 1e18} tokens")
        print(f"  Deadline: {deadline}\n")

        if not sparkdex.address:
            print("⚠️  No wallet configured. Set ECOSYSTEM__ACCOUNT_ADDRESS and")
            print("    ECOSYSTEM__ACCOUNT_PRIVATE_KEY in .env to execute swaps.\n")
            return

        # Execute the swap
        print("🔄 Executing swap...")
        print("⚠️  NOTE: This will FAIL without:")
        print("    1. Real token addresses")
        print("    2. Token balance in your wallet")
        print("    3. Token approval for SparkDEX router")
        print("    4. Sufficient FLR for gas\n")

        print("✅ Example completed (uncomment the code below to execute swap)")
        print("   Note: Swap code intentionally omitted - add real addresses first")

    except Exception as e:
        print(f"❌ Error: {e}")


async def main() -> None:
    """
    Main function demonstrating SparkDEX usage.

    For production use:
    1. Replace mock token addresses with real ones
    2. Check token balances before swapping
    3. Approve SparkDEX router to spend your tokens
    4. Adjust slippage tolerance based on market conditions
    5. Use appropriate fee tier (500/3000/10000)
    """
    await swap_tokens_example()


if __name__ == "__main__":
    asyncio.run(main())
