"""Template loading utilities for powertools."""

from importlib.resources import files


def get_template(name: str) -> str:
    """Load a template file from the templates package.

    Args:
        name: Template filename (e.g., "compose.yaml")

    Returns:
        Template content as string.
    """
    return files("powertools.templates").joinpath(name).read_text()
