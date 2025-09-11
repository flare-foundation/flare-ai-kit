#!/usr/bin/env python3
"""
FTSO Price Fetching Script

This script demonstrates fetching cryptocurrency prices from the FTSOv2 oracle.
Requires: ftso extras (core dependencies only)

Usage:
    python scripts/ftso_price.py

Environment Variables:
    ECOSYSTEM__FLARE_RPC_URL: Flare network RPC URL
    ECOSYSTEM__COSTON2_RPC_URL: Coston2 testnet RPC URL (optional)
"""

import asyncio
import sys
from pathlib import Path

# Add src to path for local development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from flare_ai_kit import FlareAIKit
from flare_ai_kit.config import AppSettings


async def main() -> None:
    """
    Fetching prices from the FTSOv2 oracle.

    For a full list of feeds: https://dev.flare.network/ftso/feeds
    """
    print("🔍 Initializing Flare AI Kit for FTSO price fetching...")
    
    # Initialize the Flare AI Kit
    kit = FlareAIKit(AppSettings())

    # Get the latest price for FLR/USD from the FTSOv2 oracle
    try:
        print("📊 Fetching FLR/USD price...")
        ftso = await kit.ftso
        price = await ftso.get_latest_price("FLR/USD")
        print(f"✅ Latest FLR/USD price: {price}")
    except Exception as e:
        print(f"❌ Error fetching FLR/USD price: {e}")
        return

    # Get the latest price for BTC/USD, ETH/USD and SOL/USD from the FTSOv2 oracle
    try:
        print("📊 Fetching multiple cryptocurrency prices...")
        ftso = await kit.ftso
        prices = await ftso.get_latest_prices(["BTC/USD", "ETH/USD", "SOL/USD"])
        print(f"✅ Latest BTC/USD price: {prices[0]}")
        print(f"✅ Latest ETH/USD price: {prices[1]}")
        print(f"✅ Latest SOL/USD price: {prices[2]}")
    except Exception as e:
        print(f"❌ Error fetching multiple prices: {e}")

    print("🎉 FTSO price fetching completed!")


if __name__ == "__main__":
    asyncio.run(main())
