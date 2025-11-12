# Use bash for all recipes
SHELL := /bin/bash

# Define the default virtual environment directory
VENV_DIR ?= .venv

.DEFAULT_GOAL := help

# Prevent make from conflicting with file names
.PHONY: all install dev run test test-unit test-integration test-cov test-cov-html \
        test-priority-critical test-priority-high test-roadmap \
        lint typecheck format clean clean-test clean-pyc clean-build \
        docker-up docker-down docker-logs docker-restart docker-clean \
        solr-status solr-collections solr-create-test solr-create-unified \
        solr-index-test solr-index-unified \
        help .install-uv

# Colors for terminal output
CYAN := \033[0;36m
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m # No Color

# Project variables
COVERAGE_MIN := 66

## --------------------------------------
## Internal Prerequisites
## --------------------------------------

# This hidden target checks if 'uv' is installed
.install-uv:
	@command -v uv >/dev/null 2>&1 || { echo "$(RED)Error: 'uv' not found. Install with: curl -LsSf https://astral.sh/uv/install.sh | sh$(NC)" >&2; exit 1; }

## --------------------------------------
## Project Setup & Installation
## --------------------------------------

# `uv sync` creates the venv AND installs all dependencies
install: .install-uv ## Install all dependencies into .venv
	@echo "$(GREEN)--- 📦 Installing dependencies into $(VENV_DIR) ---$(NC)"
	uv sync --extra test

# Alias for install (for compatibility)
all: install

install-dev: install ## Alias for install (installs all deps including test)

setup: install ## Full setup: install deps + check environment
	@echo "$(GREEN)--- ✓ Development environment ready ---$(NC)"

## --------------------------------------
## Testing & QA
## --------------------------------------

# Run unit tests only (no coverage, fast)
test-unit: install ## Run unit tests only (fast, no coverage)
	@echo "$(GREEN)--- 🐍 Running Python unit tests ---$(NC)"
	uv run env PYTHONPATH=. pytest tests/unit -v

# Run unit tests with coverage
test: install ## Run unit tests with coverage and type checking
	@echo "$(GREEN)--- 🔍 Type checking with mypy ---$(NC)"
	uv run mypy solr_mcp/
	@echo "$(GREEN)--- 🧪 Running tests with coverage ---$(NC)"
	uv run env PYTHONPATH=. pytest tests/unit --cov=solr_mcp --cov-report=term-missing --cov-fail-under=$(COVERAGE_MIN)

# Run integration tests only (requires Solr)
test-integration: install ## Run integration tests (requires Solr running)
	@echo "$(YELLOW)Warning: This requires Solr to be running (make docker-up)$(NC)"
	@echo "$(GREEN)--- 🔗 Running integration tests ---$(NC)"
	uv run env PYTHONPATH=. pytest tests/integration -m integration -v

# Run all tests (unit + integration)
test-all: install ## Run all tests (unit + integration, requires Solr)
	@echo "$(YELLOW)Warning: This requires Solr to be running (make docker-up)$(NC)"
	@echo "$(GREEN)--- 🧪 Running all tests ---$(NC)"
	uv run env PYTHONPATH=. pytest tests/ -v

# Generate HTML coverage report
test-cov-html: install ## Run tests with HTML coverage report
	@echo "$(GREEN)--- 📊 Generating HTML coverage report ---$(NC)"
	uv run env PYTHONPATH=. pytest tests/unit --cov=solr_mcp --cov-report=html --cov-report=term
	@echo "$(GREEN)✓ Coverage report generated at: htmlcov/index.html$(NC)"
	@if command -v open > /dev/null; then \
		open htmlcov/index.html; \
	fi

# Alias for test
test-cov: test

# Run tests by priority
test-priority-critical: install ## Run critical priority tests
	@echo "$(GREEN)--- 🔴 Running critical priority tests ---$(NC)"
	uv run env PYTHONPATH=. pytest -m priority_critical -v

test-priority-high: install ## Run high priority tests
	@echo "$(GREEN)--- 🟠 Running high priority tests ---$(NC)"
	uv run env PYTHONPATH=. pytest -m priority_high -v

# Show roadmap scenarios (planned features)
test-roadmap: install ## Show all planned features (roadmap scenarios)
	@echo "$(GREEN)--- 🗺️  Product Roadmap - Planned Features ---$(NC)"
	uv run env PYTHONPATH=. pytest -m roadmap -v --collect-only

## --------------------------------------
## Code Quality
## --------------------------------------

# Lint the code with ruff
lint: install ## Lint code with ruff
	@echo "$(GREEN)--- 🧹 Linting code ---$(NC)"
	uv run ruff check .

# Type check the code with mypy
typecheck: install ## Type check code with mypy
	@echo "$(GREEN)--- 🔍 Type checking with mypy ---$(NC)"
	uv run mypy solr_mcp/

# Format the code with ruff
format: install ## Format code with ruff
	@echo "$(GREEN)--- ✨ Formatting code ---$(NC)"
	uv run ruff format .
	uv run ruff check --fix --select I .

# Run all checks (format + lint + typecheck + test)
check: format ## Run all checks (format + lint + typecheck + test)
	@echo "$(GREEN)--- 🔍 Running all checks ---$(NC)"
	@echo ""
	@echo "=== Type Checking ==="
	@uv run mypy solr_mcp/ || exit 1
	@echo ""
	@echo "=== Linting ==="
	@uv run ruff check . || exit 1
	@echo ""
	@echo "=== Unit Tests ==="
	@uv run env PYTHONPATH=. pytest tests/unit --cov=solr_mcp --cov-report=term-missing || exit 1
	@echo ""
	@echo "$(GREEN)✓ All checks passed!$(NC)"

## --------------------------------------
## Docker Operations
## --------------------------------------

docker-up: ## Start Docker services (Solr, ZooKeeper, Ollama)
	@echo "$(GREEN)--- 🐳 Starting Docker services ---$(NC)"
	docker-compose up -d
	@echo "$(GREEN)✓ Services starting...$(NC)"
	@echo "$(CYAN)Solr UI: http://localhost:8983$(NC)"

docker-down: ## Stop Docker services
	@echo "$(YELLOW)--- 🛑 Stopping Docker services ---$(NC)"
	docker-compose down

docker-logs: ## Show Docker logs (follow mode)
	docker-compose logs -f

docker-logs-solr: ## Show Solr logs only
	docker-compose logs -f solr1

docker-restart: docker-down docker-up ## Restart Docker services

docker-clean: docker-down ## Stop and remove Docker containers and volumes
	@echo "$(RED)--- 🗑️  Removing Docker volumes ---$(NC)"
	docker-compose down -v
	@echo "$(GREEN)✓ Docker environment cleaned$(NC)"

## --------------------------------------
## Solr Operations
## --------------------------------------

solr-status: ## Check Solr cluster status
	@echo "$(GREEN)--- ☁️  Checking Solr status ---$(NC)"
	@curl -s http://localhost:8983/solr/admin/collections?action=CLUSTERSTATUS | python3 -m json.tool || echo "$(RED)✗ Solr not available$(NC)"

solr-collections: ## List all Solr collections
	@echo "$(GREEN)--- 📚 Solr collections ---$(NC)"
	@curl -s http://localhost:8983/solr/admin/collections?action=LIST | python3 -m json.tool

solr-create-test: install ## Create test collection
	@echo "$(GREEN)--- 🏗️  Creating test collection ---$(NC)"
	uv run python scripts/create_test_collection.py

solr-create-unified: install ## Create unified collection with vectors
	@echo "$(GREEN)--- 🏗️  Creating unified collection ---$(NC)"
	uv run python scripts/create_unified_collection.py

solr-index-test: install ## Index test documents
	@echo "$(GREEN)--- 📝 Indexing test documents ---$(NC)"
	uv run python scripts/simple_index.py

solr-index-unified: install ## Index documents to unified collection
	@echo "$(GREEN)--- 📝 Indexing to unified collection ---$(NC)"
	uv run python scripts/unified_index.py

## --------------------------------------
## Application
## --------------------------------------

run: server ## Run the MCP server (alias for server)

server: install ## Run the Solr MCP server
	@echo "$(GREEN)--- 🚀 Starting Solr MCP server ---$(NC)"
	uv run solr-mcp

dev: install ## Run server in development mode with auto-reload
	@echo "$(GREEN)--- 🔧 Starting Solr MCP server (development mode) ---$(NC)"
	uv run uvicorn solr_mcp.server:app --reload --host 0.0.0.0 --port 8080

test-mcp: install ## Run MCP test script
	@echo "$(GREEN)--- 🧪 Testing MCP server ---$(NC)"
	uv run python scripts/simple_mcp_test.py

## --------------------------------------
## Cleanup
## --------------------------------------

clean: clean-test clean-pyc clean-build ## Remove all build, test, coverage and Python artifacts

clean-test: ## Remove test and coverage artifacts
	@echo "$(YELLOW)--- 🧹 Cleaning test artifacts ---$(NC)"
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf coverage.xml
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/

clean-pyc: ## Remove Python file artifacts
	@echo "$(YELLOW)--- 🧹 Cleaning Python artifacts ---$(NC)"
	find . -type f -name '*.pyc' -delete
	find . -type f -name '*.pyo' -delete
	find . -type d -name '__pycache__' -exec rm -rf {} +
	find . -type d -name '*.egg-info' -exec rm -rf {} +

clean-build: ## Remove build artifacts
	@echo "$(YELLOW)--- 🧹 Cleaning build artifacts ---$(NC)"
	rm -rf build/
	rm -rf dist/
	rm -rf .eggs/

clean-venv: ## Remove virtual environment
	@echo "$(RED)--- 🗑️  Removing virtual environment ---$(NC)"
	rm -rf $(VENV_DIR)

## --------------------------------------
## Quick Commands
## --------------------------------------

quick-test: install ## Quick test run (unit tests only, no coverage)
	@uv run env PYTHONPATH=. pytest tests/unit -q

quick-start: docker-up ## Quick start: bring up Docker and check status
	@sleep 5
	@make solr-status

full-setup: install docker-up solr-create-unified solr-index-unified ## Full setup: install, start Docker, create collection, index data
	@echo "$(GREEN)✓ Full setup complete!$(NC)"
	@echo "$(CYAN)Solr UI: http://localhost:8983$(NC)"
	@echo "$(CYAN)Run 'make server' to start the MCP server$(NC)"

ci: clean install check ## Run CI pipeline (clean + install + format + lint + typecheck + test)
	@echo "$(GREEN)✓ CI pipeline completed successfully!$(NC)"

## --------------------------------------
## Help
## --------------------------------------

help: ## Display this help message
	@echo "$(CYAN)Solr MCP - Makefile Commands$(NC)"
	@echo ""
	@echo "$(YELLOW)Setup & Installation:$(NC)"
	@echo "  $(CYAN)make install$(NC)                - Install all dependencies (incl. test) into .venv"
	@echo "  $(CYAN)make setup$(NC)                  - Full setup: install deps"
	@echo ""
	@echo "$(YELLOW)Testing:$(NC)"
	@echo "  $(CYAN)make test$(NC)                   - Run unit tests with coverage"
	@echo "  $(CYAN)make test-unit$(NC)              - Run unit tests only (fast, no coverage)"
	@echo "  $(CYAN)make test-integration$(NC)       - Run integration tests (requires Solr)"
	@echo "  $(CYAN)make test-all$(NC)               - Run all tests (unit + integration)"
	@echo "  $(CYAN)make test-cov-html$(NC)          - Generate HTML coverage report"
	@echo "  $(CYAN)make test-priority-critical$(NC) - Run critical priority tests"
	@echo "  $(CYAN)make test-priority-high$(NC)     - Run high priority tests"
	@echo "  $(CYAN)make test-roadmap$(NC)           - Show all planned features"
	@echo ""
	@echo "$(YELLOW)Code Quality:$(NC)"
	@echo "  $(CYAN)make format$(NC)                 - Format code with ruff"
	@echo "  $(CYAN)make lint$(NC)                   - Lint code with ruff"
	@echo "  $(CYAN)make typecheck$(NC)              - Type check code with mypy"
	@echo "  $(CYAN)make check$(NC)                  - Run all checks (format + lint + typecheck + test)"
	@echo ""
	@echo "$(YELLOW)Docker Operations:$(NC)"
	@echo "  $(CYAN)make docker-up$(NC)              - Start Docker services (Solr, ZooKeeper)"
	@echo "  $(CYAN)make docker-down$(NC)            - Stop Docker services"
	@echo "  $(CYAN)make docker-logs$(NC)            - Show Docker logs"
	@echo "  $(CYAN)make docker-clean$(NC)           - Stop and remove containers and volumes"
	@echo ""
	@echo "$(YELLOW)Solr Operations:$(NC)"
	@echo "  $(CYAN)make solr-status$(NC)            - Check Solr cluster status"
	@echo "  $(CYAN)make solr-collections$(NC)       - List all Solr collections"
	@echo "  $(CYAN)make solr-create-unified$(NC)    - Create unified collection"
	@echo "  $(CYAN)make solr-index-unified$(NC)     - Index documents to unified collection"
	@echo ""
	@echo "$(YELLOW)Application:$(NC)"
	@echo "  $(CYAN)make run$(NC)                    - Run the MCP server"
	@echo "  $(CYAN)make dev$(NC)                    - Run server in development mode (auto-reload)"
	@echo ""
	@echo "$(YELLOW)Quick Commands:$(NC)"
	@echo "  $(CYAN)make quick-test$(NC)             - Quick test run (unit tests, no coverage)"
	@echo "  $(CYAN)make quick-start$(NC)            - Quick start: Docker + status check"
	@echo "  $(CYAN)make full-setup$(NC)             - Full setup: install + Docker + collection + index"
	@echo "  $(CYAN)make ci$(NC)                     - Run CI pipeline (all checks + tests)"
	@echo ""
	@echo "$(YELLOW)Cleanup:$(NC)"
	@echo "  $(CYAN)make clean$(NC)                  - Remove all build, test, and cache files"
	@echo "  $(CYAN)make clean-venv$(NC)             - Remove virtual environment"
