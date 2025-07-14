from typing import List, Dict, Any
from .base import BaseIndexer
from ..embedding.base import BaseEmbedding


def ingest_and_embed(
    indexer: BaseIndexer,
    embedding_model: BaseEmbedding,
    batch_size: int = 32,
) -> List[Dict[str, Any]]:
    """
    Processes all chunks from the indexer, generates embeddings using the embedding model,
    and returns a list of dicts with embedding, text, and metadata.

    Args:
        indexer (BaseIndexer): The data indexer yielding text chunks and metadata.
        embedding_model (BaseEmbedding): The embedding model to use.
        batch_size (int): Number of chunks to embed per batch.

    Returns:
        List[Dict[str, Any]]: Each dict contains 'embedding', 'text', and 'metadata'.
    """
    results = []
    batch_texts = []
    batch_metadata = []

    for item in indexer.ingest():
        batch_texts.append(item['text'])
        batch_metadata.append(item['metadata'])
        if len(batch_texts) == batch_size:
            embeddings = embedding_model.embed_content(batch_texts)
            for emb, text, meta in zip(embeddings, batch_texts, batch_metadata):
                results.append({'embedding': emb, 'text': text, 'metadata': meta})
            batch_texts = []
            batch_metadata = []

    # Process any remaining items
    if batch_texts:
        embeddings = embedding_model.embed_content(batch_texts)
        for emb, text, meta in zip(embeddings, batch_texts, batch_metadata):
            results.append({'embedding': emb, 'text': text, 'metadata': meta})

    return results 