"""CLI commands for powertools."""

from powertools.cli.embed import embed
from powertools.cli.init import init, project_init
from powertools.cli.main import cli
from powertools.cli.memory import memory
from powertools.cli.tasks import task

# Register all commands
cli.add_command(init)
cli.add_command(project_init, name="project-init")
cli.add_command(memory)
cli.add_command(task)
cli.add_command(embed)

__all__ = ["cli"]
