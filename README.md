# Powertools

Agentic workflow toolkit for developers. Provides persistent semantic memory and task tracking for AI-assisted development.

[![CI](https://github.com/fincognition/powertools/actions/workflows/ci.yml/badge.svg)](https://github.com/fincognition/powertools/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/fincognition/powertools/branch/main/graph/badge.svg)](https://codecov.io/gh/fincognition/powertools)
[![GitHub release](https://img.shields.io/github/release/fincognition/powertools.svg)](https://github.com/fincognition/powertools/releases)
[![PyPI version](https://badge.fury.io/py/powertools-ai.svg)](https://badge.fury.io/py/powertools-ai)
[![Homebrew](https://img.shields.io/badge/homebrew-coming%20soon-lightgrey.svg)](https://brew.sh)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Platform: macOS](https://img.shields.io/badge/platform-macOS%20%7C%20Apple%20Silicon-lightgrey.svg)](https://www.apple.com/mac/)
[![Status: Alpha](https://img.shields.io/badge/status-alpha-orange.svg)](https://github.com/fincognition/powertools)

**Requirements:** Apple Silicon Mac (M1/M2/M3/M4), macOS 14+

## Install

```bash
# Homebrew (coming soon)
# brew install powertools

# uv (fast Python package manager)
uv pip install powertools-ai
```

## Setup

```bash
# Initialize (one-time) - installs embedding daemon, downloads model
pt init

# Initialize a project
cd your-project
pt project-init -n myproject

# Start containers
docker compose -f .powertools/compose.yaml up -d
```

## Usage

### Memory (Semantic Search)

```bash
# Add facts to project memory
pt memory add "API uses JWT tokens with RS256 signing" --category architecture
pt memory add "Use snake_case for database columns" --category convention

# Search semantically
pt memory search "authentication"
pt memory search "naming conventions"

# List and manage
pt memory list
pt memory show mem-abc123
pt memory delete mem-abc123
```

### Tasks (Hierarchical Tracking)

```bash
# Create tasks
pt task create "Implement user auth" --priority 1
pt task create "Add JWT middleware" --parent pt-a1b2

# View ready tasks (unblocked, by priority)
pt task ready

# Update status
pt task update pt-a1b2 --status in_progress
pt task update pt-a1b2 --status done

# Add dependencies
pt task dep add pt-c3d4 pt-a1b2  # c3d4 blocked by a1b2
```

### MCP Server

Connect your AI agent to the MCP server at `http://localhost:8765/sse`.

Available tools:

- `add_memory`, `search_memory`, `list_memories`, `delete_memory`
- `create_task`, `get_ready_tasks`, `get_task`, `update_task`, `add_dependency`, `list_tasks`

## Commands

```bash
pt init              # Initialize ~/.powertools/ and install embedding daemon
pt project-init      # Initialize .powertools/ in current directory

pt memory add        # Add a fact
pt memory search     # Semantic search
pt memory list       # List all memories
pt memory show       # Show memory details
pt memory delete     # Delete a memory

pt task create       # Create a task
pt task ready        # List unblocked tasks by priority
pt task show         # Show task details
pt task update       # Update task status/content
pt task list         # List/filter tasks
pt task dep add/rm   # Manage dependencies

pt embed status      # Check embedding daemon status
pt embed start/stop  # Control daemon
pt embed logs        # View daemon logs
```

## Architecture

```
Host (macOS Apple Silicon)
├── powertools-embed (:8384)     # MLX embedding daemon (launchd)
│   └── Qwen3-Embedding-0.6B
│
└── Docker/Podman/OrbStack
    ├── Qdrant (:6333)           # Vector database
    └── Powertools MCP (:8765)   # MCP server for agents
```

- Embeddings run natively on Apple Silicon GPU via MLX
- Each project gets its own Qdrant collection (`pt_<project>`)
- Compose file generated per-project in `.powertools/compose.yaml`

## Configuration

**~/.powertools/config.yaml**

```yaml
embedding:
  api_base: http://localhost:8384
  model: mlx-community/Qwen3-Embedding-0.6B-4bit-DWQ
  dimensions: 1024
qdrant:
  url: http://localhost:6333
```

## License

MIT
