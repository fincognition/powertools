"""
Powertools Embedding Server

A lightweight HTTP server that provides OpenAI-compatible /v1/embeddings endpoint
using MLX for Apple Silicon GPU acceleration.

Runs as a system daemon via launchd, shared across all projects.
"""

import argparse
import json
import logging

# Check for Apple Silicon before importing MLX
import platform
import sys
import time
from typing import Any

if platform.machine() != "arm64" or platform.system() != "Darwin":
    print("Error: powertools-embed requires Apple Silicon Mac (M1/M2/M3/M4)")
    print(f"Detected: {platform.system()} {platform.machine()}")
    sys.exit(1)

try:
    import mlx.core as mx  # noqa: F401 - imported to verify mlx is available
    from mlx_embeddings.utils import load as load_model  # type: ignore[import-untyped]
except ImportError:
    print("Error: mlx-embeddings not installed. Install with:")
    print("  uv pip install powertools")
    print("  pt init")
    print("  # or")
    print("  pt embed install")
    sys.exit(1)

import uvicorn
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("powertools-embed")

# Default model - Qwen3 embedding model (4-bit quantized)
DEFAULT_MODEL = "mlx-community/Qwen3-Embedding-0.6B-4bit-DWQ"

# Global model state
_model = None
_tokenizer = None
_model_name = None


def get_model() -> tuple[Any, Any]:  # type: ignore[no-any-return]
    """Get or load the embedding model (lazy loading)."""
    global _model, _tokenizer, _model_name

    if _model is None:
        model_name = _model_name or DEFAULT_MODEL
        logger.info(f"Loading model: {model_name}")
        start = time.time()
        _model, _tokenizer = load_model(model_name)  # type: ignore[no-untyped-call]
        elapsed = time.time() - start
        logger.info(f"Model loaded in {elapsed:.2f}s")

    return _model, _tokenizer


def compute_embeddings(texts: list[str]) -> list[list[float]]:
    """Compute embeddings for a list of texts."""
    model, tokenizer = get_model()

    # Tokenize inputs
    inputs = tokenizer.batch_encode_plus(  # type: ignore[no-untyped-call]
        texts,
        return_tensors="mlx",
        padding=True,
        truncation=True,
        max_length=8192,  # Qwen3 supports up to 32K, but limit for memory
    )

    # Get embeddings
    outputs = model(  # type: ignore[no-untyped-call]
        inputs["input_ids"],
        attention_mask=inputs.get("attention_mask"),
    )

    # Use text_embeds (mean pooled and normalized)
    embeddings = outputs.text_embeds

    # Convert to Python list
    return embeddings.tolist()  # type: ignore[no-any-return]


async def health(request: Request) -> JSONResponse:
    """Health check endpoint."""
    return JSONResponse(
        {
            "status": "ok",
            "model": _model_name or DEFAULT_MODEL,
            "loaded": _model is not None,
        }
    )


async def embeddings(request: Request) -> JSONResponse:
    """
    OpenAI-compatible /v1/embeddings endpoint.

    Request body:
    {
        "input": "text" or ["text1", "text2", ...],
        "model": "optional-model-name",
        "encoding_format": "float" (default) or "base64"
    }

    Response:
    {
        "object": "list",
        "data": [
            {"object": "embedding", "embedding": [...], "index": 0},
            ...
        ],
        "model": "model-name",
        "usage": {"prompt_tokens": N, "total_tokens": N}
    }
    """
    try:
        body = await request.json()
    except json.JSONDecodeError:
        return JSONResponse(
            {"error": {"message": "Invalid JSON", "type": "invalid_request_error"}},
            status_code=400,
        )

    # Extract input
    input_data = body.get("input")
    if input_data is None:
        return JSONResponse(
            {"error": {"message": "Missing 'input' field", "type": "invalid_request_error"}},
            status_code=400,
        )

    # Normalize to list
    if isinstance(input_data, str):
        texts = [input_data]
    elif isinstance(input_data, list):
        texts = input_data
    else:
        return JSONResponse(
            {
                "error": {
                    "message": "'input' must be string or array",
                    "type": "invalid_request_error",
                }
            },
            status_code=400,
        )

    if not texts:
        return JSONResponse(
            {"error": {"message": "'input' cannot be empty", "type": "invalid_request_error"}},
            status_code=400,
        )

    # Compute embeddings
    try:
        start = time.time()
        embedding_vectors = compute_embeddings(texts)
        elapsed = time.time() - start
        logger.info(f"Generated {len(texts)} embeddings in {elapsed:.3f}s")
    except Exception as e:
        logger.exception("Error computing embeddings")
        return JSONResponse(
            {"error": {"message": str(e), "type": "server_error"}},
            status_code=500,
        )

    # Build response
    data = [
        {
            "object": "embedding",
            "embedding": vec,
            "index": i,
        }
        for i, vec in enumerate(embedding_vectors)
    ]

    # Estimate token count (rough approximation)
    total_chars = sum(len(t) for t in texts)
    estimated_tokens = total_chars // 4  # ~4 chars per token

    response = {
        "object": "list",
        "data": data,
        "model": _model_name or DEFAULT_MODEL,
        "usage": {
            "prompt_tokens": estimated_tokens,
            "total_tokens": estimated_tokens,
        },
    }

    return JSONResponse(response)


async def models(request: Request) -> JSONResponse:
    """List available models (OpenAI-compatible)."""
    return JSONResponse(
        {
            "object": "list",
            "data": [
                {
                    "id": _model_name or DEFAULT_MODEL,
                    "object": "model",
                    "created": 1700000000,
                    "owned_by": "powertools",
                }
            ],
        }
    )


# Routes
routes = [
    Route("/health", health, methods=["GET"]),
    Route("/v1/embeddings", embeddings, methods=["POST"]),
    Route("/v1/models", models, methods=["GET"]),
]

app = Starlette(routes=routes)


def main() -> None:
    """Main entry point for powertools-embed command."""
    parser = argparse.ArgumentParser(
        description="Powertools Embedding Server - MLX-powered embeddings for Apple Silicon"
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind to (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8384,
        help="Port to bind to (default: 8384)",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"Model to use (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--preload",
        action="store_true",
        help="Preload model on startup instead of lazy loading",
    )
    parser.add_argument(
        "--log-level",
        default="info",
        choices=["debug", "info", "warning", "error"],
        help="Log level (default: info)",
    )

    args = parser.parse_args()

    # Set global model name
    global _model_name
    _model_name = args.model

    # Configure logging
    logging.getLogger().setLevel(args.log_level.upper())

    # Preload model if requested
    if args.preload:
        logger.info("Preloading model...")
        get_model()

    logger.info(f"Starting powertools-embed server on {args.host}:{args.port}")
    logger.info(f"Model: {_model_name}")

    # Run server
    uvicorn.run(  # type: ignore[no-untyped-call]
        app,
        host=args.host,
        port=args.port,
        log_level=args.log_level,
    )


if __name__ == "__main__":
    main()
