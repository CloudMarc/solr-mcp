# Migration Guide: Poetry + Black → uv + ruff

This guide helps you migrate from the old Poetry + Black + isort + flake8 stack to the modern uv + ruff stack.

## Overview

The Solr MCP project has been modernized with faster, more efficient tooling:

| Old Tool | New Tool | Speed Improvement |
|----------|----------|-------------------|
| Poetry | uv | 10-100x faster |
| black + isort | ruff format | 10-100x faster |
| flake8 | ruff check | 10-100x faster |

## What Changed

### 1. Package Manager: Poetry → uv

**Before:**
```bash
poetry install
poetry run pytest
poetry run python -m solr_mcp.server
```

**After:**
```bash
uv sync --extra test  # or: make install
uv run pytest
uv run solr-mcp       # or: make server
```

### 2. Code Formatting: black + isort → ruff

**Before:**
```bash
poetry run black solr_mcp tests
poetry run isort solr_mcp tests
```

**After:**
```bash
uv run ruff format .  # or: make format
# ruff handles both formatting and import sorting!
```

### 3. Linting: flake8 → ruff

**Before:**
```bash
poetry run flake8 solr_mcp tests
```

**After:**
```bash
uv run ruff check .   # or: make lint
```

### 4. Configuration: pyproject.toml

**Before (Poetry format):**
```toml
[tool.poetry.dependencies]
python = "^3.10"
pysolr = "^3.9.0"

[tool.black]
line-length = 88

[tool.isort]
profile = "black"

[tool.flake8]
max-line-length = 88
```

**After (PEP 621 standard):**
```toml
[project]
name = "solr-mcp"
requires-python = ">=3.10"
dependencies = [
    "pysolr>=3.9.0",
]

[tool.ruff]
line-length = 88

[tool.ruff.lint]
select = ["E", "W", "F", "I"]
```

## Migration Steps

### Step 1: Install uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Verify installation:
```bash
uv --version
```

### Step 2: Clean Old Environment

Remove the old Poetry-managed environment:

```bash
# Clean old artifacts
make clean
# or manually:
rm -rf .venv
rm -rf poetry.lock
```

### Step 3: Install Dependencies with uv

```bash
# Install all dependencies including test extras
uv sync --extra test

# Verify it worked
uv run python --version
uv run pytest --version
```

### Step 4: Update Your Workflow

Replace old commands with new ones:

**Development:**
```bash
# Old: poetry run python -m solr_mcp.server
make server
# or: uv run solr-mcp

# Old: poetry run uvicorn ... --reload
make dev
```

**Testing:**
```bash
# Old: poetry run pytest
make test
# or: uv run pytest tests/unit

# Old: poetry run pytest --cov
make test  # includes coverage by default
```

**Code Quality:**
```bash
# Old: poetry run black . && poetry run isort . && poetry run flake8 .
make format && make lint
# or: uv run ruff format . && uv run ruff check .

# Or run everything at once:
make check  # format + lint + typecheck + test
```

### Step 5: Update CI/CD (if applicable)

If you have GitHub Actions or similar:

**Before:**
```yaml
- name: Install dependencies
  run: |
    pip install poetry
    poetry install

- name: Run tests
  run: poetry run pytest
```

**After:**
```yaml
- name: Install uv
  run: curl -LsSf https://astral.sh/uv/install.sh | sh

- name: Install dependencies
  run: uv sync --extra test

- name: Run tests
  run: make test
```

## New Features Available

### Enhanced Test Markers

You can now run tests by priority:

```bash
make test-priority-critical  # Critical tests only
make test-priority-high      # High priority tests
make test-roadmap            # Show planned features
```

### Better Makefile Commands

```bash
make help                # Show all available commands
make quick-test          # Fast test run (no coverage)
make full-setup          # Complete setup from scratch
make ci                  # Run full CI pipeline
```

## Troubleshooting

### "Command not found: uv"

Make sure uv is in your PATH. After installation, restart your terminal or run:
```bash
source ~/.bashrc  # or ~/.zshrc
```

### "Module not found" errors

Make sure you've installed dependencies:
```bash
uv sync --extra test
```

### "ruff: command not found"

Ruff is installed as a project dependency. Always use it via `uv run`:
```bash
uv run ruff format .
uv run ruff check .
```

Or use the Makefile (which handles this automatically):
```bash
make format
make lint
```

### Tests fail after migration

Run a clean install:
```bash
make clean
make install
make test
```

### Code formatting looks different

Ruff is designed to be 100% compatible with black. If you see differences, it's likely due to:
1. Outdated black configuration (ruff uses the pyproject.toml settings)
2. Import ordering differences (ruff follows black + isort rules)

To fix, just run:
```bash
make format
```

## Compatibility Notes

### Poetry Commands Still Work (for now)

If you have `poetry.lock` in your repo, Poetry commands will still work. However, we recommend migrating fully to uv for:
- Faster dependency resolution
- Better caching
- Industry standard PEP 621 format

### Black/isort Configuration Preserved

All your black and isort configuration has been migrated to ruff-compatible settings. Your code style remains identical.

### No Code Changes Required

The migration only affects tooling. Your Python code, imports, and formatting remain the same.

## Benefits You'll See

### Performance

- ⚡ **10-100x faster** dependency installation
- ⚡ **10-100x faster** code formatting
- ⚡ **10-100x faster** linting
- ⚡ **Faster CI/CD** pipelines

### Simplicity

- 📦 **One tool (ruff)** replaces three (black + isort + flake8)
- 🔧 **Fewer dependencies** in pyproject.toml
- 📝 **Simpler configuration**

### Modern Standards

- 🎯 **PEP 621** standard format
- 🔄 **Industry adoption** (ruff/uv are becoming the standard)
- 🛠️ **Active development** (both by Astral/Charlie Marsh)

## Quick Reference

### Common Commands

| Task | Old Command | New Command | Makefile |
|------|-------------|-------------|----------|
| Install | `poetry install` | `uv sync --extra test` | `make install` |
| Run server | `poetry run python -m solr_mcp.server` | `uv run solr-mcp` | `make server` |
| Run tests | `poetry run pytest` | `uv run pytest tests/unit` | `make test` |
| Format code | `poetry run black .` | `uv run ruff format .` | `make format` |
| Lint code | `poetry run flake8 .` | `uv run ruff check .` | `make lint` |
| Type check | `poetry run mypy solr_mcp` | `uv run mypy solr_mcp/` | `make typecheck` |

### File Changes

| File | Status |
|------|--------|
| `pyproject.toml` | ✅ Migrated to PEP 621 |
| `Makefile` | ✅ Updated to use uv/ruff |
| `CLAUDE.md` | ✅ Updated with new commands |
| `README.md` | ✅ Updated installation instructions |
| `scripts/lint.py` | ❌ Removed (replaced by ruff) |
| `scripts/format.py` | ❌ Removed (replaced by ruff) |
| `poetry.lock` | ℹ️ Can be removed (replaced by uv.lock) |

## Getting Help

If you encounter issues during migration:

1. Check this guide's troubleshooting section
2. Run `make clean && make install` for a fresh start
3. File an issue at https://github.com/allenday/solr-mcp/issues

## Additional Resources

- [uv Documentation](https://github.com/astral-sh/uv)
- [ruff Documentation](https://docs.astral.sh/ruff/)
- [PEP 621 Specification](https://peps.python.org/pep-0621/)
- [Solr MCP Makefile Guide](../MAKEFILE.md)
