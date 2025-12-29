"""Powertools - Agentic workflow toolkit with persistent memory and task tracking."""

import tomllib
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

try:
    # Try to get version from installed package metadata (works for installed packages)
    __version__ = version("powertools")
except PackageNotFoundError:
    # Fallback for editable installs: read from pyproject.toml
    pyproject_path = Path(__file__).parent.parent.parent.parent / "pyproject.toml"
    if pyproject_path.exists():
        with open(pyproject_path, "rb") as f:
            data = tomllib.load(f)
            __version__ = data["project"]["version"]
    else:
        # Last resort fallback (shouldn't happen in normal usage)
        __version__ = "unknown"
