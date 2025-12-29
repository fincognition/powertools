"""CLI commands for embedding daemon management."""

import sys

import click
import httpx
from rich.console import Console

from powertools.embed import daemon, server

console = Console()


@click.group()
def embed() -> None:
    """Manage the embedding server daemon."""
    pass


@embed.command()
@click.option("--host", default="127.0.0.1", help="Host to bind to")
@click.option("--port", default=8384, type=int, help="Port to bind to")
@click.option("--model", default=None, help="Model to use (default: Qwen3-Embedding-0.6B-4bit)")
def install(host: str, port: int, model: str | None) -> None:
    """Install the embedding daemon (launchd)."""
    console.print("[bold]Installing powertools-embed daemon...[/bold]")

    success, message = daemon.install(host=host, port=port, model=model)

    if success:
        console.print(f"[green]{message}[/green]")

        # Also start the daemon
        console.print("Starting daemon...")
        start_success, start_msg = daemon.start()

        if start_success:
            console.print(f"[green]{start_msg}[/green]")
            console.print(f"\nEmbedding server available at http://{host}:{port}")
            console.print("Test with: curl http://localhost:8384/health")
        else:
            console.print(f"[yellow]{start_msg}[/yellow]")
            console.print("You can start it manually with: pt embed start")
    else:
        console.print(f"[red]Error: {message}[/red]")
        raise SystemExit(1)


@embed.command()
def uninstall() -> None:
    """Uninstall the embedding daemon."""
    console.print("[bold]Uninstalling powertools-embed daemon...[/bold]")

    success, message = daemon.uninstall()

    if success:
        console.print(f"[green]{message}[/green]")
    else:
        console.print(f"[red]Error: {message}[/red]")
        raise SystemExit(1)


@embed.command()
def start() -> None:
    """Start the embedding daemon."""
    success, message = daemon.start()

    if success:
        console.print(f"[green]{message}[/green]")
    else:
        console.print(f"[red]Error: {message}[/red]")
        raise SystemExit(1)


@embed.command()
def stop() -> None:
    """Stop the embedding daemon."""
    success, message = daemon.stop()

    if success:
        console.print(f"[green]{message}[/green]")
    else:
        console.print(f"[red]Error: {message}[/red]")
        raise SystemExit(1)


@embed.command()
def restart() -> None:
    """Restart the embedding daemon."""
    success, message = daemon.restart()

    if success:
        console.print(f"[green]{message}[/green]")
    else:
        console.print(f"[red]Error: {message}[/red]")
        raise SystemExit(1)


@embed.command()
def status() -> None:
    """Show embedding daemon status."""
    status_info = daemon.get_status()

    console.print("[bold]Embedding Daemon Status[/bold]\n")

    # Installation status
    if status_info["installed"]:
        console.print("  Installed: [green]yes[/green]")
        console.print(f"  Plist: {status_info['plist_path']}")
    else:
        console.print("  Installed: [yellow]no[/yellow]")
        console.print("  Run 'pt embed install' to install the daemon")
        return

    # Running status
    if status_info["running"]:
        console.print("  Running: [green]yes[/green]")
        console.print(f"  PID: {status_info['pid']}")
    else:
        console.print("  Running: [red]no[/red]")
        if status_info["exit_code"] is not None:
            console.print(f"  Last exit code: {status_info['exit_code']}")
        console.print("  Run 'pt embed start' to start the daemon")
        return

    # Check HTTP health
    console.print("\n[bold]Health Check[/bold]")
    try:
        response = httpx.get("http://localhost:8384/health", timeout=5.0)
        if response.status_code == 200:
            data = response.json()
            console.print("  Status: [green]healthy[/green]")
            console.print(f"  Model: {data.get('model', 'unknown')}")
            console.print(f"  Loaded: {data.get('loaded', False)}")
        else:
            console.print(f"  Status: [yellow]unhealthy (HTTP {response.status_code})[/yellow]")
    except httpx.ConnectError:
        console.print("  Status: [yellow]not responding (connection refused)[/yellow]")
        console.print("  The daemon may still be starting up...")
    except Exception as e:
        console.print(f"  Status: [red]error ({e})[/red]")


@embed.command()
@click.option("--lines", "-n", default=50, help="Number of lines to show")
@click.option("--stderr", "-e", is_flag=True, help="Show stderr instead of stdout")
def logs(lines: int, stderr: bool):
    """Show daemon logs."""
    stdout_logs, stderr_logs = daemon.get_logs(lines=lines)

    if stderr:
        if stderr_logs:
            console.print(stderr_logs)
        else:
            console.print("[dim]No stderr logs available[/dim]")
    else:
        if stdout_logs:
            console.print(stdout_logs)
        else:
            console.print("[dim]No stdout logs available[/dim]")


@embed.command()
@click.option("--host", default="127.0.0.1", help="Host to bind to")
@click.option("--port", default=8384, type=int, help="Port to bind to")
@click.option("--model", default=None, help="Model to use")
def serve(host: str, port: int, model: str | None) -> None:
    """Run embedding server in foreground (for testing)."""
    # Build args for the server
    sys.argv = ["powertools-embed", "--host", host, "--port", str(port)]
    if model:
        sys.argv.extend(["--model", model])

    # Run the server
    server.main()  # type: ignore[no-untyped-call]
