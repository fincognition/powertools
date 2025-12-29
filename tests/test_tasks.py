"""Tests for task management."""

import tempfile
from pathlib import Path

import pytest

from powertools.core.tasks import (
    TaskManager,
    TaskPriority,
    TaskStatus,
    TaskType,
)


@pytest.fixture
def temp_project_dir():
    """Create a temporary project directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir) / ".powertools"
        project_dir.mkdir()
        (project_dir / "tasks").mkdir()
        yield project_dir


@pytest.fixture
def task_manager(temp_project_dir):
    """Create a task manager with temporary storage."""
    return TaskManager(project_dir=temp_project_dir)


class TestTaskManager:
    def test_create_task(self, task_manager):
        """Test creating a basic task."""
        task = task_manager.create(title="Test task")

        assert task.id.startswith("pt-")
        assert task.title == "Test task"
        assert task.status == TaskStatus.PENDING
        assert task.priority == TaskPriority.MEDIUM
        assert task.type == TaskType.TASK

    def test_create_task_with_priority(self, task_manager):
        """Test creating a task with specific priority."""
        task = task_manager.create(
            title="Critical task",
            priority=TaskPriority.CRITICAL,
        )

        assert task.priority == TaskPriority.CRITICAL

    def test_get_task(self, task_manager):
        """Test retrieving a task by ID."""
        created = task_manager.create(title="Test task")
        retrieved = task_manager.get(created.id)

        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.title == created.title

    def test_get_nonexistent_task(self, task_manager):
        """Test getting a task that doesn't exist."""
        result = task_manager.get("pt-nonexistent")
        assert result is None

    def test_update_task_status(self, task_manager):
        """Test updating task status."""
        task = task_manager.create(title="Test task")
        updated = task_manager.update(task.id, status=TaskStatus.IN_PROGRESS)

        assert updated is not None
        assert updated.status == TaskStatus.IN_PROGRESS

    def test_update_task_title(self, task_manager):
        """Test updating task title."""
        task = task_manager.create(title="Original title")
        updated = task_manager.update(task.id, title="New title")

        assert updated is not None
        assert updated.title == "New title"

    def test_delete_task(self, task_manager):
        """Test deleting a task."""
        task = task_manager.create(title="Task to delete")
        result = task_manager.delete(task.id)

        assert result is True
        assert task_manager.get(task.id) is None

    def test_delete_nonexistent_task(self, task_manager):
        """Test deleting a task that doesn't exist."""
        result = task_manager.delete("pt-nonexistent")
        assert result is False

    def test_add_dependency(self, task_manager):
        """Test adding a dependency between tasks."""
        parent = task_manager.create(title="Parent task")
        child = task_manager.create(title="Child task")

        result = task_manager.add_dependency(child.id, parent.id)

        assert result is True

        # Verify the dependency was added
        updated_child = task_manager.get(child.id)
        updated_parent = task_manager.get(parent.id)

        assert parent.id in updated_child.blocked_by
        assert child.id in updated_parent.blocks

    def test_get_ready_tasks(self, task_manager):
        """Test getting tasks that are ready to work on."""
        # Create a high priority task
        high = task_manager.create(title="High priority", priority=TaskPriority.HIGH)
        # Create a low priority task
        low = task_manager.create(title="Low priority", priority=TaskPriority.LOW)
        # Create a blocked task
        blocker = task_manager.create(title="Blocker")
        blocked = task_manager.create(title="Blocked task")
        task_manager.add_dependency(blocked.id, blocker.id)

        ready = task_manager.get_ready_tasks()

        # Should include high, low, and blocker, but not blocked
        ready_ids = [t.id for t in ready]
        assert high.id in ready_ids
        assert low.id in ready_ids
        assert blocker.id in ready_ids
        assert blocked.id not in ready_ids

        # High priority should come first
        assert ready[0].id == high.id

    def test_list_tasks_filter_by_status(self, task_manager):
        """Test listing tasks filtered by status."""
        task1 = task_manager.create(title="Task 1")
        task2 = task_manager.create(title="Task 2")
        task_manager.update(task2.id, status=TaskStatus.DONE)

        pending = task_manager.list_tasks(status=TaskStatus.PENDING)
        done = task_manager.list_tasks(status=TaskStatus.DONE)

        assert len(pending) == 1
        assert pending[0].id == task1.id
        assert len(done) == 1
        assert done[0].id == task2.id

    def test_hierarchical_task_ids(self, task_manager):
        """Test that child tasks get hierarchical IDs."""
        parent = task_manager.create(title="Parent", task_type=TaskType.TASK)
        child = task_manager.create(title="Child", parent=parent.id, task_type=TaskType.SUBTASK)

        assert child.id.startswith(f"{parent.id}.")
        assert child.parent == parent.id
