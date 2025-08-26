"""Settings for GraphRAG."""

from pydantic import Field, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class GraphDbSettings(BaseSettings):
    """Configuration settings for connecting to the Graph Database (Neo4j).."""

    model_config = SettingsConfigDict(
        env_prefix="GRAPHDB__",
        env_file=".env",
        extra="ignore",
    )
    web3_provider_url: HttpUrl = Field(
        default=HttpUrl(
            "https://stylish-light-theorem.flare-mainnet.quiknode.pro/ext/bc/C/rpc"
        ),
        description="Flare RPC endpoint URL.",
    )
    neo4j_uri: str = Field(
        default="bolt://localhost:7687",
        description="Connection URI for the Neo4j database.",
    )
    neo4j_username: str = Field(
        default="neo4j", description="Username for the Neo4j database."
    )
    neo4j_database: str = Field(
        default="neo4j",  # Default database name in Neo4j v4+
        description="The name of the specific Neo4j database.",
    )
    neo4j_password: str | None = Field(
        default=None,
        description="password for the Neo4j database.",
    )
