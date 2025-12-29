"""Main CLI entry point for powertools."""

import click

from powertools import __version__


@click.group()
@click.version_option(version=__version__, prog_name="powertools")
def cli() -> None:
    """Powertools - Agentic workflow toolkit with persistent memory and task tracking."""
    pass


# Subcommands are registered via entry points or imported after definition
# to avoid circular imports. See __init__.py for registration.
