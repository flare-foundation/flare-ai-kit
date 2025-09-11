#!/usr/bin/env python3
"""
Data Availability Layer Usage Script.

This script demonstrates usage of the Data Availability Layer for retrieving
voting round data and feed information with proofs.
Requires: da extras (core dependencies only)

Usage:
    python scripts/da_layer.py

Environment Variables:
    ECOSYSTEM__FLARE_RPC_URL: Flare network RPC URL
    ECOSYSTEM__COSTON2_RPC_URL: Coston2 testnet RPC URL (optional)
"""

import asyncio
import sys
from pathlib import Path

# Add src to path for local development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from flare_ai_kit.ecosystem.protocols.da_layer import DataAvailabilityLayer
from flare_ai_kit.ecosystem.settings import EcosystemSettings


async def voting_round(dal: DataAvailabilityLayer) -> int:
    """Get the latest voting round."""
    try:
        return await dal.get_latest_voting_round()
    except Exception:
        raise


async def list_feeds(dal: DataAvailabilityLayer) -> None:
    """List available feeds."""
    try:
        feeds = await dal.list_feeds()
        for _i, _feed in enumerate(feeds[:5]):  # Show first 5 feeds
            pass
        if len(feeds) > 5:
            pass
    except Exception:
        pass


async def fetch_feeds_with_proof(
    dal: DataAvailabilityLayer, voting_round: int, feed_ids: list[str]
) -> None:
    """Fetch feeds with proof for a specific voting round."""
    try:
        feeds_with_proof = await dal.get_feeds_with_proof(voting_round, feed_ids)
        for _feed in feeds_with_proof:
            pass
    except Exception:
        pass


async def main() -> None:
    """Main function demonstrating Data Availability Layer usage."""
    # Demo inputs (change as needed)
    feed_ids = [
        "0x01464c522f55534400000000000000000000000000",  # FLR/USD
        "0x014254432f55534400000000000000000000000000",  # BTC/USD
    ]

    settings = EcosystemSettings()  # typically reads env vars
    dal = await DataAvailabilityLayer.create(settings)

    try:
        latest_round = await voting_round(dal)
        await list_feeds(dal)
        await fetch_feeds_with_proof(dal, latest_round, feed_ids)  # filtered
    except Exception:
        pass
    finally:
        await dal.close()


if __name__ == "__main__":
    asyncio.run(main())
