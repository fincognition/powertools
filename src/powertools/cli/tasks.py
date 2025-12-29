"""Task management CLI commands."""

import click
from rich.console import Console
from rich.table import Table

from powertools.core.tasks import TaskManager, TaskPriority, TaskStatus, TaskType

console = Console()


def get_task_manager() -> TaskManager:
    """Get task manager, creating project dir if needed."""
    return TaskManager()


def status_style(status: TaskStatus) -> str:
    """Get rich style for status."""
    return {
        TaskStatus.PENDING: "yellow",
        TaskStatus.IN_PROGRESS: "cyan",
        TaskStatus.BLOCKED: "red",
        TaskStatus.DONE: "green",
        TaskStatus.CANCELLED: "dim",
    }.get(status, "white")


def priority_display(priority: TaskPriority) -> str:
    """Get display string for priority."""
    return {
        TaskPriority.CRITICAL: "[red bold]P0[/]",
        TaskPriority.HIGH: "[yellow]P1[/]",
        TaskPriority.MEDIUM: "[white]P2[/]",
        TaskPriority.LOW: "[dim]P3[/]",
    }.get(priority, str(priority.value))


@click.group()
def task() -> None:
    """Manage tasks (Beads-style hierarchical task tracking)."""
    pass


@task.command()
@click.argument("title")
@click.option("--description", "-d", help="Task description")
@click.option(
    "--priority",
    "-p",
    type=click.Choice(["0", "1", "2", "3"]),
    default="2",
    help="Priority: 0=critical, 1=high, 2=medium, 3=low",
)
@click.option(
    "--type",
    "-t",
    "task_type",
    type=click.Choice(["epic", "task", "subtask", "bug"]),
    default="task",
    help="Task type",
)
@click.option("--parent", help="Parent task ID for hierarchical tasks")
@click.option("--blocks", multiple=True, help="Task IDs that this task blocks")
@click.option("--tag", multiple=True, help="Tags for the task")
@click.option("--context", "-c", help="Context for the task (what agent needs to know)")
def create(
    title: str,
    description: str | None,
    priority: str,
    task_type: str,
    parent: str | None,
    blocks: tuple[str, ...],
    tag: tuple[str, ...],
    context: str | None,
) -> None:
    """Create a new task."""
    try:
        tm = get_task_manager()
        task = tm.create(
            title=title,
            description=description,
            priority=TaskPriority(int(priority)),
            task_type=TaskType(task_type),
            parent=parent,
            blocks=list(blocks) if blocks else None,
            tags=list(tag) if tag else None,
            context=context,
        )
        console.print(f"[green]Created task:[/] [cyan]{task.id}[/]")
        console.print(f"  Title: {task.title}")
        console.print(f"  Priority: {priority_display(task.priority)}, Type: {task.type.value}")
        if parent:
            console.print(f"  Parent: {parent}")
        if blocks:
            console.print(f"  Blocks: {', '.join(blocks)}")
        if tag:
            console.print(f"  Tags: {', '.join(tag)}")
    except Exception as e:
        console.print(f"[red]Error creating task:[/] {e}")
        raise SystemExit(1) from None


@task.command()
@click.option("--limit", "-l", default=10, help="Maximum tasks to show")
def ready(limit: int) -> None:
    """List tasks that are ready to work on (no blockers)."""
    try:
        tm = get_task_manager()
        tasks = tm.get_ready_tasks(limit=limit)

        if not tasks:
            console.print("[dim]No ready tasks[/]")
            return

        table = Table(title="Ready Tasks (sorted by priority)")
        table.add_column("ID", style="cyan")
        table.add_column("P", justify="center")
        table.add_column("Title")
        table.add_column("Type", style="dim")
        table.add_column("Tags", style="dim")

        for t in tasks:
            table.add_row(
                t.id,
                priority_display(t.priority),
                t.title,
                t.type.value,
                ", ".join(t.tags) if t.tags else "",
            )

        console.print(table)
    except Exception as e:
        console.print(f"[red]Error:[/] {e}")
        raise SystemExit(1) from None


@task.command()
@click.argument("task_id")
def show(task_id: str) -> None:
    """Show details for a specific task."""
    try:
        tm = get_task_manager()
        t = tm.get(task_id)

        if not t:
            console.print(f"[red]Task not found:[/] {task_id}")
            raise SystemExit(1) from None

        console.print(f"[bold cyan]{t.id}[/] - {t.title}")
        console.print()
        console.print(f"  Status:   [{status_style(t.status)}]{t.status.value}[/]")
        console.print(f"  Priority: {priority_display(t.priority)}")
        console.print(f"  Type:     {t.type.value}")

        if t.description:
            console.print(f"\n  [bold]Description:[/]\n  {t.description}")

        if t.context:
            console.print(f"\n  [bold]Context:[/]\n  {t.context}")

        if t.parent:
            console.print(f"\n  Parent: [cyan]{t.parent}[/]")

        if t.blocked_by:
            console.print(f"\n  [red]Blocked by:[/] {', '.join(t.blocked_by)}")

        if t.blocks:
            console.print(f"\n  [yellow]Blocks:[/] {', '.join(t.blocks)}")

        if t.related:
            console.print(f"\n  Related: {', '.join(t.related)}")

        if t.tags:
            console.print(f"\n  Tags: {', '.join(t.tags)}")

        console.print(f"\n  Created: {t.created.isoformat()}")
        console.print(f"  Updated: {t.updated.isoformat()}")

    except SystemExit:
        raise
    except Exception as e:
        console.print(f"[red]Error:[/] {e}")
        raise SystemExit(1) from None


@task.command()
@click.argument("task_id")
@click.option(
    "--status",
    "-s",
    type=click.Choice(["pending", "in_progress", "blocked", "done", "cancelled"]),
    help="New status",
)
@click.option("--title", "-t", help="New title")
@click.option("--description", "-d", help="New description")
@click.option("--context", "-c", help="Context for the task (what agent needs to know)")
@click.option(
    "--priority",
    "-p",
    type=click.Choice(["0", "1", "2", "3"]),
    help="New priority",
)
def update(
    task_id: str,
    status: str | None,
    title: str | None,
    description: str | None,
    context: str | None,
    priority: str | None,
) -> None:
    """Update a task."""
    try:
        tm = get_task_manager()
        updated = tm.update(
            task_id,
            status=TaskStatus(status) if status else None,
            title=title,
            description=description,
            context=context,
            priority=TaskPriority(int(priority)) if priority else None,
        )

        if not updated:
            console.print(f"[red]Task not found:[/] {task_id}")
            raise SystemExit(1) from None

        console.print(f"[green]Updated task:[/] [cyan]{task_id}[/]")
        if status:
            console.print(f"  Status: [{status_style(updated.status)}]{status}[/]")
        if title:
            console.print(f"  Title: {title}")
        if priority:
            console.print(f"  Priority: {priority_display(updated.priority)}")

    except SystemExit:
        raise
    except Exception as e:
        console.print(f"[red]Error:[/] {e}")
        raise SystemExit(1) from None


@task.group()
def dep() -> None:
    """Manage task dependencies."""
    pass


@dep.command("add")
@click.argument("child_id")
@click.argument("parent_id")
def dep_add(child_id: str, parent_id: str) -> None:
    """Add a dependency (child is blocked by parent)."""
    try:
        tm = get_task_manager()
        if tm.add_dependency(child_id, parent_id):
            console.print(
                f"[green]Added dependency:[/] [cyan]{child_id}[/] is blocked by [cyan]{parent_id}[/]"
            )
        else:
            console.print("[red]Failed to add dependency. Check that both task IDs exist.[/]")
            raise SystemExit(1) from None
    except SystemExit:
        raise
    except Exception as e:
        console.print(f"[red]Error:[/] {e}")
        raise SystemExit(1) from None


@dep.command("rm")
@click.argument("child_id")
@click.argument("parent_id")
def dep_rm(child_id: str, parent_id: str) -> None:
    """Remove a dependency."""
    try:
        tm = get_task_manager()
        if tm.remove_dependency(child_id, parent_id):
            console.print(
                f"[green]Removed dependency:[/] [cyan]{child_id}[/] -> [cyan]{parent_id}[/]"
            )
        else:
            console.print("[red]Dependency not found or tasks don't exist.[/]")
            raise SystemExit(1) from None
    except SystemExit:
        raise
    except Exception as e:
        console.print(f"[red]Error:[/] {e}")
        raise SystemExit(1) from None


@task.command("list")
@click.option(
    "--status",
    "-s",
    type=click.Choice(["pending", "in_progress", "blocked", "done", "cancelled"]),
    help="Filter by status",
)
@click.option("--tag", "-t", help="Filter by tag")
@click.option(
    "--type",
    "task_type",
    type=click.Choice(["epic", "task", "subtask", "bug"]),
    help="Filter by type",
)
@click.option("--limit", "-l", default=20, help="Maximum tasks to show")
def list_tasks(
    status: str | None,
    tag: str | None,
    task_type: str | None,
    limit: int,
) -> None:
    """List tasks with optional filters."""
    try:
        tm = get_task_manager()
        tasks = tm.list_tasks(
            status=TaskStatus(status) if status else None,
            task_type=TaskType(task_type) if task_type else None,
            tag=tag,
            limit=limit,
        )

        if not tasks:
            console.print("[dim]No tasks found[/]")
            return

        table = Table(title="Tasks")
        table.add_column("ID", style="cyan")
        table.add_column("Status")
        table.add_column("P", justify="center")
        table.add_column("Title")
        table.add_column("Type", style="dim")

        for t in tasks:
            table.add_row(
                t.id,
                f"[{status_style(t.status)}]{t.status.value}[/]",
                priority_display(t.priority),
                t.title,
                t.type.value,
            )

        console.print(table)

    except Exception as e:
        console.print(f"[red]Error:[/] {e}")
        raise SystemExit(1) from None
