"""MCP tools for memory management."""

from mcp.server import Server
from mcp.types import TextContent, Tool

from powertools.core.memory import MemoryCategory, MemoryManager


def register_memory_tools(server: Server, memory_manager: MemoryManager) -> None:
    """Register memory management tools with the MCP server."""

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name="add_memory",
                description="Add a fact or piece of knowledge to project memory",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "content": {
                            "type": "string",
                            "description": "The fact or knowledge to store",
                        },
                        "source": {
                            "type": "string",
                            "description": "Source reference (e.g., file:line, URL, 'user')",
                        },
                        "category": {
                            "type": "string",
                            "enum": [
                                "architecture",
                                "decision",
                                "pattern",
                                "dependency",
                                "convention",
                                "fact",
                            ],
                            "description": "Category of the memory",
                            "default": "fact",
                        },
                        "confidence": {
                            "type": "number",
                            "minimum": 0.0,
                            "maximum": 1.0,
                            "description": "Confidence score (0.0-1.0)",
                            "default": 1.0,
                        },
                    },
                    "required": ["content"],
                },
            ),
            Tool(
                name="search_memory",
                description="Search project memory semantically to find relevant facts and knowledge",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum results to return",
                            "default": 10,
                        },
                        "category": {
                            "type": "string",
                            "enum": [
                                "architecture",
                                "decision",
                                "pattern",
                                "dependency",
                                "convention",
                                "fact",
                            ],
                            "description": "Filter by category",
                        },
                    },
                    "required": ["query"],
                },
            ),
            Tool(
                name="list_memories",
                description="List all memories in project memory, optionally filtered by category",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "category": {
                            "type": "string",
                            "enum": [
                                "architecture",
                                "decision",
                                "pattern",
                                "dependency",
                                "convention",
                                "fact",
                            ],
                            "description": "Filter by category",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum results to return",
                            "default": 20,
                        },
                    },
                },
            ),
            Tool(
                name="delete_memory",
                description="Delete a memory by ID",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "id": {
                            "type": "string",
                            "description": "Memory ID to delete",
                        },
                    },
                    "required": ["id"],
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        try:
            if name == "add_memory":
                try:
                    category = MemoryCategory(arguments.get("category", "fact"))
                    confidence = arguments.get("confidence", 1.0)
                    if not 0.0 <= confidence <= 1.0:
                        return [
                            TextContent(
                                type="text",
                                text="Confidence must be between 0.0 and 1.0",
                            )
                        ]
                except ValueError as e:
                    return [TextContent(type="text", text=f"Invalid category: {e}")]

                mem = memory_manager.add(
                    content=arguments["content"],
                    source=arguments.get("source"),
                    category=category,
                    confidence=confidence,
                )
                return [
                    TextContent(
                        type="text",
                        text=f"Added memory {mem.id}: {mem.content[:50]}...",
                    )
                ]

            elif name == "search_memory":
                try:
                    category = (
                        MemoryCategory(arguments["category"]) if arguments.get("category") else None
                    )
                except ValueError as e:
                    return [TextContent(type="text", text=f"Invalid category: {e}")]

                results = memory_manager.search(
                    query=arguments["query"],
                    limit=arguments.get("limit", 10),
                    category=category,
                )

                if not results:
                    return [TextContent(type="text", text="No results found")]

                lines = [f"Search results for: {arguments['query']}"]
                for r in results:
                    lines.append(
                        f"- [{r['id']}] (score: {r['score']:.3f}) {r['category']}: {r['content'][:60]}..."
                    )
                return [TextContent(type="text", text="\n".join(lines))]

            elif name == "list_memories":
                try:
                    category = (
                        MemoryCategory(arguments["category"]) if arguments.get("category") else None
                    )
                except ValueError as e:
                    return [TextContent(type="text", text=f"Invalid category: {e}")]

                memories = memory_manager.list_all(
                    category=category,
                    limit=arguments.get("limit", 20),
                )

                if not memories:
                    return [TextContent(type="text", text="No memories found")]

                lines = ["Memories:"]
                for m in memories:
                    lines.append(f"- [{m.id}] {m.category.value}: {m.content[:60]}...")
                return [TextContent(type="text", text="\n".join(lines))]

            elif name == "delete_memory":
                if memory_manager.delete(arguments["id"]):
                    return [TextContent(type="text", text=f"Deleted memory {arguments['id']}")]
                return [TextContent(type="text", text=f"Memory not found: {arguments['id']}")]

            else:
                return [TextContent(type="text", text=f"Unknown tool: {name}")]

        except KeyError as e:
            return [TextContent(type="text", text=f"Missing required argument: {e}")]
        except ValueError as e:
            return [TextContent(type="text", text=f"Invalid argument value: {e}")]
        except Exception as e:
            return [TextContent(type="text", text=f"Unexpected error: {type(e).__name__}: {e}")]
