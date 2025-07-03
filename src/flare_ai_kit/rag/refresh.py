import time
import hashlib
import json
from datetime import datetime, UTC
from typing import Any
from pathlib import Path
try:
    import structlog
except ImportError:
    raise ImportError("structlog is required for logging. Please install it via 'pip install structlog'.")
from flare_ai_kit.ingestion.github_ingestor import GithubIngestor
from flare_ai_kit.ingestion.settings_models import IngestionSettingsModel
from flare_ai_kit.rag.vector.factory import create_vector_rag_pipeline
from flare_ai_kit.rag.vector.settings_models import VectorDbSettingsModel
from flare_ai_kit.agent.settings_models import AgentSettingsModel
from flare_ai_kit.common.schemas import Chunk, ChunkMetadata

logger: Any = structlog.get_logger(__name__)

REFRESH_INTERVAL_SECONDS = 60 * 60 * 24  # 1 day
HASHES_FILE = Path(".data_freshness_hashes.json")

def load_hashes() -> dict[str, str]:
    if HASHES_FILE.exists():
        with open(HASHES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_hashes(hashes: dict[str, str]):
    with open(HASHES_FILE, "w", encoding="utf-8") as f:
        json.dump(hashes, f)

def compute_source_hash(chunks: list[Chunk]) -> str:
    m = hashlib.sha256()
    for chunk in chunks:
        m.update(chunk.text.encode("utf-8"))
    return m.hexdigest()

def github_ingest_fn(config: dict[str, Any]) -> list[Chunk]:
    ingestion_settings = IngestionSettingsModel()
    ingestor = GithubIngestor(ingestion_settings)
    return list(ingestor.ingest(config["repo"], branch=config.get("branch")))

def placeholder_ingest_fn(config: dict[str, Any]) -> list[Chunk]:
    # Placeholder for news or governance ingestion. Replace with real logic when available.
    logger.info("Placeholder ingest function called. No data ingested.", config=config)
    return []

SOURCES: list[dict[str, Any]] = [
    {
        "name": "Flare Dev Hub",
        "type": "github",
        "collection_name": "flare_dev_hub_docs",
        "ttl": 60 * 60 * 24,
        "ingest_fn": github_ingest_fn,
        "config": {
            "repo": "flarenetwork/flare-developer-hub",
            "branch": None,
        },
    },
    {
        "name": "Governance Proposals",
        "type": "placeholder",
        "collection_name": "governance_proposals",
        "ttl": 60 * 60 * 24,
        "ingest_fn": placeholder_ingest_fn,
        "config": {},
    },
    {
        "name": "Flare News",
        "type": "placeholder",
        "collection_name": "flare_news",
        "ttl": 60 * 60 * 24,
        "ingest_fn": placeholder_ingest_fn,
        "config": {},
    },
]

def refresh_source(source: dict[str, Any], hashes: dict[str, str]):
    logger.info("Starting refresh", source=source["name"], type=source["type"])
    chunks = source["ingest_fn"](source["config"])
    if not chunks:
        logger.info("No data ingested for source", source=source["name"])
        return
    source_hash = compute_source_hash(chunks)
    last_hash = hashes.get(source["name"])
    if last_hash == source_hash:
        logger.info("No changes detected, skipping reindex", source=source["name"])
        return
    now = datetime.now(UTC)
    ttl = int(source["ttl"])
    for i, chunk in enumerate(chunks):
        meta = chunk.metadata
        new_meta = ChunkMetadata(
            original_filepath=meta.original_filepath,
            chunk_id=meta.chunk_id,
            start_index=meta.start_index,
            end_index=meta.end_index,
            last_updated=now,
            ttl=ttl,
            source_hash=source_hash,
        )
        chunks[i] = Chunk(text=chunk.text, metadata=new_meta)
    # Index in Qdrant
    vector_db_settings = VectorDbSettingsModel()
    agent_settings = AgentSettingsModel()
    pipeline = create_vector_rag_pipeline(vector_db_settings, agent_settings)
    retriever = pipeline.retriever
    processed, skipped, failed = retriever.embed_and_upsert(
        data=chunks,
        collection_name=source["collection_name"],
    )
    logger.info(
        "Reindex complete",
        source=source["name"],
        processed=processed,
        skipped=skipped,
        failed=len(failed),
    )
    hashes[source["name"]] = source_hash
    save_hashes(hashes)

def run_refresh_loop():
    while True:
        hashes = load_hashes()
        for source in SOURCES:
            try:
                refresh_source(source, hashes)
            except Exception as e:
                logger.exception("Error during refresh cycle", source=source["name"], error=str(e))
        logger.info("Sleeping until next refresh", seconds=REFRESH_INTERVAL_SECONDS)
        time.sleep(REFRESH_INTERVAL_SECONDS)

if __name__ == "__main__":
    run_refresh_loop() 