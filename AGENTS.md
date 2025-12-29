# Powertools

Powertools is an agentic workflow toolkit for developers that provides persistent memory and task tracking for AI-assisted development. It is agent-agnostic and exposes capabilities via CLI (for users) and MCP servers (for agents).

**Platform:** Apple Silicon Mac only (M1/M2/M3/M4), macOS 14+

## Project Overview

### Core Components

1. **Project Memory** - Vector-based semantic memory for project context

   - Stores facts, decisions, patterns, architecture details
   - Semantic search via Qdrant + MLX embeddings (Qwen3)
   - Stored in `.powertools/memory/facts.jsonl`

2. **Task Tracking** - Beads-inspired hierarchical task graph
   - Hash-based IDs (`pt-a1b2`) to avoid merge conflicts
   - Dependency graph (blocks, parent-child, related)
   - Status: pending, in_progress, blocked, done, cancelled
   - Stored in `.powertools/tasks/tasks.jsonl`

### Architecture

```
Host (macOS Apple Silicon)
├── ~/.powertools/              # User-level config
│   ├── config.yaml
│   └── logs/                   # Daemon logs
│
├── powertools-embed (:8384)    # Launchd daemon (per-user)
│   └── MLX + Qwen3-Embedding-0.6B (4-bit)
│
└── .powertools/                # Project-level (gitignored)
    ├── config.yaml
    ├── compose.yaml            # Docker services for this project
    ├── memory/facts.jsonl
    └── tasks/tasks.jsonl

Docker/Podman/OrbStack (per-project)
├── qdrant:6333                 # Vector database
└── powertools-mcp:8765         # MCP server (SSE)
```

Embeddings run natively on host via MLX for Apple Silicon GPU acceleration.
Each project gets its own Qdrant collection (`pt_<project>`).
Containers reach host embedding daemon via `host.docker.internal` (or equivalent).

### Tech Stack

- **Language**: Python 3.12
- **Package Manager**: uv
- **CLI Framework**: click
- **MCP Transport**: SSE
- **Vector DB**: Qdrant (container)
- **Embeddings**: MLX + Qwen3-Embedding-0.6B-4bit (host daemon)
- **Storage**: JSONL

## Project Structure

```
powertools/
├── AGENTS.md                # This file
├── Dockerfile               # MCP server container image
├── pyproject.toml           # Python project config (uv)
├── LICENSE                  # MIT license
├── src/
│   └── powertools/
│       ├── __init__.py      # Package init
│       ├── __main__.py      # python -m powertools entry point
│       ├── py.typed         # PEP 561 type marker
│       ├── cli/             # Click CLI commands
│       │   ├── __init__.py  # Command registration
│       │   ├── main.py      # Entry point (pt)
│       │   ├── init.py      # pt init, pt project-init
│       │   ├── embed.py     # pt embed install/start/stop/status
│       │   ├── memory.py    # pt memory add/search/list/delete
│       │   └── tasks.py     # pt task create/ready/show/update/dep
│       ├── embed/           # Embedding server daemon
│       │   ├── server.py    # HTTP server (OpenAI-compatible)
│       │   └── daemon.py    # Launchd management
│       ├── mcp/             # MCP server implementations
│       │   ├── server.py    # SSE server setup
│       │   ├── memory.py    # Memory tools
│       │   └── tasks.py     # Task tools
│       ├── core/            # Business logic
│       │   ├── config.py    # Config loading/saving
│       │   ├── memory.py    # Memory operations
│       │   ├── tasks.py     # Task operations
│       │   └── embeddings.py # HTTP client for embed daemon
│       ├── storage/         # Storage backends
│       │   ├── jsonl.py     # JSONL read/write
│       │   └── qdrant.py    # Qdrant client wrapper
│       └── templates/       # Template files
│           ├── compose.yaml # Docker compose template
│           └── agents_section.md # AGENTS.md template
└── tests/                   # Test suite
    ├── test_jsonl.py        # JSONL storage tests
    └── test_tasks.py        # Task management tests
```

## Data Schemas

### Task (JSONL)

```json
{
  "id": "pt-a1b2",
  "title": "Implement auth middleware",
  "description": "Add JWT validation to API routes",
  "status": "pending",
  "priority": 1,
  "type": "task",
  "parent": null,
  "blocks": ["pt-c3d4"],
  "blocked_by": [],
  "related": [],
  "context": "See docs/auth.md for JWT spec",
  "tags": ["auth", "api"],
  "created": "2025-12-29T10:00:00Z",
  "updated": "2025-12-29T10:00:00Z"
}
```

**Status**: `pending`, `in_progress`, `blocked`, `done`, `cancelled`
**Priority**: `0` (critical), `1` (high), `2` (medium), `3` (low)
**Type**: `epic`, `task`, `subtask`, `bug`

### Memory Fact (JSONL)

```json
{
  "id": "mem-x1y2",
  "content": "The API uses JWT tokens with RS256 signing",
  "source": "docs/auth.md:42",
  "category": "architecture",
  "confidence": 1.0,
  "created": "2025-12-29T10:00:00Z"
}
```

**Categories**: `architecture`, `decision`, `pattern`, `dependency`, `convention`, `fact`

## CLI Commands

```bash
# Setup
pt init                             # Initialize ~/.powertools/, install daemon
pt project-init                     # Initialize .powertools/ in current project

# Memory
pt memory add "fact content"        # Add a fact
pt memory search "query"            # Semantic search
pt memory list [--category X]       # List facts
pt memory show <id>                 # Show fact details
pt memory delete <id>               # Delete a fact

# Tasks
pt task create "title" [-p priority] [-t type] [--parent id] [--blocks id...] [--tag tag...] [--context text]
pt task ready                       # List unblocked tasks by priority
pt task show <id>                   # Show task details
pt task update <id> [--status X] [--title X] [--description X] [--context X] [--priority X]
pt task dep add <child> <parent>    # Add dependency
pt task dep rm <child> <parent>     # Remove dependency
pt task list [--status X] [--tag X] [--type X] [--limit N] # List/filter tasks

# Embedding daemon
pt embed install                    # Install launchd daemon
pt embed uninstall                  # Remove daemon
pt embed start                      # Start daemon
pt embed stop                       # Stop daemon
pt embed restart                    # Restart daemon
pt embed status                     # Check daemon status
pt embed logs                       # View daemon logs
pt embed serve                      # Run in foreground (testing)
```

## MCP Server Tools

### Memory Tools

| Tool            | Parameters                        | Description                   |
| --------------- | --------------------------------- | ----------------------------- |
| `add_memory`    | `content`, `source?`, `category?` | Add a fact to project memory  |
| `search_memory` | `query`, `limit?`                 | Semantic search over memories |
| `list_memories` | `category?`, `limit?`             | List memories by category     |
| `delete_memory` | `id`                              | Delete a memory               |

### Task Tools

| Tool                | Parameters                                                          | Description                            |
| ------------------- | ------------------------------------------------------------------- | -------------------------------------- |
| `create_task`       | `title`, `description?`, `priority?`, `type?`, `parent?`, `blocks?` | Create a task                          |
| `get_ready_tasks`   | `limit?`                                                            | Get unblocked tasks sorted by priority |
| `get_task`          | `id`                                                                | Get task details                       |
| `update_task`       | `id`, `status?`, `title?`, `description?`, `context?`, `priority?`  | Update a task                          |
| `add_dependency`    | `child_id`, `parent_id`                                             | Child is blocked by parent             |
| `remove_dependency` | `child_id`, `parent_id`                                             | Remove dependency                      |
| `list_tasks`        | `status?`, `tag?`, `type?`, `limit?`                                | List/filter tasks                      |

## Configuration

### ~/.powertools/config.yaml (User-level)

```yaml
embedding:
  api_base: http://localhost:8384
  model: mlx-community/Qwen3-Embedding-0.6B-4bit-DWQ
  dimensions: 1024

qdrant:
  url: http://localhost:6333
```

### .powertools/config.yaml (Project-level)

```yaml
project:
  name: myproject

container:
  runtime: docker # or podman, orbstack
  host_address: host.docker.internal
```

## Development Guidelines

### Code Style

- Python 3.12+ features welcome (type hints, match statements, etc.)
- Use `uv` for dependency management
- Format with `ruff format`, lint with `ruff check`
- Type hints required for public APIs

### Testing

- Use `pytest` for tests
- Place tests in `tests/` mirroring `src/` structure

### Commits

- Use conventional commits: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`
- Keep commits atomic and focused

## Roadmap

### Completed

- [x] Project structure and CLI skeleton
- [x] Task system with JSONL storage
- [x] Memory system with Qdrant
- [x] MLX embedding daemon for Apple Silicon
- [x] Launchd daemon management
- [x] Container runtime detection (Docker/Podman/OrbStack)
- [x] Per-project compose.yaml generation
- [x] MCP server Docker image
- [x] Basic test suite (JSONL storage, task management)
- [x] Type hints and py.typed marker
- [x] Python module entry point (python -m powertools)

### Planned

- [ ] Enhanced error handling and validation
- [ ] brew formula for installation
- [ ] GitHub Actions for Docker image publishing

## Future Plans

- **AST-based indexing** - Use ast-grep for code structure analysis
- **User-level long-term memory** - Cross-project user preferences
- **Team-shared docs** - Checked-in project memory in `docs/`
