from pydantic import BaseModel, Field
from typing import Any, List, Dict


class RagSourceConfig(BaseModel):
    name: str
    type: str
    collection_name: str
    ttl: int = Field(..., description="Time-to-live for the data in seconds.")
    ingest_fn: Any = Field(
        None,
        description="Ingestion function for the source. Not validated by Pydantic; set at runtime.",
    )
    config: Dict[str, Any] = Field(default_factory=dict)


class RagRefreshSettings(BaseModel):
    refresh_interval_seconds: int = Field(
        60 * 60 * 24,  # 1 day by default
        description="Interval in seconds between refresh cycles.",
    )
    sources: List[RagSourceConfig] = Field(
        default_factory=list,
        description="List of source configurations for RAG data freshness.",
    )
