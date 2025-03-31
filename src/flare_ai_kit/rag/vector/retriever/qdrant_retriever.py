"""VectorDB retriever using Qdrant."""

import uuid
from typing import override

import google.api_core.exceptions
import structlog
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, PointStruct, VectorParams

from flare_ai_kit.common import Chunk, SemanticSearchResult
from flare_ai_kit.config import VectorDbSettingsModel
from flare_ai_kit.rag.vector.embedding import EmbeddingTaskType, GeminiEmbedding

from .base import BaseRetriever

# Initialize logger
logger = structlog.get_logger(__name__)


class QdrantRetriever(BaseRetriever):
    """Interacting with Qdrant VectorDB, semantic search and indexing."""

    def __init__(
        self,
        client: QdrantClient,
        vectordb_config: VectorDbSettingsModel,
        embedding_client: GeminiEmbedding,
    ) -> None:
        """
        Initialize the QdrantRetriever.

        :param client: An initialized QdrantClient instance.
        :param retriever_config: Configuration object containing settings like
                                 collection_name, vector_size, embedding models.
        :param embedding_client: An embedding client (e.g., GeminiEmbedding).
        """
        self.client = client
        self.vectordb_config = vectordb_config
        self.embedding_client = embedding_client
        self.embedding_model = self.vectordb_config.embeddings_model
        self.vector_size = self.vectordb_config.qdrant_vector_size
        self.batch_size = self.vectordb_config.qdrant_batch_size

    def _create_collection(self, collection_name: str, vector_size: int) -> None:
        """
        Creates or recreates a Qdrant collection.

        Warning: This will delete the collection if it already exists.

        :param collection_name: Name of the collection.
        :param vector_size: Dimension of the vectors.
        """
        try:
            self.client.recreate_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
            )
            logger.info(
                "Successfully created/recreated collection",
                collection_name=collection_name,
                vector_size=vector_size,
            )
        except Exception as e:
            logger.exception(
                "Failed to create/recreate Qdrant collection",
                collection_name=collection_name,
                error=str(e),
            )
            raise  # Re-raise the exception after logging

    def embed_and_upsert(
        self,
        data: list[Chunk],
        collection_name: str,
    ) -> None:
        """
        Indexes documents from a Pandas DataFrame into the Qdrant collection.

        This involves creating embeddings and upserting them.
        It first recreates the collection as specified in the config.

        Requires DataFrame columns: 'content', 'file_name', 'meta_data'.

        :param df_docs: DataFrame containing the documents to index.
        :param batch_size: Number of documents to upsert in each batch.
        """
        # Ensure the collection exists (or is recreated)
        self._create_collection(collection_name, self.vector_size)

        points_batch: list[PointStruct] = []
        processed_count = 0
        skipped_count = 0
        total_docs = len(data)

        logger.info(
            "Starting indexing process",
            total_documents=total_docs,
            collection_name=collection_name,
            batch_size=self.batch_size,
        )

        for idx, element in enumerate(data):
            title = None
            try:
                contents = element.text
                title = element.metadata.original_filepath
                # Calculate embedding using Gemini
                embedding = self.embedding_client.embed_content(
                    embedding_model=self.embedding_model,
                    task_type=EmbeddingTaskType.RETRIEVAL_DOCUMENT,
                    contents=contents,
                    title=title,
                )
            except google.api_core.exceptions.InvalidArgument as e:
                if "Request payload size exceeds the limit" in str(e):
                    logger.warning(
                        "Skipping document due to embedding size limit.",
                        index=idx,
                        title=title,
                        error=str(e),
                    )
                else:
                    logger.exception(
                        "Skipping document due to invalid argument during embedding.",
                        index=idx,
                        title=title,
                    )
                skipped_count += 1
                continue
            except Exception:
                logger.exception(
                    "Skipping document due to unexpected error during embedding.",
                    index=idx,
                    title=title,
                )
                skipped_count += 1
                continue

            # Prepare payload, ensuring metadata is serializable
            payload = {
                "text": contents,
                "filename": title,
                # Ensure metadata is a dictionary (or handle other types if needed)
                "metadata": element.metadata,
            }

            point = PointStruct(
                id=str(uuid.uuid4()),  # Use UUID for robust unique IDs
                vector=embedding,  # Use the extracted vector
                payload=payload,
            )
            points_batch.append(point)

            # Upsert batch if it reaches the desired size
            if len(points_batch) >= self.batch_size:
                try:
                    # Set wait=False for potentially faster async upsert
                    self.client.upsert(
                        collection_name=collection_name,
                        points=points_batch,
                        wait=False,
                    )
                    processed_count += len(points_batch)
                    logger.info(
                        "Upserted batch to Qdrant",
                        batch_size=len(points_batch),
                        processed_count=processed_count,
                        collection_name=collection_name,
                    )
                    points_batch = []  # Clear the batch
                except Exception:
                    logger.exception(
                        "Failed to upsert batch to Qdrant",
                        collection_name=collection_name,
                        batch_size=len(points_batch),
                    )
                    # Decide how to handle batch failure: skip batch, retry, etc.
                    # For now, just log and continue with next batch
                    points_batch = []  # Clear failed batch

        # Upsert any remaining points
        if points_batch:
            try:
                self.client.upsert(
                    collection_name=collection_name,
                    points=points_batch,
                    wait=True,  # Wait for the final batch to ensure completion
                )
                processed_count += len(points_batch)
                logger.info(
                    "Upserted final batch to Qdrant",
                    batch_size=len(points_batch),
                    processed_count=processed_count,
                    collection_name=collection_name,
                )
            except Exception:
                logger.exception(
                    "Failed to upsert final batch to Qdrant",
                    collection_name=collection_name,
                    batch_size=len(points_batch),
                )

        logger.info(
            "Indexing process completed.",
            collection_name=collection_name,
            total_documents=total_docs,
            successfully_processed=processed_count,
            skipped=skipped_count,
        )

    @override
    def semantic_search(
        self,
        query: str,
        collection_name: str,
        top_k: int = 5,
        score_threshold: float | None = None,
    ) -> list[SemanticSearchResult]:
        """
        Perform semantic search using the configured query embedding model.

        :param query: The input query string.
        :param top_k: Number of top results to return.
        :param score_threshold: Optional minimum score threshold for results.
        :return: A list of SemanticSearchResult.
        """
        try:
            # Convert the query into a vector embedding
            query_vector = self.embedding_client.embed_content(
                embedding_model=self.vectordb_config.embeddings_model,
                contents=query,
                task_type=EmbeddingTaskType.RETRIEVAL_QUERY,
            )

            # Search Qdrant for similar vectors.
            search_result = self.client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                limit=top_k,
                score_threshold=score_threshold,  # Pass threshold if provided
                with_payload=True,  # Ensure payload is returned
            )

            # Process and return results.
            output: list[SemanticSearchResult] = []
            for hit in search_result:
                payload = hit.payload if hit.payload else {}
                text = payload.get("text", "")
                # Exclude 'text' from metadata, include everything else from payload
                metadata = {k: v for k, v in payload.items() if k != "text"}
                result = SemanticSearchResult(
                    text=text, score=hit.score, metadata=metadata
                )
                output.append(result)

            logger.info(
                "Semantic search performed successfully.",
                query=query,
                top_k=top_k,
                results_found=len(output),
                collection_name=collection_name,
            )
        except Exception as e:
            logger.exception(
                "Error during semantic search.",
                query=query,
                collection_name=collection_name,
                error=str(e),
            )
            return []
        else:
            return output
