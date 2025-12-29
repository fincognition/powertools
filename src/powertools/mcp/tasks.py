"""MCP tools for task management."""

from typing import Any

from mcp.server import Server
from mcp.types import TextContent, Tool

from powertools.core.tasks import TaskManager, TaskPriority, TaskStatus, TaskType


def register_task_tools(server: Server, task_manager: TaskManager) -> None:
    """Register task management tools with the MCP server."""

    @server.list_tools()  # type: ignore[untyped-decorator,no-untyped-call]
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name="create_task",
                description="Create a new task in the task tracking system",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "Title of the task",
                        },
                        "description": {
                            "type": "string",
                            "description": "Detailed description of the task",
                        },
                        "priority": {
                            "type": "integer",
                            "enum": [0, 1, 2, 3],
                            "description": "Priority: 0=critical, 1=high, 2=medium, 3=low",
                            "default": 2,
                        },
                        "type": {
                            "type": "string",
                            "enum": ["epic", "task", "subtask", "bug"],
                            "description": "Type of task",
                            "default": "task",
                        },
                        "parent": {
                            "type": "string",
                            "description": "Parent task ID for hierarchical tasks",
                        },
                        "blocks": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Task IDs that this task blocks",
                        },
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Tags for categorization",
                        },
                        "context": {
                            "type": "string",
                            "description": "Context information for executing this task",
                        },
                    },
                    "required": ["title"],
                },
            ),
            Tool(
                name="get_ready_tasks",
                description="Get tasks that are ready to work on (pending with no open blockers), sorted by priority",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of tasks to return",
                            "default": 10,
                        },
                    },
                },
            ),
            Tool(
                name="get_task",
                description="Get details of a specific task by ID",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "id": {
                            "type": "string",
                            "description": "Task ID (e.g., pt-a1b2 or pt-a1b2.1)",
                        },
                    },
                    "required": ["id"],
                },
            ),
            Tool(
                name="update_task",
                description="Update a task's status, title, description, context, or priority",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "id": {
                            "type": "string",
                            "description": "Task ID to update",
                        },
                        "status": {
                            "type": "string",
                            "enum": ["pending", "in_progress", "blocked", "done", "cancelled"],
                            "description": "New status",
                        },
                        "title": {
                            "type": "string",
                            "description": "New title",
                        },
                        "description": {
                            "type": "string",
                            "description": "New description",
                        },
                        "context": {
                            "type": "string",
                            "description": "New context information",
                        },
                        "priority": {
                            "type": "integer",
                            "enum": [0, 1, 2, 3],
                            "description": "New priority",
                        },
                    },
                    "required": ["id"],
                },
            ),
            Tool(
                name="add_dependency",
                description="Add a dependency between tasks (child is blocked by parent)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "child_id": {
                            "type": "string",
                            "description": "ID of the task that will be blocked",
                        },
                        "parent_id": {
                            "type": "string",
                            "description": "ID of the blocking task",
                        },
                    },
                    "required": ["child_id", "parent_id"],
                },
            ),
            Tool(
                name="remove_dependency",
                description="Remove a dependency between tasks",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "child_id": {
                            "type": "string",
                            "description": "ID of the blocked task",
                        },
                        "parent_id": {
                            "type": "string",
                            "description": "ID of the blocking task",
                        },
                    },
                    "required": ["child_id", "parent_id"],
                },
            ),
            Tool(
                name="list_tasks",
                description="List tasks with optional filters",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "status": {
                            "type": "string",
                            "enum": ["pending", "in_progress", "blocked", "done", "cancelled"],
                            "description": "Filter by status",
                        },
                        "type": {
                            "type": "string",
                            "enum": ["epic", "task", "subtask", "bug"],
                            "description": "Filter by type",
                        },
                        "tag": {
                            "type": "string",
                            "description": "Filter by tag",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum tasks to return",
                            "default": 20,
                        },
                    },
                },
            ),
        ]

    @server.call_tool()  # type: ignore[untyped-decorator]
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
        try:
            if name == "create_task":
                try:
                    task = task_manager.create(
                        title=arguments["title"],
                        description=arguments.get("description"),
                        priority=TaskPriority(arguments.get("priority", 2)),
                        task_type=TaskType(arguments.get("type", "task")),
                        parent=arguments.get("parent"),
                        blocks=arguments.get("blocks"),
                        tags=arguments.get("tags"),
                        context=arguments.get("context"),
                    )
                    return [
                        TextContent(
                            type="text",
                            text=f"Created task {task.id}: {task.title}",
                        )
                    ]
                except ValueError as e:
                    return [TextContent(type="text", text=f"Validation error: {e}")]

            elif name == "get_ready_tasks":
                limit = arguments.get("limit", 10)
                tasks = task_manager.get_ready_tasks(limit=limit)
                if not tasks:
                    return [TextContent(type="text", text="No ready tasks")]

                lines = ["Ready tasks (sorted by priority):"]
                for t in tasks:
                    lines.append(f"- [{t.id}] P{t.priority.value} {t.title} ({t.type.value})")
                return [TextContent(type="text", text="\n".join(lines))]

            elif name == "get_task":
                task = task_manager.get(arguments["id"])  # type: ignore[assignment]
                if task is None:
                    return [TextContent(type="text", text=f"Task not found: {arguments['id']}")]

                # mypy doesn't narrow the type after the None check
                # task is guaranteed to be non-None after the check above
                task_obj = task
                lines = [
                    f"Task: {task_obj.id}",
                    f"Title: {task_obj.title}",
                    f"Status: {task_obj.status.value}",
                    f"Priority: P{task_obj.priority.value}",
                    f"Type: {task_obj.type.value}",
                ]
                if task_obj.description:
                    lines.append(f"Description: {task_obj.description}")
                if task_obj.context:
                    lines.append(f"Context: {task_obj.context}")
                if task_obj.parent:
                    lines.append(f"Parent: {task_obj.parent}")
                if task_obj.blocked_by:
                    lines.append(f"Blocked by: {', '.join(task_obj.blocked_by)}")
                if task_obj.blocks:
                    lines.append(f"Blocks: {', '.join(task_obj.blocks)}")
                if task_obj.tags:
                    lines.append(f"Tags: {', '.join(task_obj.tags)}")

                return [TextContent(type="text", text="\n".join(lines))]

            elif name == "update_task":
                try:
                    status = TaskStatus(arguments["status"]) if arguments.get("status") else None
                    priority = (
                        TaskPriority(arguments["priority"])
                        if arguments.get("priority") is not None
                        else None
                    )
                except ValueError as e:
                    return [TextContent(type="text", text=f"Invalid status or priority: {e}")]

                updated = task_manager.update(
                    arguments["id"],
                    status=status,
                    title=arguments.get("title"),
                    description=arguments.get("description"),
                    context=arguments.get("context"),
                    priority=priority,
                )
                if not updated:
                    return [TextContent(type="text", text=f"Task not found: {arguments['id']}")]
                return [TextContent(type="text", text=f"Updated task {updated.id}")]

            elif name == "add_dependency":
                if task_manager.add_dependency(arguments["child_id"], arguments["parent_id"]):
                    return [
                        TextContent(
                            type="text",
                            text=f"Added dependency: {arguments['child_id']} is blocked by {arguments['parent_id']}",
                        )
                    ]
                return [
                    TextContent(type="text", text="Failed to add dependency. Check task IDs exist.")
                ]

            elif name == "remove_dependency":
                if task_manager.remove_dependency(arguments["child_id"], arguments["parent_id"]):
                    return [
                        TextContent(
                            type="text",
                            text=f"Removed dependency: {arguments['child_id']} -> {arguments['parent_id']}",
                        )
                    ]
                return [TextContent(type="text", text="Dependency not found or tasks don't exist.")]

            elif name == "list_tasks":
                try:
                    status = TaskStatus(arguments["status"]) if arguments.get("status") else None
                    task_type = TaskType(arguments["type"]) if arguments.get("type") else None
                except ValueError as e:
                    return [TextContent(type="text", text=f"Invalid status or type: {e}")]

                tasks = task_manager.list_tasks(
                    status=status,
                    task_type=task_type,
                    tag=arguments.get("tag"),
                    limit=arguments.get("limit", 20),
                )
                if not tasks:
                    return [TextContent(type="text", text="No tasks found")]

                lines = ["Tasks:"]
                for t in tasks:
                    lines.append(f"- [{t.id}] {t.status.value} P{t.priority.value} {t.title}")
                return [TextContent(type="text", text="\n".join(lines))]

            else:
                return [TextContent(type="text", text=f"Unknown tool: {name}")]

        except KeyError as e:
            return [TextContent(type="text", text=f"Missing required argument: {e}")]
        except ValueError as e:
            return [TextContent(type="text", text=f"Invalid argument value: {e}")]
        except Exception as e:
            return [TextContent(type="text", text=f"Unexpected error: {type(e).__name__}: {e}")]
