# Makefile Documentation

This project includes a comprehensive Makefile to simplify common development, testing, and deployment tasks.

## Quick Reference

```bash
make help           # Show all available commands
make install-dev    # Install development dependencies
make test           # Run all tests
make docker-up      # Start Solr and ZooKeeper
make server         # Run the MCP server
```

## Command Categories

### 🚀 Installation & Setup

| Command | Description |
|---------|-------------|
| `make install` | Install production dependencies only |
| `make install-dev` | Install all dependencies (dev + prod) |
| `make setup` | Full setup including pre-commit hooks |

**Example:**
```bash
# First time setup
make install-dev
```

---

### 🧪 Testing

| Command | Description |
|---------|-------------|
| `make test` | ⭐ Run unit tests with coverage (no Docker) - **RECOMMENDED** |
| `make test-unit` | Run unit tests only (fast, no coverage) |
| `make test-all` | Run all tests (unit + integration, requires Docker/Solr) |
| `make test-integration` | Run integration tests (requires Solr) |
| `make test-cov` | Alias for `make test` |
| `make test-cov-html` | Generate HTML coverage report and open it |
| `make test-watch` | Run tests in watch mode (requires pytest-watch) |
| `make quick-test` | Quick test run without coverage |

**Examples:**
```bash
# Run tests with coverage
make test-cov

# Generate and view HTML coverage report
make test-cov-html

# Quick test during development
make quick-test
```

**Current Coverage Target:** 66%

---

### 🔍 Code Quality

| Command | Description |
|---------|-------------|
| `make lint` | Run linting (flake8, mypy) |
| `make format` | Format code (black, isort) |
| `make check` | Run lint + unit tests |
| `make type-check` | Run type checking with mypy |

**Examples:**
```bash
# Format code before committing
make format

# Run all quality checks
make check
```

---

### 🐳 Docker Operations

| Command | Description |
|---------|-------------|
| `make docker-build` | Build Docker images |
| `make docker-up` | Start Solr and ZooKeeper services |
| `make docker-down` | Stop Docker services |
| `make docker-logs` | Show logs (follow mode) |
| `make docker-logs-solr` | Show Solr logs only |
| `make docker-restart` | Restart all services |
| `make docker-clean` | Stop and remove containers + volumes |

**Examples:**
```bash
# Start services
make docker-up

# Check logs
make docker-logs

# Complete cleanup
make docker-clean
```

**Services Started:**
- Solr UI: http://localhost:8983
- ZooKeeper: localhost:2181

---

### 🔎 Solr Operations

| Command | Description |
|---------|-------------|
| `make solr-status` | Check Solr cluster status |
| `make solr-collections` | List all collections |
| `make solr-create-test` | Create test collection |
| `make solr-create-unified` | Create unified collection with vectors |
| `make solr-index-test` | Index test documents |
| `make solr-index-unified` | Index to unified collection |
| `make solr-search-demo` | Run search demo |

**Examples:**
```bash
# Check if Solr is running
make solr-status

# Create and index a collection
make solr-create-unified
make solr-index-unified
```

---

### 🖥️ Application

| Command | Description |
|---------|-------------|
| `make server` | Run the Solr MCP server |
| `make run` | Alias for `make server` |
| `make dev` | Run server with auto-reload (development mode) |
| `make test-mcp` | Test MCP server functionality |

**Examples:**
```bash
# Run server normally
make server

# Run in development mode (auto-reload)
make dev

# Test MCP server
make test-mcp
```

---

### 🧹 Cleanup

| Command | Description |
|---------|-------------|
| `make clean` | Remove all build/test/coverage artifacts |
| `make clean-test` | Remove test and coverage artifacts only |
| `make clean-pyc` | Remove Python cache files |
| `make clean-build` | Remove build artifacts |
| `make clean-venv` | Remove virtual environment |

**Examples:**
```bash
# Clean everything
make clean

# Clean test artifacts only
make clean-test
```

---

### 📦 Release & Publishing

| Command | Description |
|---------|-------------|
| `make version` | Show current version |
| `make version-patch` | Bump patch version (0.1.0 → 0.1.1) |
| `make version-minor` | Bump minor version (0.1.0 → 0.2.0) |
| `make version-major` | Bump major version (0.1.0 → 1.0.0) |
| `make build` | Build package (wheel + sdist) |
| `make publish` | Publish to PyPI |
| `make publish-test` | Publish to TestPyPI |

**Examples:**
```bash
# Check current version
make version

# Bump version and build
make version-patch
make build
```

---

### ⚡ Quick Commands

Special commands that combine multiple operations:

| Command | Description |
|---------|-------------|
| `make quick-test` | Quick test without coverage |
| `make quick-start` | Start Docker + check status |
| `make full-setup` | Complete setup: install + Docker + create collection + index |
| `make ci` | Run CI pipeline (clean + install + lint + test with coverage) |

**Examples:**
```bash
# Complete first-time setup
make full-setup

# Run CI checks locally
make ci

# Quick start development environment
make quick-start
```

---

## Common Workflows

### 🆕 First Time Setup

```bash
# Clone repository
git clone <repo-url>
cd solr-mcp

# Complete setup
make full-setup

# Start coding!
make dev
```

### 💻 Daily Development

```bash
# Start services
make docker-up

# Run tests in watch mode
make test-watch

# Format code
make format

# Run server
make dev
```

### ✅ Before Committing

```bash
# Format code
make format

# Run all checks
make check

# Or run the full CI pipeline
make ci
```

### 🚀 Release Process

```bash
# Run tests
make test-cov

# Bump version
make version-patch  # or version-minor, version-major

# Build and publish
make build
make publish
```

### 🐛 Troubleshooting

```bash
# Clean everything and restart
make clean
make docker-clean
make full-setup

# Check Solr status
make solr-status
make docker-logs-solr
```

---

## Environment Variables

The Makefile uses these default settings:

- **Python Version**: 3.10+
- **Virtual Environment**: `.venv`
- **Coverage Minimum**: 66%
- **Solr URL**: http://localhost:8983
- **ZooKeeper**: localhost:2181

---

## Tips & Tricks

### Chaining Commands

```bash
# Format, lint, and test in one go
make format && make check
```

### Selective Testing

```bash
# Run specific test file
poetry run pytest tests/unit/test_specific.py -v

# Run tests matching pattern
poetry run pytest -k "test_query" -v
```

### Coverage Threshold

To change the minimum coverage requirement, edit the Makefile:

```makefile
COVERAGE_MIN := 66  # Change this value
```

### Docker Compose Override

Create `docker-compose.override.yml` for local customizations without modifying the main file.

---

## Requirements

- **Python**: 3.10 or higher
- **Poetry**: For dependency management
- **Docker**: For running Solr and ZooKeeper
- **Make**: Should be pre-installed on macOS/Linux

**Install Poetry:**
```bash
curl -sSL https://install.python-poetry.org | python3 -
```

---

## Color Output

The Makefile uses colored output for better readability:

- 🔵 **Cyan**: Command names and info
- 🟢 **Green**: Success messages
- 🟡 **Yellow**: Warnings and cleanup operations
- 🔴 **Red**: Errors and destructive operations

---

## Contributing

When adding new Makefile targets:

1. Add to appropriate category (`##@` comment)
2. Add inline documentation (`##` comment)
3. Update this documentation
4. Test the command works correctly

**Example:**
```makefile
##@ Testing

my-new-command: ## Description of what it does
	@echo "$(GREEN)Running my command...$(NC)"
	command-to-run
```

---

## Getting Help

```bash
# Show all available commands
make help

# Or just run make without arguments
make
```

For project-specific help, see [README.md](README.md) and [QUICKSTART.md](QUICKSTART.md).
