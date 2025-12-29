"""Memory management CLI commands."""

import click
from rich.console import Console
from rich.table import Table

from powertools.core.memory import MemoryCategory, MemoryManager

console = Console()


def get_memory_manager() -> MemoryManager:
    """Get memory manager instance."""
    return MemoryManager()


@click.group()
def memory() -> None:
    """Manage project memory (facts, decisions, patterns)."""
    pass


@memory.command()
@click.argument("content")
@click.option("--source", "-s", help="Source of this fact (e.g., file:line)")
@click.option(
    "--category",
    "-c",
    type=click.Choice(["architecture", "decision", "pattern", "dependency", "convention", "fact"]),
    default="fact",
    help="Category of the memory",
)
@click.option(
    "--confidence",
    type=float,
    default=1.0,
    help="Confidence score (0.0-1.0)",
)
def add(content: str, source: str | None, category: str, confidence: float) -> None:
    """Add a fact to project memory."""
    try:
        mm = get_memory_manager()
        mem = mm.add(
            content=content,
            source=source,
            category=MemoryCategory(category),
            confidence=confidence,
        )
        console.print(f"[green]Added memory:[/] [cyan]{mem.id}[/]")
        console.print(f"  Content: {content[:60]}{'...' if len(content) > 60 else ''}")
        console.print(f"  Category: {category}")
        if source:
            console.print(f"  Source: {source}")
    except Exception as e:
        console.print(f"[red]Error adding memory:[/] {e}")
        console.print("[dim]Is the embedding server running? Try 'pt status'[/]")
        raise SystemExit(1) from None


@memory.command()
@click.argument("query")
@click.option("--limit", "-l", default=10, help="Maximum results to return")
@click.option(
    "--category",
    "-c",
    type=click.Choice(["architecture", "decision", "pattern", "dependency", "convention", "fact"]),
    help="Filter by category",
)
def search(query: str, limit: int, category: str | None) -> None:
    """Search project memory semantically."""
    try:
        mm = get_memory_manager()
        results = mm.search(
            query=query,
            limit=limit,
            category=MemoryCategory(category) if category else None,
        )

        if not results:
            console.print("[dim]No results found[/]")
            return

        table = Table(title=f"Search Results for: {query}")
        table.add_column("ID", style="cyan")
        table.add_column("Score", justify="right", style="yellow")
        table.add_column("Category", style="green")
        table.add_column("Content")
        table.add_column("Source", style="dim")

        for r in results:
            table.add_row(
                r["id"],
                f"{r['score']:.3f}",
                r["category"],
                r["content"][:50] + "..." if len(r["content"]) > 50 else r["content"],
                r["source"] or "",
            )

        console.print(table)

    except Exception as e:
        console.print(f"[red]Error searching:[/] {e}")
        console.print("[dim]Is the embedding server running? Try 'pt status'[/]")
        raise SystemExit(1) from None


@memory.command("list")
@click.option(
    "--category",
    "-c",
    type=click.Choice(["architecture", "decision", "pattern", "dependency", "convention", "fact"]),
    help="Filter by category",
)
@click.option("--limit", "-l", default=20, help="Maximum results to return")
def list_memories(category: str | None, limit: int) -> None:
    """List memories, optionally filtered by category."""
    try:
        mm = get_memory_manager()
        memories = mm.list_all(
            category=MemoryCategory(category) if category else None,
            limit=limit,
        )

        if not memories:
            console.print("[dim]No memories found[/]")
            return

        table = Table(title="Memories")
        table.add_column("ID", style="cyan")
        table.add_column("Category", style="green")
        table.add_column("Content")
        table.add_column("Source", style="dim")

        for m in memories:
            table.add_row(
                m.id,
                m.category.value,
                m.content[:50] + "..." if len(m.content) > 50 else m.content,
                m.source or "",
            )

        console.print(table)

    except Exception as e:
        console.print(f"[red]Error listing memories:[/] {e}")
        raise SystemExit(1) from None


@memory.command()
@click.argument("memory_id")
def show(memory_id: str) -> None:
    """Show details of a specific memory."""
    try:
        mm = get_memory_manager()
        mem = mm.get(memory_id)

        if not mem:
            console.print(f"[red]Memory not found:[/] {memory_id}")
            raise SystemExit(1) from None

        console.print(f"[bold cyan]{mem.id}[/]")
        console.print()
        console.print(f"  Category:   [green]{mem.category.value}[/]")
        console.print(f"  Confidence: {mem.confidence:.2f}")
        if mem.source:
            console.print(f"  Source:     {mem.source}")
        console.print(f"  Created:    {mem.created.isoformat()}")
        console.print()
        console.print("  [bold]Content:[/]")
        console.print(f"  {mem.content}")

    except SystemExit:
        raise
    except Exception as e:
        console.print(f"[red]Error:[/] {e}")
        raise SystemExit(1) from None


@memory.command()
@click.argument("memory_id")
@click.confirmation_option(prompt="Are you sure you want to delete this memory?")
def delete(memory_id: str) -> None:
    """Delete a memory by ID."""
    try:
        mm = get_memory_manager()
        if mm.delete(memory_id):
            console.print(f"[green]Deleted memory:[/] {memory_id}")
        else:
            console.print(f"[red]Memory not found:[/] {memory_id}")
            raise SystemExit(1) from None
    except SystemExit:
        raise
    except Exception as e:
        console.print(f"[red]Error deleting memory:[/] {e}")
        raise SystemExit(1) from None
