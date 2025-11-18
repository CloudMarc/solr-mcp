# Clever Things You Can Do with Codebase Collection & Solr-MCP

This document demonstrates advanced search, analytics, and code discovery capabilities using the indexed codebase collection with solr-mcp.

## Overview

By indexing your codebase into Solr with both text content and vector embeddings, you can perform powerful code analysis and search operations that go far beyond simple grep.

## Quick Start

```bash
# Index your codebase
uv run python scripts/create_unified_collection.py codebase
uv run python scripts/index_codebase.py codebase

# Run example queries
uv run python scripts/clever_codebase_queries.py
uv run python scripts/tech_debt_tracker.py
```

## 1. Code Complexity Analysis

**Use Case**: Understand file sizes, code distribution, and identify large/complex files.

```bash
uv run python scripts/clever_codebase_queries.py
```

**What It Shows**:
- Total lines of code across the project
- Average file size statistics
- Largest files by line count
- Character count and average line length

**Example Output**:
```
Source Code Statistics:
  Total files analyzed: 51
  Total lines: 5,848
  Total characters: 191,192
  Average lines per file: 114.7

Largest files:
  solr_mcp/solr/client.py                    1012 lines
  solr_mcp/solr/schema/fields.py              734 lines
```

**Why It's Useful**: Identifies files that might need refactoring or splitting into smaller modules.

## 2. Documentation Coverage Analysis

**Use Case**: Find files that need better documentation.

**Query**: Files containing function/class definitions but missing standard docstring patterns.

**Example Output**:
```
Documentation Coverage:
  Files with docstrings: 40/51 (78.4%)

Files potentially missing docstrings:
  - solr_mcp/__init__.py
  - solr_mcp/solr/constants.py
```

**Why It's Useful**: Helps prioritize documentation efforts and maintain code quality.

## 3. Error Handling Pattern Analysis

**Use Case**: Understand how exceptions are handled across the codebase.

**What It Finds**:
- Files with try/except blocks
- Specific exception types used (ValueError, ConnectionError, etc.)
- Error handling coverage

**Example Output**:
```
Files with exception handling: 46

Exception type usage:
  SolrError            18 files
  ValueError            8 files
  ConnectionError       8 files
```

**Why It's Useful**: Ensures consistent error handling and identifies potential error-prone areas.

## 4. Technical Debt Tracking

**Use Case**: Find TODO, FIXME, HACK markers and track technical debt.

```bash
uv run python scripts/tech_debt_tracker.py
```

**What It Tracks**:
- TODO items
- FIXME markers
- HACK solutions
- XXX warnings
- Known bugs

**Example Output**:
```
📊 Technical Debt Summary:
  TODO       5 occurrences
  FIXME      3 occurrences

Files with Most Technical Debt:
  1. solr_mcp/tools/base.py       3 items
```

**Why It's Useful**: Provides a quantifiable view of technical debt and helps prioritize refactoring work.

## 5. Long Function Detection

**Use Case**: Find functions that might be too complex (code smell detection).

**Threshold**: Functions longer than 50 lines are flagged.

**Example Output**:
```
Long Functions (>50 lines):
  1. execute_vector_select_query    103 lines
  2. execute_query                   95 lines
  3. atomic_update                   84 lines
```

**Why It's Useful**: Long functions often indicate opportunities for refactoring and improved maintainability.

## 6. Missing Tests Detection

**Use Case**: Find source files that might not have corresponding test coverage.

**Method**: Compares source files against test files to find potential gaps.

**Example Output**:
```
Source files: 42
Test files: 56

Files potentially missing dedicated tests: 13
  - solr_mcp/tools/solr_commit.py
  - solr_mcp/tools/solr_select.py
```

**Why It's Useful**: Helps improve test coverage and identify testing gaps.

## 7. Dependency Analysis

**Use Case**: Understand import relationships and module dependencies.

**What It Shows**:
- Most commonly imported modules
- Files that depend on specific modules
- Potential circular dependencies

**Example Query**:
```python
# Find all files importing from solr_mcp.solr
q='content:"from solr_mcp.solr" OR content:"import solr_mcp.solr"'
```

**Why It's Useful**: Helps understand architecture and refactor module boundaries.

## 8. Recent Activity Tracking

**Use Case**: See which files were recently modified/indexed.

**Query**: Sort by `date_indexed_dt` field.

**Example Output**:
```
Most recently indexed source files:
  1. solr_mcp/solr/vector/manager.py
  2. solr_mcp/solr/vector/__init__.py
  3. solr_mcp/solr/query/executor.py
```

**Why It's Useful**: Tracks active development areas and recent changes.

## 9. Metadata-Based Search

**Use Case**: Find files by category, tags, or other metadata.

**Examples**:

```bash
# Find all tool implementations
q="category_ss:tools AND tags_ss:py"

# Find all configuration files
q="category_ss:configuration"

# Find all vector-related code
q="category_ss:vector"
```

**Why It's Useful**: Quickly navigate to specific types of files without knowing exact paths.

## 10. Semantic Code Search (with Vector Embeddings)

**Use Case**: Find code by meaning, not just keywords.

**Example**: Search for "handling errors and exceptions from network requests" to find relevant error handling code, even if it doesn't use those exact words.

**How It Works**:
1. Converts your query to a 768D vector embedding
2. Uses KNN (K-Nearest Neighbors) to find semantically similar code
3. Returns files that solve similar problems

**Why It's Useful**: Discover code examples and patterns without knowing exact terminology.

## 11. Hybrid Search (Keyword + Semantic)

**Use Case**: Combine exact keyword matching with semantic similarity.

**Example**: Find files that mention "solr" AND are semantically similar to "database query execution".

**Why It's Useful**: Get the precision of keyword search with the recall of semantic search.

## 12. Code Statistics & Analytics

**Use Case**: Generate project-wide statistics.

**What You Can Measure**:
- Lines of code (total, per category, per file type)
- File count by category
- Code-to-test ratio
- Documentation coverage percentage
- Exception handling coverage

**Example Query**:
```bash
uv run python scripts/count_python_loc.py
```

## Additional Ideas for Exploration

### Code Quality Metrics
- Find files with very high cyclomatic complexity
- Detect duplicate code using vector similarity
- Find unused imports or dead code

### Architecture Analysis
- Build call graphs from function definitions and calls
- Create module dependency graphs
- Identify orphaned files (not imported anywhere)

### Knowledge Management
- Build a code example search engine
- Find similar bug fixes across the codebase
- Discover alternative implementations of similar functionality

### Refactoring Assistance
- Find outdated patterns or deprecated API usage
- Identify code that violates style guidelines
- Suggest similar files for consistency

### Development Insights
- Track code churn (files that change frequently)
- Find "hotspot" files that have many dependencies
- Identify areas of technical debt accumulation

## Real-World Applications

### 1. Onboarding New Developers
**Query**: "Show me examples of error handling in API calls"

Uses semantic search to find relevant code examples without knowing exact function names.

### 2. Refactoring Planning
**Queries**:
- Find all files > 500 lines
- Find functions > 100 lines
- Find files with >10 TODO markers

Helps prioritize refactoring work.

### 3. Code Review Preparation
**Queries**:
- Recently modified files
- Files missing tests
- Files with exception handling changes

Helps reviewers focus on important areas.

### 4. Technical Debt Management
**Dashboard**:
- Total TODO/FIXME count
- Files with most debt
- Long functions requiring refactoring
- Missing documentation

Provides quantifiable metrics for technical debt.

### 5. Architecture Evolution
**Queries**:
- Module dependency analysis
- Find tightly coupled components
- Identify potential service boundaries

Helps with microservices extraction or modularization.

## Performance Considerations

- **Indexing Speed**: Initial indexing with embeddings takes ~1-2 minutes for 150 files
- **Search Speed**: Text queries return in milliseconds
- **Vector Search**: Semantic queries take 100-500ms depending on embedding generation
- **Collection Size**: 150 files = ~150 documents, ~10MB in Solr

## Extending the System

### Add More Metadata
Modify `scripts/index_codebase.py` to extract:
- Function signatures
- Class hierarchies
- Import statements as separate fields
- Git commit history
- Code metrics (cyclomatic complexity, etc.)

### Custom Categories
Add your own categorization logic:
- By team ownership
- By feature area
- By technical stack
- By risk/criticality

### Integration with Dev Tools
- CI/CD pipeline integration for automated analysis
- Git hooks for pre-commit analysis
- IDE plugins for in-editor search
- Slack/Teams bots for code discovery

## Conclusion

By indexing your codebase into Solr with solr-mcp, you transform your code from a simple file tree into a queryable, analyzable knowledge base. This enables:

1. **Better Code Discovery**: Find examples and patterns quickly
2. **Quality Metrics**: Track code quality over time
3. **Refactoring Insights**: Identify areas needing improvement
4. **Knowledge Sharing**: Help teams learn from existing code
5. **Architecture Understanding**: Visualize dependencies and relationships

The combination of full-text search, faceting, and vector embeddings makes this a powerful tool for understanding and improving your codebase.

## Scripts Reference

- `scripts/index_codebase.py` - Index codebase into Solr
- `scripts/clever_codebase_queries.py` - Run various analytical queries
- `scripts/tech_debt_tracker.py` - Track technical debt markers
- `scripts/count_python_loc.py` - Count lines of code
- `scripts/query_python_files.py` - Query for Python files

All scripts are located in the `scripts/` directory and can be run with `uv run python scripts/<script_name>.py`.
