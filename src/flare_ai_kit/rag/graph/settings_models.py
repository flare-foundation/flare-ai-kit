"""Settings for GraphRAG."""

from pydantic import BaseModel, Field


class GraphDbSettingsModel(BaseModel):
    """Configuration settings for connecting to the Graph Database (Neo4j).."""

    neo4j_uri: str = Field(
        "neo4j://localhost:7687",
        description="Connection URI for the Neo4j database.",
    )
    neo4j_database: str = Field(
        "neo4j",  # Default database name in Neo4j v4+
        description="The name of the specific Neo4j database.",
    )
