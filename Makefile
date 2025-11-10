.PHONY: help install install-dev test test-unit test-integration test-cov test-cov-html \
        lint format check clean clean-test clean-pyc clean-build \
        docker-build docker-up docker-down docker-logs docker-restart \
        solr-start solr-stop solr-create-collection solr-status \
        run server dev \
        docs-build docs-serve \
        publish version

.DEFAULT_GOAL := help

# Colors for terminal output
CYAN := \033[0;36m
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m # No Color

# Project variables
PYTHON := python3
VENV := .venv
POETRY := poetry
PYTEST := $(VENV)/bin/pytest
COVERAGE_MIN := 66

##@ General

help: ## Display this help message
	@echo "$(CYAN)Solr MCP - Makefile Commands$(NC)"
	@echo ""
	@awk 'BEGIN {FS = ":.*##"; printf "Usage:\n  make $(CYAN)<target>$(NC)\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  $(CYAN)%-20s$(NC) %s\n", $$1, $$2 } /^##@/ { printf "\n$(YELLOW)%s$(NC)\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

##@ Installation & Setup

install: ## Install production dependencies using Poetry
	@echo "$(GREEN)Installing production dependencies...$(NC)"
	$(POETRY) install --only main

install-dev: ## Install all dependencies including dev dependencies
	@echo "$(GREEN)Installing development dependencies...$(NC)"
	$(POETRY) install
	@echo "$(GREEN)✓ Development environment ready$(NC)"

setup: install-dev ## Full setup: install deps + setup pre-commit hooks
	@echo "$(GREEN)Setting up project...$(NC)"
	@if command -v pre-commit > /dev/null; then \
		pre-commit install; \
		echo "$(GREEN)✓ Pre-commit hooks installed$(NC)"; \
	else \
		echo "$(YELLOW)⚠ pre-commit not found, skipping hook installation$(NC)"; \
	fi

##@ Testing

test: ## Run unit tests with coverage (no Docker required)
	@echo "$(GREEN)Running unit tests with coverage...$(NC)"
	$(POETRY) run pytest tests/unit --cov=solr_mcp --cov-report=term-missing --cov-fail-under=$(COVERAGE_MIN)

test-unit: ## Run unit tests only (fast, no coverage)
	@echo "$(GREEN)Running unit tests (no coverage)...$(NC)"
	$(POETRY) run pytest tests/unit -v

test-all: ## Run all tests (unit + integration, requires Docker/Solr)
	@echo "$(YELLOW)Warning: This requires Solr to be running (make docker-up)$(NC)"
	@echo "$(GREEN)Running all tests...$(NC)"
	$(POETRY) run pytest tests/ -v

test-integration: ## Run integration tests only (requires Solr)
	@echo "$(YELLOW)Warning: This requires Solr to be running (make docker-up)$(NC)"
	@echo "$(GREEN)Running integration tests...$(NC)"
	$(POETRY) run pytest tests/integration -v -m integration

test-cov: ## Alias for 'make test' (unit tests with coverage)
	@$(MAKE) test

test-cov-html: ## Run tests with HTML coverage report
	@echo "$(GREEN)Generating HTML coverage report...$(NC)"
	$(POETRY) run pytest tests/unit --cov=solr_mcp --cov-report=html --cov-report=term
	@echo "$(GREEN)✓ Coverage report generated at: htmlcov/index.html$(NC)"
	@if command -v open > /dev/null; then \
		open htmlcov/index.html; \
	fi

test-watch: ## Run tests in watch mode (requires pytest-watch)
	@echo "$(GREEN)Running tests in watch mode...$(NC)"
	$(POETRY) run ptw -- tests/unit -v

##@ Code Quality

lint: ## Run linting checks (flake8, mypy)
	@echo "$(GREEN)Running linters...$(NC)"
	$(POETRY) run lint

format: ## Format code with black and isort
	@echo "$(GREEN)Formatting code...$(NC)"
	$(POETRY) run format

check: lint test-unit ## Run all checks (lint + unit tests)
	@echo "$(GREEN)✓ All checks passed!$(NC)"

type-check: ## Run type checking with mypy
	@echo "$(GREEN)Running type checks...$(NC)"
	$(POETRY) run mypy solr_mcp

##@ Docker Operations

docker-build: ## Build Docker images
	@echo "$(GREEN)Building Docker images...$(NC)"
	docker-compose build

docker-up: ## Start Docker services (Solr, ZooKeeper)
	@echo "$(GREEN)Starting Docker services...$(NC)"
	docker-compose up -d
	@echo "$(GREEN)✓ Services starting...$(NC)"
	@echo "$(CYAN)Solr UI: http://localhost:8983$(NC)"

docker-down: ## Stop Docker services
	@echo "$(YELLOW)Stopping Docker services...$(NC)"
	docker-compose down

docker-logs: ## Show Docker logs (follow mode)
	docker-compose logs -f

docker-logs-solr: ## Show Solr logs only
	docker-compose logs -f solr1

docker-restart: docker-down docker-up ## Restart Docker services

docker-clean: docker-down ## Stop and remove Docker containers, volumes
	@echo "$(RED)Removing Docker volumes...$(NC)"
	docker-compose down -v
	@echo "$(GREEN)✓ Docker environment cleaned$(NC)"

##@ Solr Operations

solr-status: ## Check Solr cluster status
	@echo "$(GREEN)Checking Solr status...$(NC)"
	@curl -s http://localhost:8983/solr/admin/collections?action=CLUSTERSTATUS | python3 -m json.tool || echo "$(RED)✗ Solr not available$(NC)"

solr-collections: ## List all Solr collections
	@echo "$(GREEN)Solr collections:$(NC)"
	@curl -s http://localhost:8983/solr/admin/collections?action=LIST | python3 -m json.tool

solr-create-test: ## Create test collection
	@echo "$(GREEN)Creating test collection...$(NC)"
	$(POETRY) run python scripts/create_test_collection.py

solr-create-unified: ## Create unified collection with vectors
	@echo "$(GREEN)Creating unified collection...$(NC)"
	$(POETRY) run python scripts/create_unified_collection.py

solr-index-test: ## Index test documents
	@echo "$(GREEN)Indexing test documents...$(NC)"
	$(POETRY) run python scripts/simple_index.py

solr-index-unified: ## Index documents to unified collection
	@echo "$(GREEN)Indexing to unified collection...$(NC)"
	$(POETRY) run python scripts/unified_index.py

solr-search-demo: ## Run search demo
	$(POETRY) run python scripts/demo_search.py

##@ Application

run: server ## Run the MCP server (alias for server)

server: ## Run the Solr MCP server
	@echo "$(GREEN)Starting Solr MCP server...$(NC)"
	$(POETRY) run solr-mcp

dev: ## Run server in development mode with auto-reload
	@echo "$(GREEN)Starting Solr MCP server (development mode)...$(NC)"
	$(POETRY) run uvicorn solr_mcp.server:app --reload --host 0.0.0.0 --port 8080

test-mcp: ## Run MCP test script
	@echo "$(GREEN)Testing MCP server...$(NC)"
	$(POETRY) run python scripts/simple_mcp_test.py

##@ Cleanup

clean: clean-test clean-pyc clean-build ## Remove all build, test, coverage and Python artifacts

clean-test: ## Remove test and coverage artifacts
	@echo "$(YELLOW)Cleaning test artifacts...$(NC)"
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf coverage.xml
	rm -rf .mypy_cache/

clean-pyc: ## Remove Python file artifacts
	@echo "$(YELLOW)Cleaning Python artifacts...$(NC)"
	find . -type f -name '*.pyc' -delete
	find . -type f -name '*.pyo' -delete
	find . -type d -name '__pycache__' -exec rm -rf {} +
	find . -type d -name '*.egg-info' -exec rm -rf {} +

clean-build: ## Remove build artifacts
	@echo "$(YELLOW)Cleaning build artifacts...$(NC)"
	rm -rf build/
	rm -rf dist/
	rm -rf .eggs/

clean-venv: ## Remove virtual environment
	@echo "$(RED)Removing virtual environment...$(NC)"
	rm -rf $(VENV)

##@ Release & Publishing

version: ## Show current version
	@$(POETRY) version

version-patch: ## Bump patch version (0.1.0 -> 0.1.1)
	@echo "$(GREEN)Bumping patch version...$(NC)"
	$(POETRY) version patch
	@echo "$(GREEN)New version: $$(poetry version -s)$(NC)"

version-minor: ## Bump minor version (0.1.0 -> 0.2.0)
	@echo "$(GREEN)Bumping minor version...$(NC)"
	$(POETRY) version minor
	@echo "$(GREEN)New version: $$(poetry version -s)$(NC)"

version-major: ## Bump major version (0.1.0 -> 1.0.0)
	@echo "$(GREEN)Bumping major version...$(NC)"
	$(POETRY) version major
	@echo "$(GREEN)New version: $$(poetry version -s)$(NC)"

build: ## Build package
	@echo "$(GREEN)Building package...$(NC)"
	$(POETRY) build
	@echo "$(GREEN)✓ Package built in dist/$(NC)"

publish: build ## Build and publish package to PyPI
	@echo "$(GREEN)Publishing package...$(NC)"
	$(POETRY) publish

publish-test: build ## Build and publish to TestPyPI
	@echo "$(GREEN)Publishing to TestPyPI...$(NC)"
	$(POETRY) publish -r testpypi

##@ Quick Commands

quick-test: ## Quick test run (unit tests only, no coverage)
	@$(POETRY) run pytest tests/unit -q

quick-start: docker-up ## Quick start: bring up Docker and check status
	@sleep 5
	@make solr-status

full-setup: install-dev docker-up solr-create-unified solr-index-unified ## Full setup: install, start Docker, create collection, index data
	@echo "$(GREEN)✓ Full setup complete!$(NC)"
	@echo "$(CYAN)Solr UI: http://localhost:8983$(NC)"
	@echo "$(CYAN)Run 'make server' to start the MCP server$(NC)"

ci: clean install-dev lint test ## Run CI pipeline (lint + test with coverage)
	@echo "$(GREEN)✓ CI pipeline completed successfully!$(NC)"
