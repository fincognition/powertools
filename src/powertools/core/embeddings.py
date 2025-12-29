"""Embedding client for powertools.

This module provides a client for generating embeddings via the powertools-embed
daemon, which runs as a local HTTP server on the host machine.
"""

import httpx

from powertools.core.config import load_config


class EmbeddingClient:
    """Client for generating embeddings via the powertools-embed daemon.

    The daemon provides an OpenAI-compatible /v1/embeddings endpoint.
    """

    def __init__(self, api_base: str | None = None) -> None:
        config = load_config()
        self.api_base = api_base or config.embedding.api_base
        self._client: httpx.Client | None = None

    @property
    def client(self) -> httpx.Client:
        """Lazy initialization of HTTP client."""
        if self._client is None:
            self._client = httpx.Client(
                timeout=60.0
            )  # Longer timeout for first request (model loading)
        return self._client

    def embed(self, text: str) -> list[float]:
        """Generate embedding for a single text."""
        return self.embed_batch([text])[0]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts via the embedding daemon.

        Args:
            texts: List of texts to embed.

        Returns:
            List of embedding vectors.

        Raises:
            httpx.ConnectError: If the daemon is not running.
            httpx.HTTPStatusError: If the request fails.
        """
        try:
            response = self.client.post(
                f"{self.api_base}/v1/embeddings",
                json={"input": texts},
            )
            response.raise_for_status()

            data = response.json()
            embeddings = sorted(data["data"], key=lambda x: x["index"])
            return [e["embedding"] for e in embeddings]
        except httpx.ConnectError:
            raise ConnectionError(
                f"Cannot connect to embedding daemon at {self.api_base}. "
                "Make sure the daemon is running: pt embed status"
            ) from None

    def health_check(self) -> bool:
        """Check if the embedding daemon is healthy."""
        try:
            response = self.client.get(f"{self.api_base}/health")
            return response.status_code == 200
        except Exception:
            return False

    def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            self._client.close()
            self._client = None

    def __enter__(self) -> "EmbeddingClient":
        return self

    def __exit__(self, *args) -> None:
        self.close()


class AsyncEmbeddingClient:
    """Async client for generating embeddings via the powertools-embed daemon.

    Used by the MCP server running in Docker containers.
    """

    def __init__(self, api_base: str | None = None) -> None:
        config = load_config()
        self.api_base = api_base or config.embedding.api_base
        self._client: httpx.AsyncClient | None = None

    @property
    def client(self) -> httpx.AsyncClient:
        """Lazy initialization of async HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=60.0)
        return self._client

    async def embed(self, text: str) -> list[float]:
        """Generate embedding for a single text."""
        embeddings = await self.embed_batch([text])
        return embeddings[0]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts via the embedding daemon.

        Args:
            texts: List of texts to embed.

        Returns:
            List of embedding vectors.
        """
        try:
            response = await self.client.post(
                f"{self.api_base}/v1/embeddings",
                json={"input": texts},
            )
            response.raise_for_status()

            data = response.json()
            embeddings = sorted(data["data"], key=lambda x: x["index"])
            return [e["embedding"] for e in embeddings]
        except httpx.ConnectError:
            raise ConnectionError(
                f"Cannot connect to embedding daemon at {self.api_base}. "
                "Make sure the daemon is running: pt embed status"
            ) from None

    async def health_check(self) -> bool:
        """Check if the embedding daemon is healthy."""
        try:
            response = await self.client.get(f"{self.api_base}/health")
            return response.status_code == 200
        except Exception:
            return False

    async def close(self) -> None:
        """Close the async HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> "AsyncEmbeddingClient":
        return self

    async def __aexit__(self, *args) -> None:
        await self.close()


def get_embedding_client(api_base: str | None = None) -> EmbeddingClient:
    """Get an embedding client.

    Args:
        api_base: Override the configured API base URL.

    Returns:
        An EmbeddingClient instance.
    """
    return EmbeddingClient(api_base=api_base)


def get_async_embedding_client(api_base: str | None = None) -> AsyncEmbeddingClient:
    """Get an async embedding client.

    Args:
        api_base: Override the configured API base URL.

    Returns:
        An AsyncEmbeddingClient instance.
    """
    return AsyncEmbeddingClient(api_base=api_base)
