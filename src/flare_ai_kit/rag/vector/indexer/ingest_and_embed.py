"""Ingest and embed pipeline for vector RAG."""

from typing import Any

from flare_ai_kit.rag.vector.embedding.base import BaseEmbedding
from flare_ai_kit.rag.vector.indexer.base import BaseIndexer


def ingest_and_embed(
    indexer: BaseIndexer,
    embedding_model: BaseEmbedding,
    batch_size: int = 32,
) -> list[dict[str, Any]]:
    """

    Process chunks from indexer and generate embeddings.

    Processes all chunks from the indexer, generates embeddings using the
    embedding model, and returns a list of dicts with embedding, text, and metadata.


    Args:
        indexer (BaseIndexer): The data indexer yielding text chunks and metadata.
        embedding_model (BaseEmbedding): The embedding model to use.
        batch_size (int): Number of chunks to embed per batch.

    Returns:
        list[dict[str, Any]]: Each dict contains 'embedding', 'text', and 'metadata'.

    """
    results: list[dict[str, Any]] = []
    batch_texts: list[str] = []
    batch_metadata: list[Any] = []

    for item in indexer.ingest():
        batch_texts.append(item["text"])
        batch_metadata.append(item["metadata"])
        if len(batch_texts) == batch_size:
            embeddings: list[Any] = embedding_model.embed_content(batch_texts)
            for emb, text, meta in zip(
                embeddings, batch_texts, batch_metadata, strict=False
            ):
                results.append({"embedding": emb, "text": text, "metadata": meta})
            batch_texts = []
            batch_metadata = []

    # Process any remaining items
    if batch_texts:
        embeddings: list[Any] = embedding_model.embed_content(batch_texts)
        for emb, text, meta in zip(
            embeddings, batch_texts, batch_metadata, strict=False
        ):
            results.append({"embedding": emb, "text": text, "metadata": meta})

    return results
