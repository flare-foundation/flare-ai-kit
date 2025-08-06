from typing import Any

from neo4j import GraphDatabase, ManagedTransaction

from flare_ai_kit.rag.graph.settings import GraphDbSettings


class GraphQueryEngine:
    def __init__(self, settings: GraphDbSettings):
        if settings.neo4j_password is None:
            raise ValueError("Neo4j password must be set")

        self._driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=("neo4j", settings.neo4j_password),
            database=settings.neo4j_database,
        )

    def close(self):
        self._driver.close()

    def get_transaction_by_hash(self, tx_hash: str) -> dict[str, Any]:
        query = """
            MATCH (tx:Transaction {hash: $tx_hash})
            OPTIONAL MATCH (from:Account)-[:FROM]->(tx)
            OPTIONAL MATCH (tx)-[:TO]->(to:Account)
            RETURN tx, from.address AS from_address, to.address AS to_address
        """

        def fetch_tx(tx: ManagedTransaction) -> Any:
            return tx.run(query, tx_hash=tx_hash).single()

        with self._driver.session() as session:
            result = session.execute_read(fetch_tx)

            if result:
                return {
                    "tx": result["tx"],
                    "from": result.get("from_address"),
                    "to": result.get("to_address"),
                }
            return {}

    def get_recent_transactions(self, limit: int = 10) -> list[dict[str, Any]]:
        query = """
            MATCH (tx:Transaction)
            RETURN tx
            ORDER BY tx.timestamp DESC
            LIMIT $limit
        """

        def fetch_tx(tx: ManagedTransaction) -> Any:
            return tx.run(query, limit=limit).single()

        with self._driver.session() as session:
            results = session.execute_read(fetch_tx)
            return [record["tx"] for record in results]

    def get_account_balance(self, address: str) -> dict[str, Any]:
        query = """
            MATCH (account:Account {address: toLower($address)})
            RETURN account.balance AS balance
        """

        def fetch_tx(tx: ManagedTransaction) -> Any:
            return tx.run(query, address=address).single()

        with self._driver.session() as session:
            result = session.execute_read(fetch_tx)

            return {
                "address": address,
                "balance": result["balance"] if result else None,
            }

    def get_contracts(self, limit: int = 20) -> list[dict[str, Any]]:
        query = """
            MATCH (c:Contract)
            RETURN c.address AS address, c.balance AS balance
            LIMIT $limit
        """

        def fetch_tx(tx: ManagedTransaction) -> Any:
            return tx.run(query, limit=limit).single()

        with self._driver.session() as session:
            result = session.execute_read(fetch_tx)

            return result

    def get_account_profile(self, address: str) -> dict[str, Any]:
        query = """
            MATCH (account:Account {address: toLower($address)})
            OPTIONAL MATCH (account)-[:FROM]->(tx_out:Transaction)
            OPTIONAL MATCH (tx_in:Transaction)-[:TO]->(account)
            RETURN account,
                   count(DISTINCT tx_out) AS total_sent,
                   count(DISTINCT tx_in) AS total_received
        """

        def fetch_tx(tx: ManagedTransaction) -> Any:
            return tx.run(query, address=address).single()

        with self._driver.session() as session:
            result = session.execute_read(fetch_tx)

            if result:
                account_node = result["account"]
                return {
                    "address": account_node.get("address"),
                    "balance": account_node.get("balance"),
                    "total_sent": result["total_sent"],
                    "total_received": result["total_received"],
                    "is_contract": "Contract" in account_node.labels,
                }
            return {"address": address, "profile": "not found"}
