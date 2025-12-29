# Contributing to Powertools

Thank you for your interest in contributing to Powertools! This document provides guidelines and instructions for contributing.

## Development Workflow

### Branch Protection

The `main` branch is protected. All changes must be made via pull requests:

1. **Create a feature branch** from `main`

   ```bash
   git checkout -b feat/your-feature-name
   ```

2. **Make your changes** and commit them using [conventional commits](#commit-messages)

3. **Push your branch** and create a pull request

   ```bash
   git push origin feat/your-feature-name
   ```

4. **Open a PR** on GitHub and merge when ready

**Direct commits to `main` are not allowed** - all changes must go through the PR process.

**Note for solo developers**: The repository owner can merge their own PRs without requiring external reviews. When additional contributors join, this can be adjusted to require peer reviews.

## Setup

### Prerequisites

- **Apple Silicon Mac** (M1/M2/M3/M4) - required for MLX dependencies
- **macOS 14+**
- **Python 3.12+**
- **uv** - fast Python package manager
- **Docker/Podman/OrbStack** - for containerized services

### Development Environment

```bash
# Clone the repository
git clone git@github.com:fincognition/powertools.git
cd powertools

# Install dependencies (including dev tools)
uv pip install -e ".[dev]"

# Run tests
pytest

# Format code
ruff format .

# Lint code
ruff check .

# Type check
mypy src/
```

## Code Style

### Python

- **Python 3.12+** features are welcome (type hints, match statements, generic syntax, etc.)
- **Type hints required** for all public APIs
- **Format with `ruff format`** - line length 100
- **Lint with `ruff check`** - follows PEP 8 with project-specific overrides
- **Type check with `mypy`** - strict mode enabled

### Import Organization

- Import modules at the top of files (no inline imports)
- Prefer module imports over individual function imports when importing multiple items:

  ```python
  # Good
  from powertools.core import config
  config.load_config()

  # Avoid
  from powertools.core.config import load_config, save_config, get_user_config_dir
  ```

### Function Naming

- Public functions (CLI commands, public APIs): no prefix
- Private/internal functions: use `_` prefix

  ```python
  def init():  # Public CLI command
      ...

  def _check_platform():  # Private helper
      ...
  ```

### Error Handling

- Use proper exception chaining: `raise NewError(...) from None` when intentionally suppressing original exception
- Provide clear error messages for user-facing errors
- Use specific exception types (e.g., `ValueError`, `KeyError`) rather than generic `Exception`

## Testing

### Test Structure

- Place tests in `tests/` directory
- Mirror `src/` structure in test files
- Use `pytest` for all tests
- Async tests use `pytest-asyncio` (auto mode enabled)

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_tasks.py

# Run with coverage (if configured)
pytest --cov=powertools
```

### Writing Tests

- Test public APIs and critical paths
- Use descriptive test names
- Keep tests focused and atomic
- Mock external dependencies (HTTP, file system, etc.)

## Commit Messages

We use [Conventional Commits](https://www.conventionalcommits.org/) for consistent commit messages:

```
<type>: <subject>

[optional body]

[optional footer]
```

### Types

- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `refactor:` - Code refactoring (no behavior change)
- `perf:` - Performance improvements
- `test:` - Adding or updating tests
- `chore:` - Maintenance tasks (dependencies, tooling, etc.)

### Examples

```bash
feat: add support for custom embedding models

fix: handle missing Qdrant connection gracefully

docs: update installation instructions for uv

refactor: consolidate import patterns across CLI modules

test: add tests for hierarchical task ID generation
```

## Pull Request Process

1. **Update documentation** if you're adding features or changing behavior
2. **Add tests** for new functionality
3. **Ensure all tests pass** (`pytest`)
4. **Format and lint** your code (`ruff format . && ruff check .`)
5. **Type check** passes (`mypy src/`)
6. **Write clear PR description** explaining:
   - What changes you made
   - Why you made them
   - Any breaking changes
   - How to test the changes

### PR Title

Use conventional commit format for PR titles (they'll be used in changelogs):

```
feat: add support for custom embedding models
```

## Project Structure

```
powertools/
├── src/powertools/     # Source code
│   ├── cli/            # CLI commands
│   ├── core/           # Business logic
│   ├── embed/          # Embedding daemon
│   ├── mcp/            # MCP server tools
│   └── storage/        # Storage backends
├── tests/              # Test suite
├── .github/            # GitHub workflows and configs
└── pyproject.toml      # Project configuration
```

## Architecture Notes

### Key Components

- **Memory System**: Vector-based semantic search using Qdrant + MLX embeddings
- **Task System**: Hierarchical task tracking with JSONL storage
- **Embedding Daemon**: Launchd service running MLX on Apple Silicon
- **MCP Server**: SSE-based server exposing tools to AI agents

### Design Principles

- **Apple Silicon First**: MLX dependencies require Apple Silicon Macs
- **Per-Project Isolation**: Each project gets its own Qdrant collection
- **Agent-Agnostic**: MCP protocol allows any agent to use powertools
- **Simple Storage**: JSONL for metadata, Qdrant for vectors

## Questions?

- Open an issue for bug reports or feature requests
- Start a discussion for questions or design ideas
- Check `AGENTS.md` for detailed architecture and API documentation

Thank you for contributing! 🎉
