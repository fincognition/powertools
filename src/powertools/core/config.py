"""Configuration loading and management for powertools."""

import os
from dataclasses import dataclass, field
from pathlib import Path

import fast_yaml as yaml  # noqa: N813 - imported as yaml for easy reversion


@dataclass
class QdrantConfig:
    """Qdrant vector database configuration."""

    url: str = "http://localhost:6333"


@dataclass
class EmbeddingConfig:
    """Embedding provider configuration."""

    api_base: str = "http://localhost:8384"
    model: str = "mlx-community/Qwen3-Embedding-0.6B-4bit-DWQ"
    dimensions: int = 1024  # Qwen3-Embedding-0.6B output dimension


@dataclass
class ContainerConfig:
    """Container runtime configuration."""

    runtime: str | None = None  # docker, podman, orbstack, etc.
    host_address: str = "host.docker.internal"  # How containers reach the host


@dataclass
class DaemonConfig:
    """Embedding daemon configuration."""

    installed: bool = False
    method: str = "launchd"  # launchd or brew


@dataclass
class ProjectConfig:
    """Project-specific configuration."""

    name: str = "default"
    container: ContainerConfig = field(default_factory=ContainerConfig)


@dataclass
class Config:
    """Main configuration container."""

    qdrant: QdrantConfig = field(default_factory=QdrantConfig)
    embedding: EmbeddingConfig = field(default_factory=EmbeddingConfig)
    project: ProjectConfig = field(default_factory=ProjectConfig)


def get_user_config_dir() -> Path:
    """Get the user-level config directory (~/.powertools/)."""
    return Path.home() / ".powertools"


def get_project_config_dir() -> Path:
    """Get the project-level config directory (.powertools/)."""
    return Path.cwd() / ".powertools"


def load_yaml_file(path: Path) -> dict:
    """Load a YAML file, returning empty dict if not found."""
    if not path.exists():
        return {}
    with open(path) as f:
        return yaml.safe_load(f) or {}


def merge_configs(base: dict, override: dict) -> dict:
    """Deep merge two config dictionaries, override takes precedence."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_configs(result[key], value)
        else:
            result[key] = value
    return result


def load_config() -> Config:
    """Load configuration from user and project levels, with env overrides."""
    # Start with defaults
    config_dict: dict = {}

    # Load user-level config
    user_config_path = get_user_config_dir() / "config.yaml"
    user_config = load_yaml_file(user_config_path)
    config_dict = merge_configs(config_dict, user_config)

    # Load project-level config
    project_config_path = get_project_config_dir() / "config.yaml"
    project_config = load_yaml_file(project_config_path)
    config_dict = merge_configs(config_dict, project_config)

    # Environment variable overrides
    if url := os.environ.get("QDRANT_URL"):
        config_dict.setdefault("qdrant", {})["url"] = url
    if api_base := os.environ.get("EMBEDDING_API_BASE"):
        config_dict.setdefault("embedding", {})["api_base"] = api_base

    # Build config object
    qdrant_dict = config_dict.get("qdrant", {})
    embedding_dict = config_dict.get("embedding", {})
    project_dict = config_dict.get("project", {})

    return Config(
        qdrant=QdrantConfig(**qdrant_dict) if qdrant_dict else QdrantConfig(),
        embedding=EmbeddingConfig(**embedding_dict) if embedding_dict else EmbeddingConfig(),
        project=ProjectConfig(**project_dict) if project_dict else ProjectConfig(),
    )


def save_user_config(config: Config) -> None:
    """Save configuration to user-level config file."""
    config_dir = get_user_config_dir()
    config_dir.mkdir(parents=True, exist_ok=True)

    config_dict = {
        "qdrant": {"url": config.qdrant.url},
        "embedding": {
            "api_base": config.embedding.api_base,
            "model": config.embedding.model,
            "dimensions": config.embedding.dimensions,
        },
    }

    config_path = config_dir / "config.yaml"
    with open(config_path, "w") as f:
        yaml.safe_dump(config_dict, f)


def save_project_config(
    project_name: str,
    container_runtime: str | None = None,
    host_address: str = "host.docker.internal",
) -> None:
    """Save project-level config file."""
    config_dir = get_project_config_dir()
    config_dir.mkdir(parents=True, exist_ok=True)

    # Create subdirectories
    (config_dir / "memory").mkdir(exist_ok=True)
    (config_dir / "tasks").mkdir(exist_ok=True)
    (config_dir / "logs").mkdir(exist_ok=True)

    config_dict = {
        "project": {
            "name": project_name,
        },
        "container": {
            "runtime": container_runtime,
            "host_address": host_address,
        },
    }

    config_path = config_dir / "config.yaml"
    with open(config_path, "w") as f:
        yaml.safe_dump(config_dict, f)
