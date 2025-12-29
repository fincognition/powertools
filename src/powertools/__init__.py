"""Powertools - Agentic workflow toolkit with persistent memory and task tracking."""

import tomllib
from importlib.metadata import version as get_version
from pathlib import Path

# Note: __package__ is "powertools" (Python package name)
# but we need "powertools-ai" (PyPI package name) to get version from installed metadata
try:
    __version__ = get_version("powertools-ai")
except Exception:
    # Fallback for editable installs or when package not installed
    pyproject_path = Path(__file__).parent.parent.parent.parent / "pyproject.toml"
    if pyproject_path.exists():
        with open(pyproject_path, "rb") as f:
            data = tomllib.load(f)
            __version__ = data["project"]["version"]
    else:
        # Last resort fallback (shouldn't happen in normal usage)
        __version__ = "unknown"
