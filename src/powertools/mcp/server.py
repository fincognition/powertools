"""MCP server setup with SSE transport."""

import asyncio
import os
from pathlib import Path
from typing import Any

import uvicorn
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import TextContent, Tool
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route

from powertools.core.memory import MemoryManager
from powertools.core.tasks import TaskManager
from powertools.mcp.memory import get_memory_tools, handle_memory_tool
from powertools.mcp.tasks import get_task_tools, handle_task_tool


def create_server(project_dir: Path | None = None) -> Server:
    """Create and configure the MCP server."""
    server = Server("powertools")

    # Initialize managers
    task_manager = TaskManager(project_dir)
    memory_manager = MemoryManager(project_dir)

    # Register combined tools from both modules
    @server.list_tools()  # type: ignore[no-untyped-call]
    async def list_tools() -> list[Tool]:
        return get_task_tools() + get_memory_tools()

    @server.call_tool()  # type: ignore[no-untyped-call]
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
        # Try task tools first
        result = await handle_task_tool(name, arguments, task_manager)
        if result is not None:
            return result

        # Try memory tools
        result = await handle_memory_tool(name, arguments, memory_manager)
        if result is not None:
            return result

        # Unknown tool
        return [TextContent(type="text", text=f"Unknown tool: {name}")]

    return server


def create_app(project_dir: Path | None = None) -> Starlette:
    """Create the Starlette ASGI app with SSE endpoint."""
    server = create_server(project_dir)
    sse = SseServerTransport("/messages")

    async def handle_sse(request: Any) -> None:
        # Note: request._send is the ASGI send callable (private API but standard pattern)
        # The MCP SSE transport requires the ASGI scope, receive, and send callables
        async with sse.connect_sse(request.scope, request.receive, request._send) as streams:
            await server.run(streams[0], streams[1], server.create_initialization_options())

    async def handle_messages(request: Any) -> Any:
        # Handle POST messages from the client
        return await sse.handle_post_message(request.scope, request.receive, request._send)

    async def health(request: Any) -> JSONResponse:
        return JSONResponse({"status": "ok", "server": "powertools"})

    # Debug mode from environment (default: False for production)
    debug = os.environ.get("POWERTOOLS_DEBUG", "false").lower() in ("true", "1", "yes")

    app = Starlette(
        debug=debug,
        routes=[
            Route("/sse", handle_sse),
            Route("/messages", handle_messages, methods=["POST"]),
            Route("/health", health),
        ],
    )

    return app


async def run_server(
    host: str = "0.0.0.0", port: int = 8765, project_dir: Path | None = None
) -> None:
    """Run the MCP server."""
    app = create_app(project_dir)
    config = uvicorn.Config(app, host=host, port=port, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()


def main() -> None:
    """Entry point for running the MCP server."""
    # Get project directory from environment or use current directory
    project_dir_str = os.environ.get("POWERTOOLS_PROJECT_DIR")
    project_dir = Path(project_dir_str) if project_dir_str else None

    host = os.environ.get("POWERTOOLS_HOST", "0.0.0.0")
    port = int(os.environ.get("POWERTOOLS_PORT", "8765"))

    print(f"Starting powertools MCP server on {host}:{port}")
    if project_dir:
        print(f"Project directory: {project_dir}")

    asyncio.run(run_server(host, port, project_dir))


if __name__ == "__main__":
    main()
