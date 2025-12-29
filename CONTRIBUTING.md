# Contributing to Powertools

Thank you for your interest in contributing to Powertools! This document provides guidelines and instructions for contributing.

## Development Workflow

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

# Run linting checks
./script/lint

# Run tests
./script/test
```

**Note:** The `script/lint` and `script/test` scripts automatically find the project root using git, so they can be run from any directory in the repository.

## Code Style

### Python

- **Python 3.12+** features are welcome (type hints, match statements, generic syntax, etc.)
- **Type hints required** for all public APIs
- **Format with `ruff format`** - line length 100
- **Lint with `ruff check`** - follows PEP 8 with project-specific overrides
- **Type check with `mypy`** - strict mode enabled

### Import Organization

- Import modules at the top of files (no inline imports), unless unavoidable
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
# Run all tests (quiet mode, shows output only on failure)
./script/test

# Or run pytest directly
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
3. **Run linting checks** (`./script/lint`) - ensures formatting, linting, and type checking pass
4. **Run tests** (`./script/test`) - ensures all tests pass with coverage
5. **Write clear PR description** explaining:
   - What changes you made
   - Why you made them
   - Any breaking changes
   - How to test the changes

**Note:** The `script/lint` and `script/test` scripts run all checks automatically. You can also run individual tools directly if needed.

### PR Title

Use conventional commit format for PR titles (they'll be used in changelogs):

```
feat: add support for custom embedding models
```

## Releases and Versioning

Powertools uses [python-semantic-release](https://python-semantic-release.readthedocs.io/) to automatically manage versions and create releases based on conventional commit messages.

### How It Works

1. **When a PR is merged to `main`:**

   - CI runs lint-and-test checks
   - If checks pass, semantic-release analyzes commits since the last release
   - If commits indicate a version bump is needed, semantic-release will:
     - Update the version in `pyproject.toml`
     - Create a git tag (e.g., `v0.2.0`)
     - Generate a changelog entry
     - Build a wheel package
     - Create a GitHub release with the wheel and changelog
     - Build and publish Docker images
   - If no version bump is needed, the release step is skipped

2. **Version Bump Rules:**

   - `feat:` commits → **Minor version** bump (0.1.0 → 0.2.0)
   - `fix:` commits → **Patch version** bump (0.1.0 → 0.1.1)
   - `BREAKING CHANGE:` in commit body or `!` after type → **Major version** bump (0.1.0 → 1.0.0)
   - `chore:`, `docs:`, `refactor:`, `test:` → No version bump (unless breaking)

3. **Manual Version Bumps:**
   - **Do not manually edit the version in `pyproject.toml`** - semantic-release manages it automatically
   - If you need to force a specific version bump, use the appropriate commit message:
     - `feat: ...` for minor bump
     - `fix: ...` for patch bump
     - `feat!: ...` or include `BREAKING CHANGE:` for major bump

### Examples

```bash
# This will trigger a minor version bump (0.1.0 → 0.2.0)
feat: add support for custom embedding models

# This will trigger a patch version bump (0.1.0 → 0.1.1)
fix: handle missing Qdrant connection gracefully

# This will trigger a major version bump (0.1.0 → 1.0.0)
feat!: change API authentication method

BREAKING CHANGE: API now requires OAuth2 instead of API keys
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
├── script/             # Development scripts
│   ├── lint            # Run all linting checks
│   └── test            # Run tests with coverage
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
