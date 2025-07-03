"""Tests for Goldsky integration."""

from unittest.mock import AsyncMock, patch

import pytest

from flare_ai_kit.ecosystem.tooling.goldsky import (
    ChainSlug,
    DatasetType,
    Goldsky,
    GoldskyConfig,
    GoldskyPipeline,
    PipelineDefinition,
    create_flare_contract_filter,
    create_postgres_sink_config,
    create_webhook_sink_config,
)

# Test constants
DEFAULT_PORT = 5432
EXPECTED_BATCH_SIZE = 50
EXPECTED_ADDRESS_COUNT = 2
EXPECTED_TOPIC_COUNT = 2
TEST_PASSWORD = "test_password_123"  # Test password constant


@pytest.fixture
def goldsky_config() -> GoldskyConfig:
    """Create test Goldsky configuration."""
    return GoldskyConfig(
        api_key="test_api_key",
        project_name="test_project",
        chain_slug=ChainSlug.FLARE_COSTON2,
    )


@pytest.fixture
def goldsky_client(goldsky_config: GoldskyConfig) -> Goldsky:
    """Create test Goldsky client."""
    return Goldsky(goldsky_config)


@pytest.fixture
def sample_pipeline_definition() -> PipelineDefinition:
    """Create sample pipeline definition."""
    return PipelineDefinition(
        sources=[
            {"type": "chain-level", "chain": "flare-coston2", "dataset": "blocks"}
        ],
        sinks=[{"type": "webhook", "url": "https://example.com/webhook"}],
    )


class TestGoldskyConfig:
    """Test GoldskyConfig class."""

    def test_config_creation(self) -> None:
        """Test creating Goldsky configuration."""
        config = GoldskyConfig(api_key="test_key", project_name="test_project")

        assert config.api_key == "test_key"
        assert config.project_name == "test_project"
        assert config.chain_slug == ChainSlug.FLARE_MAINNET
        assert config.goldsky_cli_path == "goldsky"


class TestPipelineDefinition:
    """Test PipelineDefinition model."""

    def test_valid_definition(
        self, sample_pipeline_definition: PipelineDefinition
    ) -> None:
        """Test creating valid pipeline definition."""
        assert sample_pipeline_definition.version == "1"
        assert len(sample_pipeline_definition.sources) == 1
        assert len(sample_pipeline_definition.sinks) == 1

    def test_empty_sources_validation(self) -> None:
        """Test validation fails with empty sources."""
        with pytest.raises(ValueError, match="At least one source must be specified"):
            PipelineDefinition(sources=[], sinks=[{"type": "webhook"}])

    def test_empty_sinks_validation(self) -> None:
        """Test validation fails with empty sinks."""
        with pytest.raises(ValueError, match="At least one sink must be specified"):
            PipelineDefinition(sources=[{"type": "chain-level"}], sinks=[])


class TestGoldskyPipeline:
    """Test GoldskyPipeline class."""

    def test_pipeline_creation(
        self,
        goldsky_config: GoldskyConfig,
        sample_pipeline_definition: PipelineDefinition,
    ) -> None:
        """Test creating pipeline."""
        pipeline = GoldskyPipeline(
            "test_pipeline", goldsky_config, sample_pipeline_definition
        )

        assert pipeline.name == "test_pipeline"
        assert pipeline.config == goldsky_config
        assert pipeline.definition == sample_pipeline_definition

    @pytest.mark.asyncio
    @patch("asyncio.create_subprocess_exec")
    async def test_deploy_success(
        self,
        mock_subprocess: AsyncMock,
        goldsky_config: GoldskyConfig,
        sample_pipeline_definition: PipelineDefinition,
    ) -> None:
        """Test successful pipeline deployment."""
        # Mock successful process
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate.return_value = (b"Success", b"")
        mock_subprocess.return_value = mock_process

        pipeline = GoldskyPipeline(
            "test_pipeline", goldsky_config, sample_pipeline_definition
        )
        result = await pipeline.deploy()

        assert result is True

    @pytest.mark.asyncio
    @patch("asyncio.create_subprocess_exec")
    async def test_deploy_failure(
        self,
        mock_subprocess: AsyncMock,
        goldsky_config: GoldskyConfig,
        sample_pipeline_definition: PipelineDefinition,
    ) -> None:
        """Test failed pipeline deployment."""
        # Mock failed process
        mock_process = AsyncMock()
        mock_process.returncode = 1
        mock_process.communicate.return_value = (b"", b"Error occurred")
        mock_subprocess.return_value = mock_process

        pipeline = GoldskyPipeline(
            "test_pipeline", goldsky_config, sample_pipeline_definition
        )
        result = await pipeline.deploy()

        assert result is False


class TestGoldsky:
    """Test Goldsky main class."""

    def test_goldsky_creation(self, goldsky_config: GoldskyConfig) -> None:
        """Test creating Goldsky client."""
        client = Goldsky(goldsky_config)

        assert client.config == goldsky_config
        assert len(client.pipelines) == 0

    def test_create_chain_data_pipeline(self, goldsky_client: Goldsky) -> None:
        """Test creating chain data pipeline."""
        sink_config = create_webhook_sink_config("https://example.com/webhook")

        pipeline = goldsky_client.create_chain_data_pipeline(
            pipeline_name="test_blocks",
            dataset_types=[DatasetType.BLOCKS, DatasetType.LOGS],
            sink_config=sink_config,
        )

        assert pipeline.name == "test_blocks"
        assert len(pipeline.definition.sources) == EXPECTED_ADDRESS_COUNT
        assert pipeline.definition.sources[0]["dataset"] == "blocks"
        assert pipeline.definition.sources[1]["dataset"] == "logs"
        assert "test_blocks" in goldsky_client.pipelines

    def test_create_subgraph_pipeline(self, goldsky_client: Goldsky) -> None:
        """Test creating subgraph pipeline."""
        sink_config = create_postgres_sink_config(
            host="localhost", database="test_db", username="user", password="pass"
        )

        pipeline = goldsky_client.create_subgraph_pipeline(
            pipeline_name="test_subgraph",
            subgraph_name="flare/test-subgraph",
            sink_config=sink_config,
        )

        assert pipeline.name == "test_subgraph"
        assert len(pipeline.definition.sources) == 1
        assert pipeline.definition.sources[0]["type"] == "subgraph"
        assert pipeline.definition.sources[0]["name"] == "flare/test-subgraph"

    @pytest.mark.asyncio
    @patch("aiohttp.ClientSession.post")
    async def test_query_indexed_data(
        self, mock_post: AsyncMock, goldsky_client: Goldsky
    ) -> None:
        """Test querying indexed data."""
        # Mock response
        mock_response = AsyncMock()
        mock_response.json.return_value = {
            "data": {"blocks": [{"number": 1, "hash": "0x123"}]}
        }
        mock_post.return_value.__aenter__.return_value = mock_response

        query = "query { blocks { number hash } }"
        result = await goldsky_client.query_indexed_data(query)

        assert "data" in result
        assert "blocks" in result["data"]

    @pytest.mark.asyncio
    async def test_get_flare_blocks(self, goldsky_client: Goldsky) -> None:
        """Test getting Flare blocks."""
        with patch.object(goldsky_client, "query_indexed_data") as mock_query:
            mock_query.return_value = {
                "data": {
                    "blocks": [
                        {"number": 100, "hash": "0x123", "timestamp": "1234567890"},
                        {"number": 101, "hash": "0x456", "timestamp": "1234567891"},
                    ]
                }
            }

            blocks = await goldsky_client.get_flare_blocks(100, 101)

            assert len(blocks) == EXPECTED_ADDRESS_COUNT
            assert blocks[0]["number"] == 100
            assert blocks[1]["number"] == 101

    @pytest.mark.asyncio
    async def test_correlate_with_graphrag(self, goldsky_client: Goldsky) -> None:
        """Test correlation with GraphRAG."""
        blockchain_data = [
            {"transactionHash": "0x123", "value": "100"},
            {"transactionHash": "0x456", "value": "200"},
        ]

        result = await goldsky_client.correlate_with_graphrag(
            blockchain_data=blockchain_data,
            graphrag_query="MATCH (tx:Transaction) RETURN tx",
            correlation_field="transactionHash",
        )

        assert "blockchain_data" in result
        assert "graphrag_insights" in result
        assert len(result["blockchain_data"]) == EXPECTED_ADDRESS_COUNT
        assert (
            len(result["graphrag_insights"]["correlation_values"])
            == EXPECTED_ADDRESS_COUNT
        )


class TestUtilityFunctions:
    """Test utility functions."""

    def test_create_postgres_sink_config(self) -> None:
        """Test creating PostgreSQL sink configuration."""
        config = create_postgres_sink_config(
            host="localhost",
            database="test_db",
            username="user",
            password=TEST_PASSWORD,
            port=DEFAULT_PORT,
        )

        assert config["type"] == "postgres"
        assert config["connection"]["host"] == "localhost"
        assert config["connection"]["database"] == "test_db"
        assert config["table_prefix"] == "goldsky_"

    def test_create_webhook_sink_config(self) -> None:
        """Test creating webhook sink configuration."""
        config = create_webhook_sink_config(
            webhook_url="https://example.com/webhook",
            headers={"Authorization": "Bearer token"},
            batch_size=EXPECTED_BATCH_SIZE,
        )

        assert config["type"] == "webhook"
        assert config["url"] == "https://example.com/webhook"
        assert config["headers"]["Authorization"] == "Bearer token"
        assert config["batch_size"] == EXPECTED_BATCH_SIZE

    def test_create_flare_contract_filter(self) -> None:
        """Test creating Flare contract filter."""
        filter_config = create_flare_contract_filter(
            contract_addresses=["0x123", "0x456"], event_signatures=["0xabcd", "0xefgh"]
        )

        assert "address" in filter_config
        assert len(filter_config["address"]) == EXPECTED_ADDRESS_COUNT
        assert filter_config["address"][0] == "0x123"
        assert "topics" in filter_config
        assert len(filter_config["topics"]) == EXPECTED_TOPIC_COUNT
