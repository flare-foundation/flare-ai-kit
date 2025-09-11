#!/usr/bin/env python3
"""
Data Availability Layer Usage Script

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
    print("🗳️  Fetching latest voting round...")
    try:
        latest_round = await dal.get_latest_voting_round()
        print(f"✅ Latest voting round: {latest_round}")
        return latest_round
    except Exception as e:
        print(f"❌ Error fetching voting round: {e}")
        raise


async def list_feeds(dal: DataAvailabilityLayer) -> None:
    """List available feeds."""
    print("📋 Listing available feeds...")
    try:
        feeds = await dal.list_feeds()
        print(f"✅ Found {len(feeds)} feeds:")
        for i, feed in enumerate(feeds[:5]):  # Show first 5 feeds
            print(f"   {i + 1}. {feed}")
        if len(feeds) > 5:
            print(f"   ... and {len(feeds) - 5} more feeds")
    except Exception as e:
        print(f"❌ Error listing feeds: {e}")


async def fetch_feeds_with_proof(
    dal: DataAvailabilityLayer, voting_round: int, feed_ids: list[str]
) -> None:
    """Fetch feeds with proof for a specific voting round."""
    print(f"🔍 Fetching feeds with proof for round {voting_round}...")
    try:
        feeds_with_proof = await dal.get_feeds_with_proof(voting_round, feed_ids)
        print(f"✅ Retrieved {len(feeds_with_proof)} feeds with proof:")
        for feed in feeds_with_proof:
            print(f"   Feed ID: {feed.feed_id}")
            print(f"   Value: {feed.value}")
            print(f"   Proof length: {len(feed.proof.merkle_proof)}")
    except Exception as e:
        print(f"❌ Error fetching feeds with proof: {e}")


async def main() -> None:
    """Main function demonstrating Data Availability Layer usage."""
    print("🔍 Initializing Data Availability Layer...")

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
        print("🎉 Data Availability Layer demo completed!")
    except Exception as e:
        print(f"❌ Demo failed: {e}")
    finally:
        await dal.close()


if __name__ == "__main__":
    asyncio.run(main())
