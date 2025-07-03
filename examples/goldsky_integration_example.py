"""
Example usage of Goldsky integration with flare-ai-kit.

This example demonstrates how to:
1. Set up Goldsky client
2. Create data pipelines for blockchain data
3. Query indexed data
4. Correlate with GraphRAG insights
"""

import asyncio
import os

from flare_ai_kit.ecosystem.tooling.goldsky import (
    ChainSlug,
    DatasetType,
    Goldsky,
    GoldskyConfig,
    create_flare_contract_filter,
    create_postgres_sink_config,
    create_webhook_sink_config,
)

# Constants
TEST_DB_PASSWORD = "test_password_123"
BLOCK_RANGE_START = 1000000
BLOCK_RANGE_END = 1000010
QUERY_LIMIT = 10


async def main() -> None:
    """Main example function."""
    # Create Goldsky configuration
    config = GoldskyConfig(
        api_key=os.getenv("GOLDSKY_API_KEY", "your_api_key_here"),
        project_name="flare-ai-kit-example",
        chain_slug=ChainSlug.FLARE_COSTON2,  # Using testnet for example
    )

    # Initialize Goldsky client
    async with Goldsky(config) as goldsky:
        # Example 1: Create a pipeline for block and transaction data
        print("Creating blockchain data pipeline...")

        # Configure webhook sink for receiving data
        webhook_sink = create_webhook_sink_config(
            webhook_url="https://your-app.com/goldsky-webhook",
            headers={"Authorization": "Bearer your_webhook_token"},
            batch_size=100,
        )

        # Create pipeline for blocks and transactions
        _ = goldsky.create_chain_data_pipeline(
            pipeline_name="flare_blocks_and_txs",
            dataset_types=[DatasetType.BLOCKS, DatasetType.TRANSACTIONS],
            sink_config=webhook_sink,
            filters=create_flare_contract_filter(
                contract_addresses=["0x1234567890123456789012345678901234567890"],
                event_signatures=[
                    "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
                ],
            ),
        )

        # Example 2: Create pipeline for smart contract logs
        print("Creating contract logs pipeline...")

        # Configure PostgreSQL sink for storing data
        postgres_sink = create_postgres_sink_config(
            host="localhost",
            database="flare_data",
            username="postgres",
            password=TEST_DB_PASSWORD,
            table_prefix="flare_",
        )

        _ = goldsky.create_chain_data_pipeline(
            pipeline_name="flare_contract_logs",
            dataset_types=[DatasetType.LOGS],
            sink_config=postgres_sink,
        )

        # Example 3: Deploy pipelines (commented out to avoid actual deployment)
        # Would be uncommented in real usage:
        # print("Deploying pipelines...")
        # deployment_results = await goldsky.deploy_all_pipelines()
        # print(f"Deployment results: {deployment_results}")

        # Example 4: Query indexed data
        print("Querying indexed blockchain data...")

        try:
            # Get recent blocks
            recent_blocks = await goldsky.get_flare_blocks(
                start_block=BLOCK_RANGE_START,
                end_block=BLOCK_RANGE_END,
                include_transactions=True,
            )
            print(f"Retrieved {len(recent_blocks)} blocks")

            # Get contract logs
            contract_logs = await goldsky.get_transaction_logs(
                contract_address="0x1234567890123456789012345678901234567890",
                start_block=BLOCK_RANGE_START,
                end_block=BLOCK_RANGE_END,
            )
            print(f"Retrieved {len(contract_logs)} contract logs")

            # Example 5: Correlate with GraphRAG
            print("Correlating blockchain data with GraphRAG...")

            graphrag_query = (
                "MATCH (b:Block)-[:CONTAINS]->(tx:Transaction) "
                f"WHERE b.number >= {BLOCK_RANGE_START} RETURN b, tx"
            )
            correlated_data = await goldsky.correlate_with_graphrag(
                blockchain_data=recent_blocks,
                graphrag_query=graphrag_query,
                correlation_field="hash",
            )

            blockchain_count = len(correlated_data["blockchain_data"])
            print(f"Correlated data contains {blockchain_count} blockchain records")

        except Exception as e:
            print(f"Error querying data: {e}")

        # Example 6: Custom GraphQL query
        print("Executing custom GraphQL query...")

        try:
            custom_query = """
            query GetRecentTransactions($limit: Int!) {
                transactions(
                    first: $limit,
                    orderBy: blockNumber,
                    orderDirection: desc
                ) {
                    hash
                    from
                    to
                    value
                    gasUsed
                    block {
                        number
                        timestamp
                    }
                }
            }
            """

            query_result = await goldsky.query_indexed_data(
                query=custom_query, variables={"limit": QUERY_LIMIT}
            )

            transactions = query_result.get("data", {}).get("transactions", [])
            print(f"Retrieved {len(transactions)} recent transactions")

        except Exception as e:
            print(f"Error executing custom query: {e}")


if __name__ == "__main__":
    asyncio.run(main())
