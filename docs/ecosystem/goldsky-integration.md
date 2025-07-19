# Goldsky Integration

The Goldsky integration enables real-time blockchain data indexing and querying capabilities for AI agents in the flare-ai-kit. This integration allows agents to access chain-level datasets and correlate them with GraphRAG insights.

## Overview

Goldsky provides high-performance data indexing for Flare blockchain, offering two primary approaches:
- **Subgraphs**: High-performance subgraphs for structured data access
- **Mirror**: Real-time data replication pipelines for raw blockchain data

## Features

- ✅ Real-time data pipeline creation and management
- ✅ Chain-level data access (blocks, logs, transactions, traces)
- ✅ GraphQL query interface for indexed data
- ✅ Integration with GraphRAG engine for enhanced insights
- ✅ Multiple sink types (PostgreSQL, BigQuery, Webhooks, S3)
- ✅ Configurable data filters and transformations

## Quick Start

### 1. Installation

Ensure you have the required dependencies:

```bash
uv sync --all-extras

2. Configuration
Set up your Goldsky configuration:
pythonfrom flare_ai_kit.ecosystem.tooling.goldsky import GoldskyConfig, ChainSlug

config = GoldskyConfig(
    api_key="your_goldsky_api_key",
    project_name="your_project_name",
    chain_slug=ChainSlug.FLARE_MAINNET  # or FLARE_COSTON2 for testnet
)
3. Create a Goldsky Client
pythonfrom flare_ai_kit.ecosystem.tooling.goldsky import Goldsky

async with Goldsky(config) as goldsky:
    # Use goldsky client here
    pass
Creating Data Pipelines
Chain-Level Data Pipeline
pythonfrom flare_ai_kit.ecosystem.tooling.goldsky import (
    DatasetType,
    create_webhook_sink_config
)

# Configure data destination
sink_config = create_webhook_sink_config(
    webhook_url="https://your-app.com/webhook",
    headers={"Authorization": "Bearer token"},
    batch_size=100
)

# Create pipeline for blocks and transactions
pipeline = goldsky.create_chain_data_pipeline(
    pipeline_name="flare_blockchain_data",
    dataset_types=[DatasetType.BLOCKS, DatasetType.TRANSACTIONS],
    sink_config=sink_config
)

# Deploy the pipeline
success = await pipeline.deploy()
Subgraph Data Pipeline
pythonfrom flare_ai_kit.ecosystem.tooling.goldsky import create_postgres_sink_config

# Configure PostgreSQL sink
postgres_sink = create_postgres_sink_config(
    host="localhost",
    database="flare_data",
    username="postgres",
    password="password"
)

# Create subgraph pipeline
subgraph_pipeline = goldsky.create_subgraph_pipeline(
    pipeline_name="flare_defi_data",
    subgraph_name="flare/defi-protocols",
    sink_config=postgres_sink
)
Querying Indexed Data
Get Block Data
python# Get blocks with transaction data
blocks = await goldsky.get_flare_blocks(
    start_block=1000000,
    end_block=1000100,
    include_transactions=True
)

for block in blocks:
    print(f"Block {block['number']}: {len(block.get('transactions', []))} transactions")
Get Contract Logs
python# Get logs for specific contract
logs = await goldsky.get_transaction_logs(
    contract_address="0x1234...5678",
    event_signature="0xddf252ad...",  # Transfer event signature
    start_block=1000000,
    end_block=1000100
)
Custom GraphQL Queries
python# Execute custom GraphQL query
query = """
query GetTokenTransfers($contractAddress: String!, $limit: Int!) {
    logs(
        where: { address: $contractAddress },
        first: $limit,
        orderBy: blockNumber,
        orderDirection: desc
    ) {
        transactionHash
        blockNumber
        data
        topics
    }
}
"""

result = await goldsky.query_indexed_data(
    query=query,
    variables={
        "contractAddress": "0x1234...5678",
        "limit": 100
    }
)
Integration with GraphRAG
The Goldsky integration can correlate blockchain data with GraphRAG insights:
python# Get blockchain data
blockchain_data = await goldsky.get_flare_blocks(1000000, 1000010)

# Correlate with GraphRAG
correlated_data = await goldsky.correlate_with_graphrag(
    blockchain_data=blockchain_data,
    graphrag_query="MATCH (b:Block)-[:CONTAINS]->(tx:Transaction) RETURN b, tx",
    correlation_field="hash"
)

# Access correlated insights
for correlation in correlated_data["correlations"]:
    blockchain_record = correlation["blockchain_data"]
    graph_insight = correlation["graphrag_insight"]
    # Process correlated data
Configuration Options
Sink Types
PostgreSQL Sink
pythonpostgres_sink = create_postgres_sink_config(
    host="localhost",
    database="flare_data",
    username="postgres", 
    password="password",
    port=5432,
    table_prefix="goldsky_"
)
Webhook Sink
pythonwebhook_sink = create_webhook_sink_config(
    webhook_url="https://api.yourapp.com/goldsky",
    headers={"Authorization": "Bearer token"},
    batch_size=100
)
Data Filters
pythonfrom flare_ai_kit.ecosystem.tooling.goldsky import create_flare_contract_filter

# Filter for specific contracts and events
contract_filter = create_flare_contract_filter(
    contract_addresses=[
        "0x1234567890123456789012345678901234567890",
        "0x0987654321098765432109876543210987654321"
    ],
    event_signatures=[
        "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef",  # Transfer
        "0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925"   # Approval
    ]
)