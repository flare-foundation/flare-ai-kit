"""Example: Using Stargate cross-chain bridge on Flare."""

import asyncio

from flare_ai_kit.ecosystem import Stargate
from flare_ai_kit.ecosystem.settings import EcosystemSettings


async def stargate_bridge_example() -> None:  # noqa: PLR0915
    """
    Demonstrate Stargate cross-chain bridging information.

    This example shows how to:
    1. Get Stargate OFT token addresses on Flare
    2. Get supported destination chains and endpoint IDs
    3. View bridge configuration
    """
    # Initialize settings
    settings = EcosystemSettings(
        wallet_address="YOUR_WALLET_ADDRESS",
        private_key="YOUR_PRIVATE_KEY",
    )

    # Create Stargate connector
    print("Initializing Stargate connector...")
    stargate = await Stargate.create(settings)
    print("✓ Stargate connector initialized\n")

    # --- 1. Get Bridge Information ---
    print("=" * 60)
    print("1. STARGATE BRIDGE INFO")
    print("=" * 60)

    info = stargate.get_bridge_info()
    print(f"Network: {info['network']}")
    print(f"Endpoint ID: {info['endpoint_id']}")
    print(f"Token Messaging: {info['token_messaging']}")
    print(f"Treasurer: {info['treasurer']}")
    print()

    # --- 2. Supported Tokens ---
    print("=" * 60)
    print("2. SUPPORTED TOKENS (OFTs)")
    print("=" * 60)

    tokens = stargate.get_supported_tokens()
    print("You can bridge these tokens from Flare:")

    for token in tokens:
        oft_address = stargate.get_oft_address(token)
        print(f"  • {token}: {oft_address}")

    print()

    # --- 3. Supported Destination Chains ---
    print("=" * 60)
    print("3. SUPPORTED DESTINATION CHAINS")
    print("=" * 60)

    chains = stargate.get_supported_chains()
    print(f"You can bridge to {len(chains)} chains:")

    for chain in sorted(chains):
        endpoint = stargate.get_chain_endpoint(chain)
        print(f"  • {chain.title()}: endpoint {endpoint}")

    print()

    # --- 4. Example: Bridge ETH from Flare to Arbitrum ---
    print("=" * 60)
    print("4. EXAMPLE: BRIDGE ETH FLARE → ARBITRUM")
    print("=" * 60)

    eth_oft = stargate.get_oft_address("ETH")
    arbitrum_endpoint = stargate.get_chain_endpoint("arbitrum")

    print(f"Source Token (Flare): {eth_oft}")
    print(f"Destination Chain: Arbitrum (endpoint {arbitrum_endpoint})")
    print()
    print("To bridge:")
    print("  1. Approve ETH OFT contract to spend your tokens")
    print("  2. Call send() on the OFT contract with:")
    print(f"     - dstEid: {arbitrum_endpoint}")
    print("     - amount: your bridge amount")
    print("     - recipient: your address on Arbitrum")
    print()

    # --- 5. Example: Bridge USDC from Flare to Base ---
    print("=" * 60)
    print("5. EXAMPLE: BRIDGE USDC FLARE → BASE")
    print("=" * 60)

    usdc_oft = stargate.get_oft_address("USDC")
    base_endpoint = stargate.get_chain_endpoint("base")

    print(f"Source Token (Flare): {usdc_oft}")
    print(f"Destination Chain: Base (endpoint {base_endpoint})")
    print()

    # --- 6. Summary ---
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print("Stargate Bridge on Flare:")
    print("  • Bridge ETH, USDC, USDT to 10+ chains")
    print("  • Use LayerZero OFT (Omnichain Fungible Token) standard")
    print("  • Unified liquidity across multiple chains")
    print("  • Low fees, fast, secure bridging")
    print()
    print("Note: This connector provides bridge info for AI agents.")
    print("For actual bridging, use Stargate's frontend or OFT contracts directly.")
    print()
    print("BRIDGE ALL THE THINGS! 🌉")


if __name__ == "__main__":
    asyncio.run(stargate_bridge_example())
