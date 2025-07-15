import asyncio
import hashlib
import json
from datetime import datetime, UTC
from typing import Any, List
from pathlib import Path
import logging
from flare_ai_kit.ingestion.github_ingestor import GithubIngestor
from flare_ai_kit.ingestion.settings_models import IngestionSettingsModel
from flare_ai_kit.rag.vector.factory import create_vector_rag_pipeline
from flare_ai_kit.rag.vector.settings_models import VectorDbSettingsModel, DEFAULT_ALLOWED_EXTENSIONS, DEFAULT_IGNORED_DIRS, DEFAULT_IGNORED_FILES
from flare_ai_kit.agent.settings_models import AgentSettingsModel
from flare_ai_kit.common.schemas import Chunk, ChunkMetadata
from flare_ai_kit.rag.settings_models import RagRefreshSettings, RagSourceConfig

import aiohttp
from bs4 import BeautifulSoup, Tag
from pydantic import SecretStr

logger = logging.getLogger("flare_ai_kit.rag.refresh")
logging.basicConfig(level=logging.INFO)

HASHES_FILE = Path(".data_freshness_hashes.json")

# --- Utility functions ---
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

# --- Ingestion functions ---
def github_ingest_fn(config: dict[str, Any]) -> list[Chunk]:
    ingestion_settings = IngestionSettingsModel(
        chunk_size=512,
        chunk_overlap=64,
        github_allowed_extensions=DEFAULT_ALLOWED_EXTENSIONS,
        github_ignored_dirs=DEFAULT_IGNORED_DIRS,
        github_ignored_files=DEFAULT_IGNORED_FILES,
    )
    ingestor = GithubIngestor(ingestion_settings)
    return list(ingestor.ingest(config["repo"], branch=config.get("branch")))

async def news_ingest_fn(config: dict[str, Any]) -> List[Chunk]:
    url = config.get("url", "https://flare.network/news")
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            html = await resp.text()
    soup = BeautifulSoup(html, "html.parser")
    articles: List[str] = []
    for a in soup.find_all("a", href=True):
        if isinstance(a, Tag):
            href_val = a.get("href", "")
            href = str(href_val) if href_val is not None else ""
            # Only add news articles, skip events, newsletter, etc.
            if href.startswith("/news/") and href != "/news/" and "event" not in href and "newsletter" not in href:
                articles.append("https://flare.network" + href)
    articles = list(set(articles))  # deduplicate
    chunks: List[Chunk] = []
    for article_url in articles:
        async with session.get(article_url) as resp:
            article_html = await resp.text()
        article_soup = BeautifulSoup(article_html, "html.parser")
        title = article_soup.find("h1")
        date = article_soup.find("time")
        author = article_soup.find("span", class_="author")
        tags = [t.text for t in article_soup.find_all("a", class_="tag")] if article_soup.find_all("a", class_="tag") else []
        content = article_soup.find("div", class_="entry-content") or article_soup.find("article")
        text = (title.text.strip() if title else "") + "\n"
        if date:
            text += f"Date: {date.text.strip()}\n"
        if author:
            text += f"Author: {author.text.strip()}\n"
        if tags:
            text += f"Tags: {', '.join(tags)}\n"
        text += (content.text.strip() if content else "")
        if text.strip():
            meta = ChunkMetadata(
                original_filepath=article_url,
                chunk_id=0,
                start_index=0,
                end_index=len(text),
                last_updated=datetime.now(UTC),
                ttl=config.get("ttl", 60 * 60 * 24),
                source_hash="",
            )
            chunks.append(Chunk(text=text, metadata=meta))
    logger.info(f"Ingested {len(chunks)} news articles from {url}")
    return chunks

async def governance_ingest_fn(config: dict[str, Any]) -> List[Chunk]:
    url = config.get("url", "https://proposals.flare.network")
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            html = await resp.text()
    soup = BeautifulSoup(html, "html.parser")
    articles: List[str] = []
    for a in soup.find_all("a", href=True):
        if isinstance(a, Tag):
            href_val = a.get("href", "")
            href = str(href_val) if href_val is not None else ""
            if href.endswith(".html") and not href.startswith("http") and "index" not in href:
                articles.append(url.rstrip("/") + "/" + href.lstrip("/"))
    articles = list(set(articles))
    chunks: List[Chunk] = []
    for article_url in articles:
        async with session.get(article_url) as resp:
            article_html = await resp.text()
        article_soup = BeautifulSoup(article_html, "html.parser")
        title = article_soup.find("h1")
        # Try to extract proposal metadata (e.g., ID, status, date)
        meta_table = article_soup.find("table")
        meta_info = ""
        if meta_table:
            for r in meta_table.find_all("tr"):
                if not isinstance(r, Tag):
                    continue
                row: Tag = r
                cells = row.find_all(["td", "th"])
                if len(cells) == 2:
                    meta_info += f"{cells[0].text.strip()}: {cells[1].text.strip()}\n"
        content = article_soup.find("main") or article_soup.find("article")
        text = (title.text.strip() if title else "") + "\n"
        text += meta_info
        text += (content.text.strip() if content else "")
        if text.strip():
            meta = ChunkMetadata(
                original_filepath=article_url,
                chunk_id=0,
                start_index=0,
                end_index=len(text),
                last_updated=datetime.now(UTC),
                ttl=config.get("ttl", 60 * 60 * 24),
                source_hash="",
            )
            chunks.append(Chunk(text=text, metadata=meta))
    logger.info(f"Ingested {len(chunks)} governance proposals from {url}")
    return chunks

# --- Async refresh logic ---
async def refresh_source_async(source: RagSourceConfig, hashes: dict[str, str]):
    logger.info(f"Starting refresh: source={source.name}, type={source.type}")
    # Support both sync and async ingest_fn
    if asyncio.iscoroutinefunction(source.ingest_fn):
        chunks = await source.ingest_fn(source.config)
    else:
        chunks = source.ingest_fn(source.config)
    if not chunks:
        logger.info(f"No data ingested for source: {source.name}")
        return
    source_hash = compute_source_hash(chunks)
    last_hash = hashes.get(source.name)
    if last_hash == source_hash:
        logger.info(f"No changes detected, skipping reindex: {source.name}")
        return
    now = datetime.now(UTC)
    ttl = int(source.ttl)
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
    # Pass None for all required fields for local/test runs; update as needed for production
    vector_db_settings = VectorDbSettingsModel(
        qdrant_url=None,
        qdrant_vector_size=768,
        qdrant_batch_size=100,
        embeddings_model="gemini-embedding-exp-03-07",
        embeddings_output_dimensionality=None,
        postgres_dsn=None,
    )
    agent_settings = AgentSettingsModel(
        gemini_api_key=SecretStr(""),  # Use SecretStr for required field
        gemini_model="",    # Use empty string for required str
        openrouter_api_key=None,
    )
    pipeline = create_vector_rag_pipeline(vector_db_settings, agent_settings)
    retriever = pipeline.retriever
    processed, skipped, failed = retriever.embed_and_upsert(
        data=chunks,
        collection_name=source.collection_name,
    )
    logger.info(
        f"Reindex complete: source={source.name}, processed={processed}, skipped={skipped}, failed={len(failed)}"
    )
    hashes[source.name] = source_hash
    save_hashes(hashes)

async def run_refresh_once_async():
    hashes = load_hashes()
    for source in refresh_settings.sources:
        try:
            await refresh_source_async(source, hashes)
        except Exception as e:
            logger.exception(f"Error during refresh cycle: source={source.name}, error={e}")
    logger.info(f"Sleeping until next refresh: seconds={refresh_settings.refresh_interval_seconds}")

async def run_refresh_periodically():
    """
    Periodically refresh all sources using the configured interval.
    This function is non-blocking and can be scheduled in an async event loop or SDK.
    """
    while True:
        await run_refresh_once_async()
        await asyncio.sleep(refresh_settings.refresh_interval_seconds)

# --- Configurable sources and refresh interval ---
refresh_settings = RagRefreshSettings(
    refresh_interval_seconds=60 * 60 * 24,  # This can be loaded from env/config
    sources=[
        RagSourceConfig(
            name="Flare Dev Hub",
            type="github",
            collection_name="flare_dev_hub_docs",
            ttl=60 * 60 * 24,
            ingest_fn=github_ingest_fn,
            config={
                "repo": "flare-foundation/developer-hub",
                "branch": None,
            },
        ),
        RagSourceConfig(
            name="Governance Proposals",
            type="governance",
            collection_name="governance_proposals",
            ttl=60 * 60 * 24,
            ingest_fn=governance_ingest_fn,
            config={
                "url": "https://proposals.flare.network",
            },
        ),
        RagSourceConfig(
            name="Flare News",
            type="news",
            collection_name="flare_news",
            ttl=60 * 60 * 24,
            ingest_fn=news_ingest_fn,
            config={
                "url": "https://flare.network/news",
            },
        ),
    ],
)

# --- Entrypoint for manual testing ---
if __name__ == "__main__":
    # Example: run a single refresh cycle (for testing)
    asyncio.run(run_refresh_once_async())
    # To run periodically, use: asyncio.run(run_refresh_periodically()) 