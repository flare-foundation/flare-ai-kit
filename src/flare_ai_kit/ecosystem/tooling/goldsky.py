"""
Goldsky integration for blockchain data indexing and querying.

This module provides integration with Goldsky Mirror for real-time data replication
pipelines, enabling AI agents to access chain-level datasets (blocks, logs, traces)
and cross-reference with GraphRAG insights.
"""

import asyncio
import json
import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

import aiohttp
from pydantic import BaseModel, Field, field_validator
from flare_ai_kit.ecosystem.settings_model import GoldskyConfig  

logger = logging.getLogger(__name__)


class FlareAIKitError(Exception):
    """Custom exception for Flare AI Kit."""


class ChainSlug(str, Enum):
    """Supported Flare chain slugs."""

    FLARE_MAINNET = "flare"
    FLARE_COSTON2 = "flare-coston2"


class DatasetType(str, Enum):
    """Available dataset types for Goldsky pipelines."""

    BLOCKS = "blocks"
    LOGS = "logs"
    TRANSACTIONS = "transactions"
    TRACES = "traces"


class SinkType(str, Enum):
    """Supported sink types for data replication."""

    POSTGRES = "postgres"
    BIGQUERY = "bigquery"
    WEBHOOK = "webhook"
    S3 = "s3"


@dataclass
class GoldskyConfig:
    """Configuration for Goldsky integration."""

    api_key: str
    project_name: str
    chain_slug: ChainSlug = ChainSlug.FLARE_MAINNET
    goldsky_cli_path: str = "goldsky"
    base_url: str = "https://api.goldsky.com"
    timeout: int = 30


class PipelineDefinition(BaseModel):
    """Pipeline definition for Goldsky Mirror."""

    version: str = Field(default="1", description="Pipeline definition version")
    sources: list[dict[str, Any]] = Field(description="Data sources configuration")
    sinks: list[dict[str, Any]] = Field(description="Data sinks configuration")
    transforms: list[dict[str, Any]] | None = Field(
        default=None, description="Data transformations"
    )

    @field_validator("sources")
    @classmethod
    def validate_sources(cls, v: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Validate sources configuration."""
        if not v:
            msg = "At least one source must be specified"
            raise ValueError(msg)
        return v

    @field_validator("sinks")
    @classmethod
    def validate_sinks(cls, v: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Validate sinks configuration."""
        if not v:
            msg = "At least one sink must be specified"
            raise ValueError(msg)
        return v


class GoldskyPipeline:
    """Represents a Goldsky Mirror pipeline."""

    def __init__(
        self, name: str, config: GoldskyConfig, definition: PipelineDefinition
    ) -> None:
        self.name = name
        self.config = config
        self.definition = definition
        self._definition_file: Path | None = None

    def _create_definition_file(self) -> Path:
        """Create pipeline definition file."""
        definition_dir = Path(".goldsky")
        definition_dir.mkdir(exist_ok=True)

        definition_file = definition_dir / f"{self.name}-pipeline.json"

        definition_file.write_text(json.dumps(self.definition.model_dump(), indent=2))

        self._definition_file = definition_file
        return definition_file

    async def deploy(self) -> bool:
        """Deploy the pipeline using Goldsky CLI."""
        try:
            definition_file = self._create_definition_file()

            cmd = [
                self.config.goldsky_cli_path,
                "pipeline",
                "create",
                self.name,
                "--definition-path",
                str(definition_file),
            ]

            logger.info(
                "Deploying pipeline %s with definition file: %s",
                self.name,
                definition_file,
            )

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={"GOLDSKY_API_KEY": self.config.api_key},
            )

            _stdout, stderr = await process.communicate()

            if process.returncode == 0:
                logger.info("Pipeline %s deployed successfully", self.name)
                return True

            logger.error("Failed to deploy pipeline %s: %s", self.name, stderr.decode())
            return False

        except Exception:
            logger.exception("Error deploying pipeline %s", self.name)
            return False

    async def delete(self) -> bool:
        """Delete the pipeline."""
        try:
            cmd = [self.config.goldsky_cli_path, "pipeline", "delete", self.name]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={"GOLDSKY_API_KEY": self.config.api_key},
            )

            _stdout, stderr = await process.communicate()

            if process.returncode == 0:
                logger.info("Pipeline %s deleted successfully", self.name)
                return True

            logger.error("Failed to delete pipeline %s: %s", self.name, stderr.decode())
            return False

        except Exception:
            logger.exception("Error deleting pipeline %s", self.name)
            return False


class Goldsky:
    """
    Main Goldsky integration class for blockchain data indexing and querying.

    This class provides methods to:
    - Create and manage Mirror pipelines for real-time data replication
    - Query indexed blockchain data
    - Integrate with GraphRAG engine for enhanced insights
    """

    def __init__(self, config: GoldskyConfig) -> None:
        """Initialize Goldsky client."""
        self.config = config
        self._session: aiohttp.ClientSession | None = None
        self.pipelines: dict[str, GoldskyPipeline] = {}

    async def __aenter__(self) -> "Goldsky":
        """Async context manager entry."""
        self._session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.config.timeout)
        )
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        if self._session:
            await self._session.close()

    def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if not self._session:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.config.timeout)
            )
        return self._session

    def create_chain_data_pipeline(
        self,
        pipeline_name: str,
        dataset_types: list[DatasetType],
        sink_config: dict[str, Any],
        filters: dict[str, Any] | None = None,
        transforms: list[dict[str, Any]] | None = None,
    ) -> GoldskyPipeline:
        """
        Create a pipeline for chain-level data replication.

        Args:
            pipeline_name: Name of the pipeline
            dataset_types: Types of data to replicate (blocks, logs, transactions, traces)
            sink_config: Configuration for data destination
            filters: Optional filters to apply to the data
            transforms: Optional data transformations

        Returns:
            GoldskyPipeline instance

        """
        sources: list[dict[str, Any]] = []

        for dataset_type in dataset_types:
            source_config: dict[str, Any] = {
                "type": "chain-level",
                "chain": self.config.chain_slug.value,
                "dataset": dataset_type.value,
            }

            if filters:
                source_config["filters"] = filters

            sources.append(source_config)

        sinks = [sink_config]

        definition = PipelineDefinition(
            sources=sources, sinks=sinks, transforms=transforms
        )

        pipeline = GoldskyPipeline(pipeline_name, self.config, definition)
        self.pipelines[pipeline_name] = pipeline

        return pipeline

    def create_subgraph_pipeline(
        self,
        pipeline_name: str,
        subgraph_name: str,
        sink_config: dict[str, Any],
        filters: dict[str, Any] | None = None,
    ) -> GoldskyPipeline:
        """
        Create a pipeline for subgraph data replication.

        Args:
            pipeline_name: Name of the pipeline
            subgraph_name: Name of the source subgraph
            sink_config: Configuration for data destination
            filters: Optional filters to apply to the data

        Returns:
            GoldskyPipeline instance

        """
        source_config: dict[str, Any] = {"type": "subgraph", "name": subgraph_name}

        if filters:
            source_config["filters"] = filters

        definition = PipelineDefinition(sources=[source_config], sinks=[sink_config])

        pipeline = GoldskyPipeline(pipeline_name, self.config, definition)
        self.pipelines[pipeline_name] = pipeline

        return pipeline

    async def query_indexed_data(
        self, query: str, variables: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Query indexed data using GraphQL.

        Args:
            query: GraphQL query string
            variables: Optional query variables

        Returns:
            Query results

        """
        session = self._get_session()

        payload = {"query": query, "variables": variables or {}}

        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with session.post(
                f"{self.config.base_url}/graphql", json=payload, headers=headers
            ) as response:
                response.raise_for_status()
                return await response.json()

        except aiohttp.ClientError as e:
            logger.exception("Error querying indexed data")
            msg = f"Failed to query indexed data: {e!s}"
            raise FlareAIKitError(msg) from e

    async def get_flare_blocks(
        self, start_block: int, end_block: int, include_transactions: bool = False
    ) -> list[dict[str, Any]]:
        """
        Get Flare blocks data within a specified range.

        Args:
            start_block: Starting block number
            end_block: Ending block number
            include_transactions: Whether to include transaction data

        Returns:
            List of block data

        """
        query = """
        query GetBlocks($startBlock: Int!, $endBlock: Int!, $includeTransactions: Boolean!) {
            blocks(
                where: {
                    number_gte: $startBlock,
                    number_lte: $endBlock
                }
                orderBy: number
                orderDirection: asc
            ) {
                number
                hash
                timestamp
                gasUsed
                gasLimit
                baseFeePerGas
                transactions @include(if: $includeTransactions) {
                    hash
                    from
                    to
                    value
                    gasPrice
                    gasUsed
                }
            }
        }
        """

        variables = {
            "startBlock": start_block,
            "endBlock": end_block,
            "includeTransactions": include_transactions,
        }

        result = await self.query_indexed_data(query, variables)
        return result.get("data", {}).get("blocks", [])

    async def get_transaction_logs(
        self,
        contract_address: str,
        event_signature: str | None = None,
        start_block: int | None = None,
        end_block: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        Get transaction logs for a specific contract.

        Args:
            contract_address: Contract address to filter logs
            event_signature: Optional event signature to filter
            start_block: Optional starting block number
            end_block: Optional ending block number

        Returns:
            List of transaction logs

        """
        query = """
        query GetLogs(
            $contractAddress: String!,
            $eventSignature: String,
            $startBlock: Int,
            $endBlock: Int
        ) {
            logs(
                where: {
                    address: $contractAddress,
                    topics_contains: [$eventSignature],
                    blockNumber_gte: $startBlock,
                    blockNumber_lte: $endBlock
                }
                orderBy: blockNumber
                orderDirection: asc
            ) {
                id
                address
                topics
                data
                blockNumber
                transactionHash
                logIndex
            }
        }
        """

        variables: dict[str, str | int] = {
            "contractAddress": contract_address.lower(),
        }

        if event_signature is not None:
            variables["eventSignature"] = event_signature
        if start_block is not None:
            variables["startBlock"] = start_block
        if end_block is not None:
            variables["endBlock"] = end_block

        result = await self.query_indexed_data(query, variables)
        return result.get("data", {}).get("logs", [])

    async def correlate_with_graphrag(
        self,
        blockchain_data: list[dict[str, Any]],
        graphrag_query: str,
        correlation_field: str = "transactionHash",
    ) -> dict[str, Any]:
        """
        Correlate blockchain data with GraphRAG insights.

        Args:
            blockchain_data: Blockchain data from Goldsky
            graphrag_query: Query to execute on GraphRAG engine
            correlation_field: Field to use for correlation

        Returns:
            Correlated data combining blockchain and GraphRAG insights

        """
        # Extract correlation values from blockchain data
        correlation_values = [
            item.get(correlation_field)
            for item in blockchain_data
            if item.get(correlation_field)
        ]

        # This would integrate with the GraphRAG engine
        # For now, we'll return a placeholder structure
        correlated_data = {
            "blockchain_data": blockchain_data,
            "graphrag_insights": {
                "query": graphrag_query,
                "correlation_field": correlation_field,
                "correlation_values": correlation_values,
                "insights": [],  # Would be populated by GraphRAG engine
            },
            "correlations": [],
        }

        logger.info(
            "Correlated %d blockchain records with GraphRAG",
            len(blockchain_data),
        )
        return correlated_data

    async def deploy_all_pipelines(self) -> dict[str, bool]:
        """Deploy all registered pipelines."""
        results: dict[str, bool] = {}

        for name, pipeline in self.pipelines.items():
            try:
                success = await pipeline.deploy()
                results[name] = success
            except Exception:
                logger.exception("Failed to deploy pipeline %s", name)
                results[name] = False

        return results

    async def cleanup_pipelines(self) -> dict[str, bool]:
        """Delete all registered pipelines."""
        results: dict[str, bool] = {}

        for name, pipeline in self.pipelines.items():
            try:
                success = await pipeline.delete()
                results[name] = success
            except Exception:
                logger.exception("Failed to delete pipeline %s", name)
                results[name] = False

        return results


# Utility functions for common use cases


def create_postgres_sink_config(
    host: str,
    database: str,
    username: str,
    password: str,
    port: int = 5432,
    table_prefix: str = "goldsky_",
) -> dict[str, Any]:
    """Create PostgreSQL sink configuration."""
    return {
        "type": "postgres",
        "connection": {
            "host": host,
            "port": port,
            "database": database,
            "username": username,
            "password": password,
        },
        "table_prefix": table_prefix,
    }


def create_webhook_sink_config(
    webhook_url: str, headers: dict[str, str] | None = None, batch_size: int = 100
) -> dict[str, Any]:
    """Create webhook sink configuration."""
    config: dict[str, Any] = {
        "type": "webhook",
        "url": webhook_url,
        "batch_size": batch_size,
    }

    if headers:
        config["headers"] = headers

    return config


def create_flare_contract_filter(
    contract_addresses: list[str], event_signatures: list[str] | None = None
) -> dict[str, Any]:
    """Create filter for Flare contract events."""
    filter_config: dict[str, Any] = {
        "address": [addr.lower() for addr in contract_addresses]
    }

    if event_signatures:
        filter_config["topics"] = event_signatures

    return filter_config
