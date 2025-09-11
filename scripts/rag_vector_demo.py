#!/usr/bin/env python3
"""
RAG Vector Demo Script

This script demonstrates Retrieval-Augmented Generation (RAG) using vector embeddings.
It shows how to chunk, embed, store, and search text using Qdrant vector database.
Requires: rag extras (qdrant-client, dulwich)

Usage:
    python scripts/rag_vector_demo.py

Environment Variables:
    AGENT__GEMINI_API_KEY: Gemini API key for embeddings
    VECTOR_DB__QDRANT_URL: Qdrant server URL (default: http://localhost:6333)
    VECTOR_DB__COLLECTION_NAME: Collection name (default: flare_ai_kit)
"""

import asyncio
import sys
from pathlib import Path

# Add src to path for local development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from qdrant_client import QdrantClient

from flare_ai_kit.agent import AgentSettings
from flare_ai_kit.rag import (
    FixedSizeChunker,
    GeminiEmbedding,
    LocalFileIndexer,
    QdrantRetriever,
    ingest_and_embed,
    upsert_to_qdrant,
)
from flare_ai_kit.rag.vector.settings import VectorDbSettings


async def setup_demo_data() -> Path:
    """Create sample text data for the RAG demo."""
    print("📁 Setting up demo data...")

    # 1. Prepare a sample text file in a dedicated directory
    demo_dir = Path("demo_data")
    demo_dir.mkdir(parents=True, exist_ok=True)

    sample_text = (
        "Retrieval-Augmented Generation (RAG) is a technique that combines "
        "information retrieval with generative models.\n"
        "It allows large language models to access external knowledge bases "
        "for more accurate and up-to-date answers.\n"
        "This demo shows how to chunk, embed, store, and search text using Qdrant.\n"
        "Flare Network is a blockchain platform that provides decentralized data "
        "to smart contracts through its Time Series Oracle (FTSO) system.\n"
        "The Flare AI Kit enables developers to build verifiable AI agents "
        "that can interact with blockchain data and external APIs securely.\n"
        "Vector databases like Qdrant are essential for semantic search "
        "and retrieval-augmented generation applications.\n"
        "Embeddings transform text into high-dimensional vectors that capture "
        "semantic meaning and enable similarity-based search operations."
    )

    tmp_file = demo_dir / "rag_demo_sample.txt"
    with tmp_file.open("w", encoding="utf-8") as f:
        f.write(sample_text)

    print(f"✅ Created demo file: {tmp_file}")
    return demo_dir


async def setup_rag_components() -> tuple[
    FixedSizeChunker, LocalFileIndexer, GeminiEmbedding, QdrantClient
]:
    """Initialize RAG components."""
    print("🔧 Setting up RAG components...")

    agent = AgentSettings()  # pyright: ignore[reportCallIssue]
    vector_db = VectorDbSettings(qdrant_batch_size=8)

    # 2. Set up chunker and indexer
    chunker = FixedSizeChunker(chunk_size=15)

    # 3. Use the Gemini embedding model
    embedding_model = GeminiEmbedding(
        api_key=agent.gemini_api_key.get_secret_value(),
        model=vector_db.embeddings_model,
        output_dimensionality=vector_db.embeddings_output_dimensionality,
    )

    # 4. Set up Qdrant client
    qdrant_client = QdrantClient(url=vector_db.qdrant_url)

    print("✅ RAG components initialized")
    return chunker, embedding_model, qdrant_client, vector_db


async def ingest_documents(
    demo_dir: Path,
    chunker: FixedSizeChunker,
    embedding_model: GeminiEmbedding,
    qdrant_client: QdrantClient,
    vector_db: VectorDbSettings,
) -> None:
    """Ingest and embed documents into Qdrant."""
    print("📚 Ingesting documents...")

    # Set up indexer to only index the demo_data directory
    indexer = LocalFileIndexer(
        root_dir=str(demo_dir), chunker=chunker, allowed_extensions={".txt"}
    )

    # 5. Ingest and embed documents
    chunks = await ingest_and_embed(indexer, embedding_model)
    print(f"📄 Generated {len(chunks)} text chunks")

    # 6. Upsert chunks to Qdrant
    await upsert_to_qdrant(
        qdrant_client,
        chunks,
        collection_name=vector_db.collection_name,
        vector_size=vector_db.embeddings_output_dimensionality,
        batch_size=vector_db.qdrant_batch_size,
    )
    print(
        f"✅ Uploaded {len(chunks)} chunks to Qdrant collection '{vector_db.collection_name}'"
    )


async def perform_semantic_search(
    embedding_model: GeminiEmbedding,
    qdrant_client: QdrantClient,
    vector_db: VectorDbSettings,
) -> None:
    """Perform semantic search queries."""
    print("🔍 Performing semantic search...")

    # 7. Set up retriever for semantic search
    retriever = QdrantRetriever(
        client=qdrant_client,
        embedding_client=embedding_model,
        collection_name=vector_db.collection_name,
        top_k=3,
    )

    # 8. Perform semantic searches
    queries = [
        "What is RAG?",
        "How does Flare Network work?",
        "What are vector databases used for?",
        "Tell me about embeddings",
    ]

    for query in queries:
        print(f"\n🔎 Query: '{query}'")
        try:
            results = await retriever.search(query)
            print(f"📊 Found {len(results)} relevant chunks:")

            for i, result in enumerate(results, 1):
                print(f"   {i}. Score: {result.score:.4f}")
                print(f"      Text: {result.chunk.text[:100]}...")
                print(f"      Source: {result.chunk.metadata.source}")

        except Exception as e:
            print(f"❌ Search failed for query '{query}': {e}")


async def cleanup_demo_data(demo_dir: Path) -> None:
    """Clean up demo data."""
    print("🧹 Cleaning up demo data...")
    try:
        import shutil

        if demo_dir.exists():
            shutil.rmtree(demo_dir)
            print("✅ Demo data cleaned up")
    except Exception as e:
        print(f"⚠️  Warning: Could not clean up demo data: {e}")


async def main() -> None:
    """Main function demonstrating RAG vector operations."""
    print("🔍 Starting RAG Vector Demo...")

    demo_dir = None
    try:
        # Setup demo data
        demo_dir = await setup_demo_data()

        # Setup RAG components
        (
            chunker,
            embedding_model,
            qdrant_client,
            vector_db,
        ) = await setup_rag_components()

        # Ingest documents
        await ingest_documents(
            demo_dir, chunker, embedding_model, qdrant_client, vector_db
        )

        # Perform semantic search
        await perform_semantic_search(embedding_model, qdrant_client, vector_db)

        print("\n🎉 RAG Vector Demo completed successfully!")
        print("💡 Try modifying the sample text or queries to experiment further!")

    except Exception as e:
        print(f"❌ Demo failed: {e}")
        raise
    finally:
        # Cleanup
        if demo_dir:
            await cleanup_demo_data(demo_dir)


if __name__ == "__main__":
    asyncio.run(main())
