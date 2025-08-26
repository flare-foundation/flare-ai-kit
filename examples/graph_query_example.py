import asyncio

from flare_ai_kit.rag.graph.engine import GraphQueryEngine
from flare_ai_kit.rag.graph.indexers.neo4j_indexer import Neo4jIngester
from flare_ai_kit.rag.graph.settings import GraphDbSettings


async def main():
    settings = GraphDbSettings()
    ingester = Neo4jIngester(settings)
    engine = GraphQueryEngine(settings)

    # Ingest some blocks
    await ingester.batch_ingest(start_block=45476458, count=3)

    # Query recent transactions
    recent_txs = engine.get_recent_transactions(limit=5)
    print(" Recent transactions:")
    for tx in recent_txs:
        print(tx)

    # Only try to fetch a tx by hash if we actually got some
    if recent_txs:
        print("\n Transactions Details:")
        for tx in recent_txs:
            sample_hash = tx["hash"]
            tx_details = engine.get_transaction_by_hash(sample_hash)
            print(tx_details, end="\n")
            print()

            if tx_details.get("from"):
                print(f"Sender: {tx_details['from']}, Receiver: {tx_details['to']}")
    else:
        print("No recent transactions found to show details for.")

    # Account balance of sender
    if tx_details.get("from_address"):
        balance = engine.get_account_balance(tx_details["from_address"])
        print("\n Account balance:")
        print(balance)

    # List some contracts
    contracts = engine.get_contracts(limit=5)
    print("\n Example contracts:")
    for c in contracts:
        print(c)

    # Account profile of receiver
    if tx_details.get("to_address"):
        profile = engine.get_account_profile(tx_details["to_address"])
        print("\n Account profile:")
        print(profile)

    ingester.close()
    engine.close()


if __name__ == "__main__":
    asyncio.run(main())
