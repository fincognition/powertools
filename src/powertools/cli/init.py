"""Initialization commands for powertools."""

import platform
import shutil
import subprocess
from pathlib import Path

import click
from rich.console import Console

from powertools.core import config
from powertools.embed import daemon
from powertools.templates import get_template

console = Console()


def _is_apple_silicon() -> bool:
    """Check if running on Apple Silicon Mac."""
    return platform.system() == "Darwin" and platform.machine() == "arm64"


def _detect_container_runtime() -> str | None:
    """Detect which container runtime is available."""
    runtimes = [
        ("docker", "docker"),
        ("podman", "podman"),
        ("orbstack", "docker"),  # OrbStack provides docker CLI
        ("colima", "docker"),  # Colima provides docker CLI
    ]

    for name, cli in runtimes:
        if shutil.which(cli):
            try:
                result = subprocess.run(
                    [cli, "info"],
                    capture_output=True,
                    timeout=5,
                )
                if result.returncode == 0:
                    return name
            except Exception:
                continue

    return None


def _get_host_address_for_runtime(runtime: str) -> str:
    """Get the host address that containers should use to reach the host."""
    mapping = {
        "docker": "host.docker.internal",
        "orbstack": "host.docker.internal",
        "podman": "host.containers.internal",
        "colima": "host.docker.internal",
    }
    return mapping.get(runtime, "host.docker.internal")


def _ensure_project_not_initialized(config_dir: Path) -> None:
    """Check if project is already initialized and prompt for reinitialize."""
    if config_dir.exists():
        console.print(f"[yellow]Project already initialized:[/] {config_dir}")
        if not click.confirm("Reinitialize?"):
            raise SystemExit(0)


def _create_project_config(name: str) -> tuple[Path, str]:
    """Create project configuration and return config directory and host address."""
    config_dir = config.get_project_config_dir()
    _ensure_project_not_initialized(config_dir)

    # Detect container runtime
    runtime = _detect_container_runtime()
    host_address = _get_host_address_for_runtime(runtime) if runtime else "host.docker.internal"

    # Create project config and directories
    config.save_project_config(name, container_runtime=runtime, host_address=host_address)

    console.print(f"[green]Created project config:[/] {config_dir}")
    return config_dir, host_address


def _create_compose_file(config_dir: Path, name: str, host_address: str) -> None:
    """Generate and write compose.yaml file."""
    compose_template = get_template("compose.yaml")
    compose_content = compose_template.format(project_name=name, host_address=host_address)
    compose_path = config_dir / "compose.yaml"
    compose_path.write_text(compose_content)
    console.print(f"[green]Created compose.yaml:[/] {compose_path}")


def _update_gitignore() -> None:
    """Add .powertools/ to .gitignore if not already present."""
    gitignore_path = Path.cwd() / ".gitignore"
    gitignore_entry = ".powertools/"

    if gitignore_path.exists():
        content = gitignore_path.read_text()
        if gitignore_entry not in content:
            with open(gitignore_path, "a") as f:
                f.write(f"\n# Powertools local data\n{gitignore_entry}\n")
            console.print(f"[green]Added to .gitignore:[/] {gitignore_entry}")
    else:
        with open(gitignore_path, "w") as f:
            f.write(f"# Powertools local data\n{gitignore_entry}\n")
        console.print(f"[green]Created .gitignore with:[/] {gitignore_entry}")


def _update_agents_md() -> None:
    """Append powertools section to AGENTS.md if it exists and doesn't already contain it."""
    agents_md_path = Path.cwd() / "AGENTS.md"

    if agents_md_path.exists():
        content = agents_md_path.read_text()
        if "powertools" not in content.lower():
            agents_section = get_template("agents_section.md")
            with open(agents_md_path, "a") as f:
                f.write(agents_section)
            console.print("[green]Appended powertools section to AGENTS.md[/]")
    else:
        console.print("[dim]No AGENTS.md found, skipping[/]")


def _print_project_init_next_steps() -> None:
    """Print next steps after project initialization."""
    console.print("\n[bold]Ready![/]")
    console.print("  Start services: [cyan]cd .powertools && docker compose up -d[/]")
    console.print("  Then use: [cyan]pt task create[/] or [cyan]pt memory add[/]")


def _check_platform() -> None:
    """Check if running on Apple Silicon, exit if not."""
    if not _is_apple_silicon():
        console.print("[red]Error: Powertools requires Apple Silicon Mac (M1/M2/M3/M4)[/red]")
        console.print(f"Detected: {platform.system()} {platform.machine()}")
        raise SystemExit(1)


def _create_user_config() -> Path:
    """Create user-level configuration directory and config file."""
    config_dir = config.get_user_config_dir()

    if config_dir.exists():
        console.print(f"[yellow]Config directory already exists:[/] {config_dir}")
        if not click.confirm("Overwrite existing configuration?"):
            raise SystemExit(0)

    config_dir.mkdir(parents=True, exist_ok=True)

    # Create default config
    cfg = config.Config()
    config.save_user_config(cfg)

    console.print(f"[green]Created config:[/] {config_dir / 'config.yaml'}")
    return config_dir


def _check_container_runtime() -> None:
    """Check and display container runtime status."""
    console.print("\n[bold]Checking container runtime...[/bold]")
    runtime = _detect_container_runtime()
    if runtime:
        console.print(f"  Found: [green]{runtime}[/green]")
    else:
        console.print("  [yellow]No container runtime found[/yellow]")
        console.print("  Install Docker Desktop, OrbStack, or Podman to use powertools")


def _install_embedding_daemon() -> None:
    """Prompt and install the embedding daemon."""
    console.print("\n[bold]Embedding Server[/bold]")
    console.print("Powertools uses a local embedding server for semantic memory search.")
    console.print("The server runs as a background daemon using MLX (Apple Silicon GPU).")

    install_daemon = click.confirm(
        "\nInstall embedding daemon? (recommended)",
        default=True,
    )

    if not install_daemon:
        console.print("\nSkipping daemon installation.")
        console.print("You can install later with: pt embed install")
        return

    console.print("\n[bold]Installing embedding daemon...[/bold]")
    success, message = daemon.install()

    if success:
        console.print(f"[green]{message}[/green]")

        console.print("Starting daemon...")
        start_success, start_msg = daemon.start()

        if start_success:
            console.print(f"[green]{start_msg}[/green]")
            console.print("\nEmbedding server available at http://localhost:8384")
        else:
            console.print(f"[yellow]{start_msg}[/yellow]")
            console.print("You can start it later with: pt embed start")
    else:
        console.print(f"[yellow]Warning: {message}[/yellow]")
        console.print("You can install later with: pt embed install")


def _print_init_next_steps() -> None:
    """Print next steps after initialization."""
    console.print("\n[bold]Next steps:[/bold]")
    console.print("  1. Run [cyan]pt project-init[/] in your project directory")
    console.print("  2. Start containers with [cyan]docker compose up -d[/]")


@click.command()
def init() -> None:
    """Initialize user-level powertools configuration (~/.powertools/)."""
    _check_platform()
    _create_user_config()
    _check_container_runtime()
    _install_embedding_daemon()
    _print_init_next_steps()


@click.command()
@click.option(
    "--name",
    "-n",
    prompt="Project name",
    help="Name for this project (used for Qdrant collection)",
)
def project_init(name: str) -> None:
    """Initialize powertools for the current project (.powertools/)."""
    config_dir, host_address = _create_project_config(name)
    _create_compose_file(config_dir, name, host_address)
    _update_gitignore()
    _update_agents_md()
    _print_project_init_next_steps()
