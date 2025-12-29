"""Task management operations."""

import secrets
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field

from powertools.core.config import get_project_config_dir
from powertools.storage.jsonl import JSONLStore


class TaskStatus(str, Enum):
    """Task status values."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    DONE = "done"
    CANCELLED = "cancelled"


class TaskType(str, Enum):
    """Task type values."""

    EPIC = "epic"
    TASK = "task"
    SUBTASK = "subtask"
    BUG = "bug"


class TaskPriority(int, Enum):
    """Task priority values (lower = higher priority)."""

    CRITICAL = 0
    HIGH = 1
    MEDIUM = 2
    LOW = 3


class Task(BaseModel):
    """A task in the task graph."""

    id: str
    title: str
    description: str | None = None
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.MEDIUM
    type: TaskType = TaskType.TASK
    parent: str | None = None
    blocks: list[str] = Field(default_factory=list)
    blocked_by: list[str] = Field(default_factory=list)
    related: list[str] = Field(default_factory=list)
    context: str | None = None
    tags: list[str] = Field(default_factory=list)
    created: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated: datetime = Field(default_factory=lambda: datetime.now(UTC))


def generate_task_id() -> str:
    """Generate a hash-based task ID for root tasks.

    Returns a root ID like pt-a1b2.
    For child tasks, TaskManager.create() handles hierarchical IDs (pt-a1b2.1, pt-a1b2.2, etc.)
    """
    # Generate 4 random hex chars
    random_suffix = secrets.token_hex(2)
    return f"pt-{random_suffix}"


class TaskManager:
    """Manages task operations."""

    def __init__(self, project_dir: Path | None = None) -> None:
        self.project_dir = project_dir if project_dir is not None else get_project_config_dir()
        tasks_file = self.project_dir / "tasks" / "tasks.jsonl"
        self.store = JSONLStore(tasks_file, Task)
        self._task_cache: dict[str, Task] | None = None

    def _invalidate_cache(self) -> None:
        """Invalidate the task cache."""
        self._task_cache = None

    def _get_all_tasks(self) -> dict[str, Task]:
        """Get all tasks as a dict keyed by ID."""
        if self._task_cache is None:
            self._task_cache = {t.id: t for t in self.store.list_all()}
        return self._task_cache

    def _next_child_number(self, parent_id: str) -> int:
        """Get the next available child number for a parent task."""
        tasks = self._get_all_tasks()
        prefix = f"{parent_id}."
        max_num = 0
        for task_id in tasks:
            if task_id.startswith(prefix):
                # Extract the child number (e.g., "pt-a1b2.3" -> 3)
                suffix = task_id[len(prefix) :]
                # Handle nested children by only looking at immediate children
                if "." not in suffix:
                    try:
                        num = int(suffix)
                        max_num = max(max_num, num)
                    except ValueError:
                        pass
        return max_num + 1

    def create(
        self,
        title: str,
        description: str | None = None,
        priority: TaskPriority = TaskPriority.MEDIUM,
        task_type: TaskType = TaskType.TASK,
        parent: str | None = None,
        blocks: list[str] | None = None,
        tags: list[str] | None = None,
        context: str | None = None,
    ) -> Task:
        """Create a new task.

        ID Structure:
        - EPIC, TASK, BUG: Root-level IDs like pt-a1b2 (no parent allowed)
        - SUBTASK: Hierarchical IDs like pt-a1b2.1, pt-a1b2.2 (requires parent)

        Dependencies:
        - Epic -> Task relationships use blocks/blocked_by (not parent-child)
        - Parent-child is only for breaking tasks into subtasks
        """
        # Validate: Only subtasks can have parents
        if parent and task_type != TaskType.SUBTASK:
            raise ValueError(
                f"Only subtasks can have a parent. {task_type.value} tasks must be root-level. "
                "Use dependencies (blocks/blocked_by) to relate epics to tasks."
            )

        # Validate: Subtasks must have a parent
        if task_type == TaskType.SUBTASK and not parent:
            raise ValueError("Subtasks must have a parent task.")

        # Generate ID based on task type
        tasks = self._get_all_tasks()

        if parent:
            # Only subtasks get hierarchical IDs (pt-a1b2.1, pt-a1b2.2, etc.)
            child_num = self._next_child_number(parent)
            task_id = f"{parent}.{child_num}"
            # Hierarchical IDs shouldn't collide (next_child_number finds max), but handle edge case
            # If collision occurs, increment until we find an available number
            while task_id in tasks:
                child_num += 1
                task_id = f"{parent}.{child_num}"
        else:
            # EPIC, TASK, BUG get root-level IDs (pt-a1b2, pt-c3d4, etc.)
            task_id = generate_task_id()
            # Handle rare collisions for root IDs
            while task_id in tasks:
                task_id = generate_task_id()

        now = datetime.now(UTC)
        task = Task(
            id=task_id,
            title=title,
            description=description,
            priority=priority,
            type=task_type,
            parent=parent,
            blocks=blocks or [],
            tags=tags or [],
            context=context,
            created=now,
            updated=now,
        )

        # Update blocked_by for tasks that this task blocks
        if blocks:
            for blocked_id in blocks:
                blocked_task = tasks.get(blocked_id)
                if blocked_task and task_id not in blocked_task.blocked_by:
                    blocked_task.blocked_by.append(task_id)
                    blocked_task.updated = now
                    self.store.update(blocked_id, blocked_task)

        self.store.append(task)
        self._invalidate_cache()
        return task

    def get(self, task_id: str) -> Task | None:
        """Get a task by ID."""
        return self._get_all_tasks().get(task_id)

    def update(
        self,
        task_id: str,
        status: TaskStatus | None = None,
        title: str | None = None,
        description: str | None = None,
        context: str | None = None,
        priority: TaskPriority | None = None,
    ) -> Task | None:
        """Update a task. Returns updated task or None if not found."""
        task = self.get(task_id)
        if not task:
            return None

        if status is not None:
            task.status = status
        if title is not None:
            task.title = title
        if description is not None:
            task.description = description
        if context is not None:
            task.context = context
        if priority is not None:
            task.priority = priority

        task.updated = datetime.now(UTC)
        self.store.update(task_id, task)
        self._invalidate_cache()
        return task

    def delete(self, task_id: str) -> bool:
        """Delete a task. Returns True if deleted."""
        result = self.store.delete(task_id)
        if result:
            self._invalidate_cache()
        return result

    def add_dependency(self, child_id: str, parent_id: str) -> bool:
        """Add a dependency: child is blocked by parent.

        Returns True if dependency was added.
        """
        tasks = self._get_all_tasks()
        child = tasks.get(child_id)
        parent = tasks.get(parent_id)

        if not child or not parent:
            return False

        now = datetime.now(UTC)
        modified = False

        if parent_id not in child.blocked_by:
            child.blocked_by.append(parent_id)
            child.updated = now
            self.store.update(child_id, child)
            modified = True

        if child_id not in parent.blocks:
            parent.blocks.append(child_id)
            parent.updated = now
            self.store.update(parent_id, parent)
            modified = True

        if modified:
            self._invalidate_cache()

        return modified

    def remove_dependency(self, child_id: str, parent_id: str) -> bool:
        """Remove a dependency.

        Returns True if dependency was removed.
        """
        tasks = self._get_all_tasks()
        child = tasks.get(child_id)
        parent = tasks.get(parent_id)

        if not child or not parent:
            return False

        now = datetime.now(UTC)
        modified = False

        if parent_id in child.blocked_by:
            child.blocked_by.remove(parent_id)
            child.updated = now
            self.store.update(child_id, child)
            modified = True

        if child_id in parent.blocks:
            parent.blocks.remove(child_id)
            parent.updated = now
            self.store.update(parent_id, parent)
            modified = True

        if modified:
            self._invalidate_cache()

        return modified

    def get_ready_tasks(self, limit: int = 10) -> list[Task]:
        """Get tasks that are ready to work on (pending, no open blockers).

        Returns tasks sorted by priority (lowest number = highest priority).
        """
        tasks = self._get_all_tasks()
        ready: list[Task] = []

        for task in tasks.values():
            if task.status != TaskStatus.PENDING:
                continue

            # Check if all blockers are done
            all_blockers_done = True
            for blocker_id in task.blocked_by:
                blocker = tasks.get(blocker_id)
                if blocker and blocker.status not in (TaskStatus.DONE, TaskStatus.CANCELLED):
                    all_blockers_done = False
                    break

            if all_blockers_done:
                ready.append(task)

        # Sort by priority (lower = higher priority), then by created date
        ready.sort(key=lambda t: (t.priority.value, t.created))
        return ready[:limit]

    def list_tasks(
        self,
        status: TaskStatus | None = None,
        task_type: TaskType | None = None,
        tag: str | None = None,
        limit: int = 50,
    ) -> list[Task]:
        """List tasks with optional filters."""
        tasks = list(self._get_all_tasks().values())

        if status:
            tasks = [t for t in tasks if t.status == status]
        if task_type:
            tasks = [t for t in tasks if t.type == task_type]
        if tag:
            tasks = [t for t in tasks if tag in t.tags]

        # Sort by priority, then updated (most recent first)
        tasks.sort(key=lambda t: (t.priority.value, -t.updated.timestamp()))
        return tasks[:limit]
