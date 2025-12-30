"""Memory management operations."""

import secrets
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from powertools.core.config import get_project_config_dir, load_config
from powertools.core.embeddings import get_embedding_client
from powertools.storage.jsonl import JSONLStore
from powertools.storage.qdrant import QdrantStore


class MemoryCategory(str, Enum):
    """Memory category values."""

    ARCHITECTURE = "architecture"
    DECISION = "decision"
    PATTERN = "pattern"
    DEPENDENCY = "dependency"
    CONVENTION = "convention"
    FACT = "fact"


class Memory(BaseModel):
    """A memory/fact in project memory."""

    id: str
    content: str
    source: str | None = None
    category: MemoryCategory = MemoryCategory.FACT
    confidence: float = 1.0
    created: datetime = Field(default_factory=lambda: datetime.now(UTC))


def generate_memory_id() -> str:
    """Generate a unique memory ID."""
    return f"mem-{secrets.token_hex(4)}"


class MemoryManager:
    """Manages memory operations with vector search."""

    def __init__(self, project_dir: Path | None = None) -> None:
        self.project_dir = project_dir if project_dir is not None else get_project_config_dir()

        # JSONL store for metadata backup
        memories_file = self.project_dir / "memory" / "facts.jsonl"
        self.jsonl_store = JSONLStore(memories_file, Memory)

        # Load config for collection naming
        config = load_config()
        collection_name = f"pt_{config.project.name}"

        # Qdrant store for vector search
        self.vector_store = QdrantStore(collection_name)

        # Embedding client (uses provider from config)
        self.embeddings = get_embedding_client()

    def add(
        self,
        content: str,
        source: str | None = None,
        category: MemoryCategory = MemoryCategory.FACT,
        confidence: float = 1.0,
    ) -> Memory:
        """Add a new memory.

        Args:
            content: The fact/memory content.
            source: Optional source reference (e.g., file:line).
            category: Category of the memory.
            confidence: Confidence score (0.0-1.0).

        Returns:
            The created Memory object.
        """
        memory_id = generate_memory_id()

        # Ensure unique ID
        while self.jsonl_store.get_by_id(memory_id):
            memory_id = generate_memory_id()

        memory = Memory(
            id=memory_id,
            content=content,
            source=source,
            category=category,
            confidence=confidence,
        )

        # Generate embedding
        embedding = self.embeddings.embed(content)

        # Store in vector DB
        self.vector_store.upsert(
            id=memory_id,
            vector=embedding,
            payload={
                "content": content,
                "source": source,
                "category": category.value,
                "confidence": confidence,
                "created": memory.created.isoformat(),
            },
        )

        # Also store in JSONL for backup/portability
        self.jsonl_store.append(memory)

        return memory

    def search(
        self,
        query: str,
        limit: int = 10,
        category: MemoryCategory | None = None,
    ) -> list[dict[str, Any]]:
        """Search memories semantically.

        Args:
            query: Search query text.
            limit: Maximum results to return.
            category: Optional category filter.

        Returns:
            List of matching memories with scores.
        """
        # Generate query embedding
        query_embedding = self.embeddings.embed(query)

        # Build filter
        filter_conditions = None
        if category:
            filter_conditions = {"category": category.value}

        # Search vector store
        results = self.vector_store.search(
            vector=query_embedding,
            limit=limit,
            filter_conditions=filter_conditions,
        )

        return [
            {
                "id": r["id"],
                "content": r["payload"].get("content"),
                "source": r["payload"].get("source"),
                "category": r["payload"].get("category"),
                "confidence": r["payload"].get("confidence"),
                "score": r["score"],
            }
            for r in results
        ]

    def get(self, memory_id: str) -> Memory | None:
        """Get a memory by ID.

        Args:
            memory_id: The memory ID.

        Returns:
            Memory object or None if not found.
        """
        return self.jsonl_store.get_by_id(memory_id)

    def list_all(
        self,
        category: MemoryCategory | None = None,
        limit: int = 100,
    ) -> list[Memory]:
        """List all memories.

        Args:
            category: Optional category filter.
            limit: Maximum results to return.

        Returns:
            List of Memory objects.
        """
        # Read from Qdrant (source of truth) instead of JSONL
        filter_conditions = None
        if category:
            filter_conditions = {"category": category.value}

        results = self.vector_store.list_all(
            filter_conditions=filter_conditions,
            limit=limit,
        )

        # Convert Qdrant results to Memory objects
        memories = []
        for r in results:
            payload = r["payload"]
            try:
                created = datetime.fromisoformat(payload.get("created", ""))
            except (ValueError, TypeError):
                created = datetime.now(UTC)

            memory = Memory(
                id=r["id"],
                content=payload.get("content", ""),
                source=payload.get("source"),
                category=MemoryCategory(payload.get("category", "fact")),
                confidence=payload.get("confidence", 1.0),
                created=created,
            )
            memories.append(memory)

        # Sort by created date, newest first
        memories.sort(key=lambda m: m.created, reverse=True)

        return memories

    def delete(self, memory_id: str) -> bool:
        """Delete a memory.

        Args:
            memory_id: The memory ID to delete.

        Returns:
            True if deleted.
        """
        # Delete from vector store
        self.vector_store.delete(memory_id)

        # Delete from JSONL
        return self.jsonl_store.delete(memory_id)

    def health_check(self) -> dict[str, bool]:
        """Check health of memory system components."""
        return {
            "embeddings": self.embeddings.health_check(),
            "qdrant": self.vector_store.health_check(),
        }

    def close(self) -> None:
        """Close all connections."""
        self.embeddings.close()
        self.vector_store.close()
