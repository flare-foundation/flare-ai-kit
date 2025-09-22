from typing import Any, cast

from eth_typing import ChecksumAddress
from neo4j import GraphDatabase, ManagedTransaction
from web3 import AsyncHTTPProvider, AsyncWeb3
from web3.middleware import (
    ExtraDataToPOAMiddleware,  # pyright: ignore[reportUnknownVariableType]
)
from web3.types import BlockData, TxData

from flare_ai_kit.rag.graph.settings import GraphDbSettings


class Neo4jIngester:
    def __init__(self, settings: GraphDbSettings):
        if settings.neo4j_password is None:
            raise ValueError("Neo4j password must be set")
        self.driver = GraphDatabase.driver(
            settings.neo4j_uri, auth=("neo4j", settings.neo4j_password)
        )
        self.web3 = AsyncWeb3(
            AsyncHTTPProvider(str(settings.web3_provider_url)),
            middleware=[ExtraDataToPOAMiddleware],
        )

    def close(self):
        self.driver.close()

    def ingest_transactions(self, transactions: list[dict[str, Any]]) -> None:
        with self.driver.session(database="neo4j") as session:
            session.execute_write(self._create_transaction_nodes, transactions)

    @staticmethod
    def _create_transaction_nodes(
        tx: ManagedTransaction, transactions: list[dict[str, Any]]
    ) -> None:
        # Normalize hashes to lowercase hex strings
        for t in transactions:
            if isinstance(t.get("hash"), (bytes, bytearray)):
                t["hash"] = t["hash"].hex()
            elif isinstance(t.get("hash"), str) and t["hash"].startswith("0x"):
                t["hash"] = t["hash"][2:]  # strip 0x
            elif isinstance(t.get("hash"), str):
                t["hash"] = t["hash"].lower()

        tx.run(
            """
            UNWIND $transactions AS tx_data

            // Create sender node (User or Contract)
            MERGE (from:Account {address: toLower(tx_data.from)})
            ON CREATE SET from.created_at = timestamp()
            SET from.balance = tx_data.from_balance

            // Create recipient node and check if it's a contract
            MERGE (to:Account {address: toLower(tx_data.to)})
            ON CREATE SET to.created_at = timestamp()
            SET to.balance = tx_data.to_balance

            // Optional: Label contract if code is present
            FOREACH (_ IN CASE WHEN tx_data.to_code IS NOT NULL AND tx_data.to_code <> '0x' THEN [1] ELSE [] END |
                SET to:Contract
            )
            FOREACH (_ IN CASE WHEN tx_data.from_code IS NOT NULL AND tx_data.from_code <> '0x' THEN [1] ELSE [] END |
                SET from:Contract
            )

            // Transaction node
            MERGE (tx:Transaction {hash: tx_data.hash})
            SET tx.blockNumber = tx_data.blockNumber,
                tx.timestamp = datetime({ epochMillis: tx_data.timestamp }),
                tx.value = tx_data.value

            MERGE (from)-[:FROM]->(tx)
            MERGE (tx)-[:TO]->(to)
            """,
            parameters={"transactions": transactions},
        )

    async def fetch_block_transactions(self, block_number: int) -> list[dict[str, Any]]:
        block: BlockData | None = await self.web3.eth.get_block(
            block_number, full_transactions=True
        )
        transactions: list[dict[str, Any]] = []

        if not block:
            return transactions

        block_timestamp = block.get("timestamp")
        if block_timestamp is None:
            return transactions

        tx_list = block.get("transactions", [])
        for tx_raw in tx_list:
            if not isinstance(tx_raw, dict):
                continue

            tx: TxData = tx_raw

            hash_val = tx.get("hash")
            block_number_val = tx.get("blockNumber")
            value = tx.get("value")
            from_address = cast("ChecksumAddress", tx.get("from"))
            to_address = cast("ChecksumAddress", tx.get("to"))

            # Normalize hash into canonical 0x-prefixed string
            if isinstance(hash_val, (bytes, bytearray)):
                hash_str = "0x" + hash_val.hex()
            else:
                hash_str = str(hash_val).lower()
                if not hash_str.startswith("0x"):
                    hash_str = "0x" + hash_str

            if not all([hash_str, block_number_val, value, from_address]):
                continue

            from_balance = await self.web3.eth.get_balance(from_address)
            from_code = await self.web3.eth.get_code(from_address)

            to_balance = await self.web3.eth.get_balance(to_address)
            to_code = await self.web3.eth.get_code(to_address)

            transactions.append(
                {
                    "hash": hash_str,
                    "from": from_address,
                    "to": to_address,
                    "blockNumber": block_number_val,
                    "timestamp": block_timestamp * 1000,
                    "value": str(value),
                    "from_balance": str(from_balance),
                    "to_balance": str(to_balance),
                    "from_code": from_code.hex(),
                    "to_code": to_code.hex(),
                }
            )

        return transactions

    async def batch_ingest(self, start_block: int, count: int) -> None:
        for i in range(start_block, start_block + count):
            txs = await self.fetch_block_transactions(i)
            if txs:
                print(f"Ingesting block {i} with {len(txs)} transactions")
                self.ingest_transactions(txs)
            else:
                print(f"Block {i} has no transactions, skipping")
        self.close()
