import os
from typing import List
from flare_ai_kit.rag.vector.indexer.fixed_size_chunker import FixedSizeChunker
from flare_ai_kit.rag.vector.indexer.local_file_indexer import LocalFileIndexer
from flare_ai_kit.rag.vector.indexer.ingest_and_embed import ingest_and_embed
from flare_ai_kit.rag.vector.indexer.qdrant_upserter import upsert_to_qdrant
from flare_ai_kit.rag.vector.retriever.qdrant_retriever import QdrantRetriever
from flare_ai_kit.rag.vector.embedding.gemini_embedding import GeminiEmbedding
from qdrant_client import QdrantClient
from pydantic import BaseModel, Field, PositiveInt


# VectorDbSettingsModel for retriever
class VectorDbSettingsModel(BaseModel):
    qdrant_vector_size: PositiveInt = Field(768)  # Gemini embedding default size
    qdrant_batch_size: PositiveInt = Field(100)
    embeddings_model: str = Field("demo-collection")


if __name__ == "__main__":
    # 1. Prepare a sample text file
    sample_text = """
    Retrieval-Augmented Generation (RAG) is a technique that combines information retrieval with generative models. 
    It allows large language models to access external knowledge bases for more accurate and up-to-date answers.
    This demo shows how to chunk, embed, store, and search text using Qdrant.
    """
    tmp_file = "rag_demo_sample.txt"
    with open(tmp_file, "w", encoding="utf-8") as f:
        f.write(sample_text)

    # 2. Set up chunker and indexer
    chunker = FixedSizeChunker(chunk_size=15)
    indexer = LocalFileIndexer(
        root_dir=".", chunker=chunker, allowed_extensions={".txt"}
    )

    # 3. Use the Gemini embedding model
    api_key = os.environ.get("GEMINI_API_KEY")
    model = "gemini-embedding-001"
    output_dimensionality = 768
    embedding_model = GeminiEmbedding(
        api_key=api_key, model=model, output_dimensionality=output_dimensionality
    )

    # 4. Ingest and embed
    data = ingest_and_embed(indexer, embedding_model, batch_size=8)
    print(f"Ingested and embedded {len(data)} chunks.")

    # 5. Upsert to Qdrant
    qdrant_url = "http://localhost:6333"
    collection_name = "demo-collection"
    vector_size = 768  # Gemini embedding output size
    upsert_to_qdrant(data, qdrant_url, collection_name, vector_size, batch_size=8)
    print(f"Upserted {len(data)} vectors to Qdrant collection '{collection_name}'.")

    # 6. Retrieve using QdrantRetriever
    client = QdrantClient(qdrant_url)
    settings = VectorDbSettingsModel()
    retriever = QdrantRetriever(client, embedding_model, settings)
    query = "What is RAG?"
    results = retriever.semantic_search(query, collection_name, top_k=3)
    print(f"\nTop results for query: '{query}'\n")
    for i, res in enumerate(results, 1):
        print(f"Result {i} (score={res['score']:.3f}):\n{res['text']}\n---")

    # Cleanup demo file
    os.remove(tmp_file)
