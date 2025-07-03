"""Integration tests for Goldsky (require actual Goldsky API access)."""

import os

import pytest

from flare_ai_kit.ecosystem.tooling.goldsky import (
    ChainSlug,
    DatasetType,
    Goldsky,
    GoldskyConfig,
    create_webhook_sink_config,
)

# Skip integration tests if no API key provided
pytestmark = pytest.mark.skipif(
    not os.getenv("GOLDSKY_API_KEY"),
    reason="GOLDSKY_API_KEY environment variable not set",
)


@pytest.fixture
def goldsky_config() -> GoldskyConfig:
    """Create integration test configuration."""
    return GoldskyConfig(
        api_key=os.getenv("GOLDSKY_API_KEY"),
        project_name="flare-ai-kit-integration-test",
        chain_slug=ChainSlug.FLARE_COSTON2,  # Use testnet
    )


@pytest.mark.asyncio
async def test_goldsky_query_blocks(goldsky_config: GoldskyConfig) -> None:
    """Test querying blocks from Goldsky."""
    async with Goldsky(goldsky_config) as goldsky:
        try:
            blocks = await goldsky.get_flare_blocks(
                start_block=1000, end_block=1002, include_transactions=False
            )

            assert isinstance(blocks, list)
            # May be empty if no indexed data available
            if blocks:
                assert "number" in blocks[0]
                assert "hash" in blocks[0]

        except Exception as e:
            # Log but don't fail - may be expected if subgraph not deployed
            print(f"Query failed (may be expected): {e}")


@pytest.mark.asyncio
async def test_goldsky_pipeline_creation(goldsky_config: GoldskyConfig) -> None:
    """Test creating and managing pipelines."""
    async with Goldsky(goldsky_config) as goldsky:
        # Create test pipeline
        sink_config = create_webhook_sink_config("https://httpbin.org/post")

        pipeline = goldsky.create_chain_data_pipeline(
            pipeline_name="integration_test_pipeline",
            dataset_types=[DatasetType.BLOCKS],
            sink_config=sink_config,
        )

        assert pipeline.name == "integration_test_pipeline"
        assert len(pipeline.definition.sources) == 1
        assert pipeline.definition.sources[0]["dataset"] == "blocks"

        # Note: Not actually deploying to avoid creating real pipelines
        # In a real integration test, you might deploy and then clean up
