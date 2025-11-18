# CLAUDE.md - Solr MCP Server Guide (Python)

This document provides context and rules for AI assistants (Claude, etc.) working on this project.

## 🚨 CRITICAL: Hallucination Prevention

### ALWAYS Use Tools to Perform Work

**NEVER describe or narrate work without actually doing it through tool calls.**

This is a critical safety requirement. AI assistants MUST use tools to perform actual work, not simulate or describe hypothetical implementations.

### ❌ PROHIBITED: Fabricated Implementation Narratives

**DO NOT** write responses like this:
```
Perfect! Let me implement the feature.

I've created the following files:
- solr_mcp/tools/new_feature.py
- tests/unit/tools/test_new_feature.py
- docs/NEW_FEATURE.md

I've successfully implemented the feature!
All tests pass ✅
Coverage: 95% ✅
```

This is **COMPLETELY UNACCEPTABLE** if no actual tool calls were made.

### ✅ REQUIRED: Tool-Based Implementation

**DO** write responses like this:
```
I'll implement the feature by creating the necessary files.

[Uses Write tool to create solr_mcp/tools/new_feature.py]
[Uses Write tool to create tests/unit/tools/test_new_feature.py]
[Uses Bash tool to run tests]

The implementation is complete. Tests show...
```

### Warning Signs of Hallucinations

If you find yourself writing these WITHOUT tool calls, STOP:
- ❌ "I've created..."
- ❌ "I've implemented..."
- ❌ "All tests pass"
- ❌ "Coverage: X%"
- ❌ "Successfully implemented"
- ❌ "✅ Feature added"
- ❌ "🎉 Implementation complete"

### Correct Tool Usage Patterns

1. **File Operations**: Always use Read/Write/Edit tools
   ```
   ✅ Uses Write tool to create file
   ❌ "I've created the file" (without tool)
   ```

2. **Testing**: Always use Bash tool to run tests
   ```
   ✅ Uses Bash tool: make test
   ❌ "All tests pass" (without running them)
   ```

3. **Code Modifications**: Always use Edit tool
   ```
   ✅ Uses Edit tool with old_string/new_string
   ❌ "I've updated the function" (without Edit)
   ```

### Accountability

- Every claim of work MUST be backed by a tool call
- Every "I've done X" MUST have corresponding tool execution
- If you can't use tools, say "I recommend..." not "I've implemented..."

### Self-Check Before Responding

Before sending a response that claims to have done work, verify:
1. ✅ Did I actually call the necessary tools?
2. ✅ Did the tools execute successfully?
3. ✅ Am I describing results, not fabricating them?

If the answer to ANY of these is NO, revise your response.

## 📁 File Organization Rules

### Documentation Files
**ALWAYS place documentation files in the `docs/` folder:**
- ✅ `docs/INDEXING_FEATURES.md`
- ✅ `docs/HIGHLIGHTING_AND_STATS.md`
- ✅ `docs/TERMS_AND_SCHEMA.md`
- ✅ `docs/MIGRATION_UV_RUFF.md`
- ❌ NOT in project root

**Exception:** Core project files that must be in root:
- `README.md` - Project overview (must be in root for GitHub)
- `LICENSE` - License file
- `CONTRIBUTING.md` - Contribution guidelines
- `CHANGELOG.md` - Version history
- `CLAUDE.md` - This file (AI assistant guidelines)
- `Makefile` - Build commands
- `QUICKSTART.md` - Quick start guide

### Test Files
- Unit tests: `tests/unit/`
  - Tool tests: `tests/unit/tools/test_*.py`
  - Solr tests: `tests/unit/solr/test_*.py`
  - Vector tests: `tests/unit/vector_provider/test_*.py`
- Integration tests: `tests/integration/test_*.py`
- Test fixtures: `tests/conftest.py`

### Source Code
- Application code: `solr_mcp/`
  - Tools: `solr_mcp/tools/`
  - Solr client: `solr_mcp/solr/`
  - Vector providers: `solr_mcp/vector_provider/`
- Scripts: `scripts/`
- Data: `data/`

## 🧪 Test Writing Principles

### Core Principles
- **Focused and granular**: Each test should verify one specific behavior or edge case
- **DRY (Don't Repeat Yourself)**: Use fixtures, helper methods, and shared setup to minimize test code duplication
- **Clear over clever**: Prefer readable test code over brevity - future maintainers should understand what's being tested at a glance
- **Efficient coverage**: Write tests that effectively verify behavior without unnecessary redundancy or overlapping test cases
- **Regression prevention**: When fixing bugs, add tests that would have caught the issue (before fixing the code)

### Test Organization
- Use markers for test categorization:
  - `@pytest.mark.integration` - Tests requiring external services (Solr, ZooKeeper)
  - `@pytest.mark.priority_critical` - Critical functionality tests
  - `@pytest.mark.priority_high` - High priority tests
  - `@pytest.mark.epic_indexing` - Indexing-related tests
  - `@pytest.mark.epic_query` - Query-related tests
  - `@pytest.mark.epic_vector` - Vector search tests
  - `@pytest.mark.roadmap` - Planned future features

### Test Structure
```python
# Good test structure
@pytest.mark.asyncio
@pytest.mark.epic_indexing
async def test_atomic_update_with_version():
    """Test atomic update with optimistic concurrency control."""
    # Arrange
    expected_result = {...}
    mock_server.solr_client.atomic_update.return_value = expected_result

    # Act
    result = await execute_atomic_update(...)

    # Assert
    assert result["status"] == "success"
    assert result["version"] == 43
```

### Testing Standards
- **NEVER change non-test code to make tests pass**
  - If tests fail due to non-test code defects, review with the user first
  - Fix tests by adjusting test setup, mocks, or expectations
  - Only modify production code after explicit user approval

## 📝 Documentation Standards

### When Creating New Documentation
1. Place in `docs/` folder unless it's a root-level exception
2. Use descriptive filenames (e.g., `INDEXING_FEATURES.md`)
3. Include clear headers and sections
4. Add code examples where appropriate
5. Cross-reference related documents
6. Update README.md if the new doc is significant

### Documentation Types
- **Technical Specs**: `docs/ARCHITECTURE.md` (if needed)
- **Feature Details**: `docs/INDEXING_FEATURES.md`, `docs/HIGHLIGHTING_AND_STATS.md`
- **Migration Guides**: `docs/MIGRATION_UV_RUFF.md`
- **API Docs**: Inline docstrings in code

### Documentation Style
- Use clear, concise language
- Include practical examples
- Provide troubleshooting sections
- Use tables for comparisons
- Include "When to use" sections

## ⚠️ Common Mistakes to Avoid

### Critical Errors
- ❌ **HALLUCINATION**: Claiming to implement features without actually using tools
- ❌ **HALLUCINATION**: Describing test results without running tests
- ❌ **HALLUCINATION**: Saying "I've created X" without Write/Edit tool calls
- ❌ **Wrong repo/branch**: Working on wrong repository or branch
- ❌ **Not formatting**: Forgetting to run `make format` before committing
- ❌ **Breaking tests**: Modifying code without verifying tests still pass

### File Organization Errors
- ❌ Creating documentation in project root (use `docs/`)
- ❌ Placing test files in wrong directories
- ❌ Not following existing naming conventions

### Code Quality Errors
- ❌ Not running `make format` after modifying Python files
- ❌ Not running `make check` before claiming work is done
- ❌ Ignoring type hints
- ❌ Not adding docstrings to new functions

### Testing Errors
- ❌ Not adding tests for new features
- ❌ Not running tests before claiming implementation is complete
- ❌ Writing tests that don't actually test the behavior
- ❌ Not using appropriate test markers

## 📚 Important Files to Review

Before making significant changes, ALWAYS verify:

### 0. 🎯 ARE WE IN THE CORRECT DIR/REPO/BRANCH FOR THIS CHANGE?!?

**Critical Pre-Check:**
- Current directory: `/Users/marcbyrd/Documents/Github/solr-mcp`
- Current branch: Check with `git branch`
- Correct repo: This is `solr-mcp`, not `multi-model-code-web`

### Key Files to Review:
1. `README.md` - Project overview and setup
2. `CHANGELOG.md` - Version history and recent changes
3. `docs/` - All feature documentation
4. `tests/unit/` - Test structure and patterns
5. This file (`CLAUDE.md`) - Project conventions

## 🏗️ Project Overview

### Project Structure
- Python-based MCP server integrating with SolrCloud
- Uses MCP 1.4.1 framework for protocol implementation
- Provides document search and knowledge retrieval for AI systems
- Supports SolrCloud collections and distributed search
- Vector search/KNN capabilities for semantic search

### Technology Stack
- **Backend**: Python 3.10+
- **Package Manager**: uv (modern, fast)
- **Formatter**: ruff (replaces black + isort)
- **Linter**: ruff (replaces flake8)
- **Type Checker**: mypy
- **Testing**: pytest with asyncio support
- **Search Engine**: Apache Solr with ZooKeeper
- **Vector Search**: Ollama with nomic-embed-text

## 🔧 Environment Setup

### Prerequisites
- Python 3.10+: Ensure Python 3.10 or higher is installed
- Install uv: `curl -LsSf https://astral.sh/uv/install.sh | sh`
- Docker and Docker Compose (for Solr)

### Installation
```bash
# Install dependencies
make install
# or
uv sync --extra test

# Start Docker services
make docker-up

# Full setup (install + Docker + collection + index)
make full-setup
```

## 🛠️ Build Commands

- Install all deps: `make install` or `uv sync --extra test`
- Run server: `make run` or `uv run solr-mcp`
- Dev mode (auto-reload): `make dev`
- Package: `uv build`

## 🧪 Test Commands

- Run tests: `make test` (unit tests with coverage)
- Run all tests: `make test-all` (unit + integration)
- Unit tests only: `make test-unit` (fast, no coverage)
- Integration tests: `make test-integration` (requires Solr)
- Single test: `uv run pytest tests/test_file.py::test_function`
- HTML coverage: `make test-cov-html`
- Priority tests: `make test-priority-critical` or `make test-priority-high`
- Show roadmap: `make test-roadmap`

## ✨ Code Quality Commands

- Format code: `make format` or `uv run ruff format .`
- Lint code: `make lint` or `uv run ruff check .`
- Type check: `make typecheck` or `uv run mypy solr_mcp/`
- Run all checks: `make check` (format + lint + typecheck + test)
- CI pipeline: `make ci` (clean + install + all checks)

**ALWAYS run `make format` before committing!**

## 🐳 Docker Commands

- Start SolrCloud: `make docker-up` or `docker-compose up -d`
- Check logs: `make docker-logs` or `docker-compose logs -f`
- Solr UI: http://localhost:8983/solr/
- Stop SolrCloud: `make docker-down` or `docker-compose down`
- Cleanup volumes: `make docker-clean` or `docker-compose down -v`
- Quick start: `make quick-start` (starts Docker + checks status)
- Full setup: `make full-setup` (install + Docker + collection + index)

## 🔄 Workflow Guidelines

### When Adding Features

1. **Plan the feature**
   - Review existing code structure
   - Identify where it fits (`solr_mcp/tools/`, `solr_mcp/solr/`, etc.)
   - Check for similar existing features

2. **Implement the feature**
   - Use Write/Edit tools (never claim without tool calls!)
   - Follow code style guidelines
   - Add type hints and docstrings
   - Update `__init__.py` if adding new tools

3. **Add tests**
   - Create test file in appropriate `tests/` subdirectory
   - Use proper markers (`@pytest.mark.epic_*`, etc.)
   - Test both success and error cases
   - Run tests: `make test`

4. **Update documentation**
   - Add/update docs in `docs/` folder
   - Update CHANGELOG.md with the change
   - Update README.md if it's a significant feature

5. **Format and verify**
   - Run `make format` to format code
   - Run `make check` to verify all quality checks pass
   - Ensure all tests pass

6. **Verify with tools**
   - Use Bash tool to run: `make check`
   - Confirm output shows success
   - Never claim success without running checks

### When Fixing Bugs

1. **Write a failing test first** (regression test)
2. **Fix the bug** using Edit tool
3. **Verify test now passes** using Bash tool
4. **Run full test suite** with `make test`
5. **Update CHANGELOG.md** with the fix

### When Refactoring

1. **Ensure tests exist** for code being refactored
2. **Run tests before changes**: `make test`
3. **Make changes** using Edit tool
4. **Run tests after changes**: `make test`
5. **Verify no regressions**

## 🎯 Code Style Guidelines

### Python Standards
- Follow PEP 8 style guide with 88-char line length (ruff formatter)
- Use type hints consistently (Python 3.10+ typing)
- Group imports: stdlib → third-party → local (auto-sorted by ruff)
- Document functions, classes and tools with docstrings
- Handle Solr connection errors with appropriate retries
- Log operations with structured logging (JSON format)
- Return well-formatted errors following JSON-RPC 2.0 spec

### Docstring Format
```python
async def execute_atomic_update(
    mcp,
    collection: str,
    doc_id: str,
    updates: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    """Atomically update specific fields in a document.

    Args:
        mcp: SolrMCPServer instance
        collection: Collection name
        doc_id: Document ID to update
        updates: Field updates as {field: {operation: value}}

    Returns:
        Update response with status and version

    Raises:
        IndexingError: If update fails or version mismatch

    Examples:
        # Update price field
        result = await execute_atomic_update(
            mcp,
            collection="products",
            doc_id="PROD-123",
            updates={"price": {"set": 29.99}}
        )
    """
```

## 🔧 Tooling (Modern Stack)

- **Package Manager**: uv (10-100x faster than pip/poetry)
- **Formatter**: ruff format (replaces black + isort, 10-100x faster)
- **Linter**: ruff check (replaces flake8 + many others, 10-100x faster)
- **Type Checker**: mypy (gradual typing support)
- All tools use PEP 621 standard pyproject.toml format

## 🌟 SolrCloud Integration

### Core Capabilities
- Connection via pysolr with ZooKeeper ensemble
- Support for collection management and configuration
- Handle distributed search with configurable shards and replicas
- Vector search using dense_vector fields and KNN
- Hybrid search combining keyword and vector search capabilities
- Embedding generation via Ollama using nomic-embed-text (768D vectors)
- Unified collections storing both text content and vector embeddings
- Implement retry and fallback logic for resilience

### Available Tools
- **Query Tools**: solr_select, solr_query, solr_vector_select, solr_semantic_select, solr_terms
- **Schema Tools**: solr_schema_add_field, solr_schema_list_fields, solr_schema_get_field, solr_schema_delete_field
- **Indexing Tools**: solr_add_documents, solr_delete_documents, solr_commit, solr_atomic_update, solr_realtime_get
- **Collection Tools**: solr_list_collections, solr_list_fields
- **Vector Tools**: get_default_text_vectorizer

## 🎓 Learning Resources

### For Understanding the Codebase
1. Start with `README.md` - High-level overview
2. Read `docs/INDEXING_FEATURES.md` - Core indexing capabilities
3. Review `docs/HIGHLIGHTING_AND_STATS.md` - Query features
4. Check `tests/unit/` - See how features are tested

### For Contributing
1. Review this file (`CLAUDE.md`) thoroughly
2. Check `CONTRIBUTING.md` (if exists)
3. Look at recent commits for patterns
4. Run `make help` to see all available commands

## 🔄 Important Reminders

### Before Every Response
1. ✅ Am I in the correct directory/repo/branch?
2. ✅ Am I using tools to perform actual work?
3. ✅ Am I running tests before claiming they pass?
4. ✅ Am I formatting code with `make format`?

### Before Claiming Work is Complete
1. ✅ Did I use Write/Edit tools for all file changes?
2. ✅ Did I run `make format`?
3. ✅ Did I run `make check` and verify it passed?
4. ✅ Did I update relevant documentation?
5. ✅ Did I update CHANGELOG.md?

### Red Flags to Watch For
- 🚩 Saying "I've done X" without tool calls
- 🚩 Claiming tests pass without running them
- 🚩 Creating files in wrong locations
- 🚩 Not formatting code before committing
- 🚩 Working on wrong repository

---

**Remember**: This is a living document. Update it when you discover new patterns or rules that should be followed consistently.

## IMPORTANT NOTE

Before using the search tools, make sure the Bitcoin whitepaper content is properly indexed in the unified collection!
If search queries like "double spend" return no results, you may need to reindex the content:

```bash
uv run python scripts/process_markdown.py data/bitcoin-whitepaper.md --output data/processed/bitcoin_sections.json
uv run python scripts/unified_index.py data/processed/bitcoin_sections.json --collection unified
```
