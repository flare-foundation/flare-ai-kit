"""DA Layer usage examples."""

import asyncio

from flare_ai_kit.common import AttestationNotFoundError, DALayerError
from flare_ai_kit.ecosystem import DataAvailabilityLayer
from flare_ai_kit.ecosystem.settings import EcosystemSettings


async def voting_round(dal: DataAvailabilityLayer) -> int:
    voting_round = await dal.get_latest_voting_round()
    print(
        f"Latest voting round ID: {voting_round.voting_round_id} at "
        f"TS: {voting_round.start_timestamp}"
    )
    return voting_round.voting_round_id


async def list_feeds(dal: DataAvailabilityLayer) -> None:
    feeds = await dal.get_ftso_anchor_feed_names()
    print(f"✅ Found {len(feeds)} feeds. Showing first 10:")
    for f in feeds[:10]:  # show a few
        print(f"  • {f.feed_id} ({f.feed_name})")


async def fetch_feeds_with_proof(
    dal: DataAvailabilityLayer,
    voting_round: int,
    feed_ids: list[str],
) -> None:
    try:
        res = await dal.get_ftso_anchor_feeds_with_proof(feed_ids)
    except AttestationNotFoundError:
        print(f"❌ No attestation found for round {voting_round}")
        return
    except DALayerError as e:
        print(f"❌ DA Layer error: {e}")
        return

    print(f"✅ Round {res[0].body.voting_round_id}")
    print(f"   Feeds returned: {len(res)}")
    for feed in res:
        print(
            f"  • {feed.body.feed_id}: value={feed.body.value}, "
            f"decimals={feed.body.decimals}"
        )


async def main() -> None:
    # Demo inputs (change as needed)
    feed_ids = [
        "0x01464c522f55534400000000000000000000000000",
        "0x014254432f55534400000000000000000000000000",
    ]

    settings = EcosystemSettings()  # typically reads env vars
    dal = await DataAvailabilityLayer.create(settings)
    try:
        latest_round = await voting_round(dal)
        await list_feeds(dal)
        await fetch_feeds_with_proof(dal, latest_round, feed_ids)  # filtered
    finally:
        await dal.close()


if __name__ == "__main__":
    asyncio.run(main())
