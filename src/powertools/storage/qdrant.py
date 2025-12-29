"""Qdrant vector database client wrapper."""

from collections.abc import Sequence
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

from powertools.core.config import load_config


class QdrantStore:
    """Wrapper for Qdrant vector database operations."""

    def __init__(
        self,
        collection_name: str,
        url: str | None = None,
        dimensions: int | None = None,
    ) -> None:
        config = load_config()
        self.url = url or config.qdrant.url
        self.dimensions = dimensions or config.embedding.dimensions
        self.collection_name = collection_name
        self._client: QdrantClient | None = None

    @property
    def client(self) -> QdrantClient:
        """Lazy initialization of Qdrant client."""
        if self._client is None:
            self._client = QdrantClient(url=self.url)
        return self._client

    def ensure_collection(self) -> None:
        """Ensure the collection exists, creating it if necessary."""
        collections = self.client.get_collections().collections
        exists = any(c.name == self.collection_name for c in collections)

        if not exists:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.dimensions,
                    distance=Distance.COSINE,
                ),
            )

    def upsert(
        self,
        id: str,
        vector: list[float],
        payload: dict[str, Any],
    ) -> None:
        """Insert or update a point in the collection.

        Args:
            id: Unique identifier for the point.
            vector: Embedding vector.
            payload: Metadata to store with the point.
        """
        self.ensure_collection()

        # Store original ID in payload for retrieval
        payload["_id"] = id

        self.client.upsert(
            collection_name=self.collection_name,
            points=[
                PointStruct(
                    id=self._hash_id(id),
                    vector=vector,
                    payload=payload,
                )
            ],
        )

    def search(
        self,
        vector: list[float],
        limit: int = 10,
        filter_conditions: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Search for similar vectors.

        Args:
            vector: Query vector.
            limit: Maximum number of results.
            filter_conditions: Optional filter conditions as {field: value}.

        Returns:
            List of results with payload and score.
        """
        self.ensure_collection()

        # Build filter if conditions provided
        query_filter = None
        if filter_conditions:
            must = [
                FieldCondition(key=k, match=MatchValue(value=v))
                for k, v in filter_conditions.items()
            ]
            query_filter = Filter(must=must)

        results = self.client.query_points(
            collection_name=self.collection_name,
            query=vector,
            limit=limit,
            query_filter=query_filter,
        )

        return [
            {
                "id": r.payload.get("_id") if r.payload else None,
                "score": r.score,
                "payload": {k: v for k, v in (r.payload.items() if r.payload else []) if k != "_id"},
            }
            for r in results.points
        ]

    def get(self, id: str) -> dict[str, Any] | None:
        """Get a point by ID.

        Args:
            id: The point ID.

        Returns:
            Point payload or None if not found.
        """
        self.ensure_collection()

        results = self.client.retrieve(
            collection_name=self.collection_name,
            ids=[self._hash_id(id)],
            with_payload=True,
        )

        if not results:
            return None

        payload = results[0].payload
        if not payload:
            return None
        return {
            "id": payload.get("_id"),
            "payload": {k: v for k, v in payload.items() if k != "_id"},
        }

    def delete(self, id: str) -> bool:
        """Delete a point by ID.

        Args:
            id: The point ID.

        Returns:
            True if deleted (or didn't exist).
        """
        self.ensure_collection()

        self.client.delete(
            collection_name=self.collection_name,
            points_selector=[self._hash_id(id)],
        )
        return True

    def list_all(
        self,
        filter_conditions: dict[str, Any] | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """List all points in the collection.

        Args:
            filter_conditions: Optional filter conditions.
            limit: Maximum number of results.

        Returns:
            List of points with payloads.
        """
        self.ensure_collection()

        # Build filter if conditions provided
        query_filter: Filter | None = None
        if filter_conditions:
            must: Sequence[FieldCondition] = [
                FieldCondition(key=k, match=MatchValue(value=v))
                for k, v in filter_conditions.items()
            ]
            query_filter = Filter(must=must)

        # Use scroll to get all points
        results, _ = self.client.scroll(
            collection_name=self.collection_name,
            limit=limit,
            scroll_filter=query_filter,
            with_payload=True,
        )

        return [
            {
                "id": r.payload.get("_id") if r.payload else None,
                "payload": {k: v for k, v in (r.payload.items() if r.payload else []) if k != "_id"},
            }
            for r in results
        ]

    def count(self) -> int:
        """Get the number of points in the collection."""
        self.ensure_collection()
        info = self.client.get_collection(self.collection_name)
        return info.points_count or 0

    def health_check(self) -> bool:
        """Check if Qdrant is healthy."""
        try:
            self.client.get_collections()
            return True
        except Exception:
            return False

    def _hash_id(self, id: str) -> int:
        """Convert string ID to integer hash for Qdrant.

        Qdrant requires integer or UUID point IDs.
        """
        # Use hash to convert string to int, handle negatives
        return abs(hash(id)) % (2**63)

    def close(self) -> None:
        """Close the Qdrant client."""
        if self._client is not None:
            self._client.close()
            self._client = None
