import sys
from pathlib import Path

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

agent = AgentSettings()  # pyright: ignore[reportCallIssue]
vector_db = VectorDbSettings(qdrant_batch_size=8)

if __name__ == "__main__":
    # 1. Prepare a sample text file in a dedicated directory
    demo_dir = Path("demo_data")
    demo_dir.mkdir(parents=True, exist_ok=True)
    sample_text = (
        "Retrieval-Augmented Generation (RAG) is a technique that combines "
        "information retrieval with generative models.\n"
        "It allows large language models to access external knowledge bases "
        "for more accurate and up-to-date answers.\n"
        "This demo shows how to chunk, embed, store, and search text using Qdrant."
    )
    tmp_file = demo_dir / "rag_demo_sample.txt"
    with tmp_file.open("w", encoding="utf-8") as f:
        f.write(sample_text)

    # 2. Set up chunker and indexer to only index the demo_data directory
    chunker = FixedSizeChunker(chunk_size=15)
    indexer = LocalFileIndexer(
        root_dir=str(demo_dir), chunker=chunker, allowed_extensions={".txt"}
    )

    # 3. Use the Gemini embedding model for testing
    # Check if API key is configured
    if agent.gemini_api_key is None:
        print("❌ GEMINI_API_KEY environment variable not set.")
        print("Please set the GEMINI_API_KEY environment variable to run this demo.")
        print("Example: export GEMINI_API_KEY='your_api_key_here'")
        sys.exit(1)

    embedding_model = GeminiEmbedding(
        api_key=agent.gemini_api_key.get_secret_value(),
        model=vector_db.embeddings_model,
        output_dimensionality=vector_db.embeddings_output_dimensionality,
    )

    # 4. Ingest and embed
    data = ingest_and_embed(indexer, embedding_model, batch_size=8)
    print(f"Ingested and embedded {len(data)} chunks.")

    # 5. Upsert to Qdrant
    collection_name = "demo-collection"
    vector_size = 768  # Gemini embedding output size
    upsert_to_qdrant(
        data,
        str(vector_db.qdrant_url),
        collection_name,
        vector_size,
        batch_size=vector_db.qdrant_batch_size,
    )
    print(f"Upserted {len(data)} vectors to Qdrant collection '{collection_name}'.")

    # 6. Retrieve using QdrantRetriever
    client = QdrantClient(str(vector_db.qdrant_url))
    settings = VectorDbSettings()
    retriever = QdrantRetriever(client, embedding_model, settings)
    query = "What is RAG?"
    results = retriever.semantic_search(query, collection_name, top_k=3)
    print(f"\nTop results for query: '{query}'\n")
    for i, res in enumerate(results, 1):
        print(f"Result {i} (score={res.score:.3f}):\n{res.text}\n---")

    # Cleanup demo file and directory
    tmp_file.unlink()
    demo_dir.rmdir()
