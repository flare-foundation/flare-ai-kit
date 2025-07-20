"""Qdrant upserter for vector storage."""

import uuid
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, PointStruct, VectorParams


def make_id(metadata: dict[str, Any]) -> str:
    """Generate a deterministic UUID for a chunk using its metadata."""
    key = f"{metadata.get('file_path', '')}:{metadata.get('chunk_index', '')}"
    # Use UUID5 to deterministically generate a UUID from the key
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, key))


def upsert_to_qdrant(
    data: list[dict[str, Any]],
    qdrant_url: str,
    collection_name: str,
    vector_size: int,
    batch_size: int = 100,
) -> None:
    """
    Upserts embeddings and metadata into a Qdrant collection.

    Args:
        data (List[Dict[str, Any]]): List of dicts with 'embedding', 'text',
            and 'metadata'.
        qdrant_url (str): Qdrant instance URL.
        collection_name (str): Name of the Qdrant collection.
        vector_size (int): Dimension of the embedding vectors.
        batch_size (int): Number of points to upsert per batch.

    """
    client = QdrantClient(qdrant_url)

    # Create collection if it doesn't exist
    if collection_name not in [c.name for c in client.get_collections().collections]:
        client.recreate_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )

    # Upsert in batches
    for i in range(0, len(data), batch_size):
        batch = data[i : i + batch_size]
        points = [
            PointStruct(
                id=make_id(item["metadata"]),
                vector=item["embedding"],
                payload={
                    **item["metadata"],
                    "text": item["text"],
                },
            )
            for item in batch
        ]
        client.upsert(collection_name=collection_name, points=points)
