# Solr MCP

A Python package for accessing Apache Solr indexes via Model Context Protocol (MCP). This integration allows AI assistants like Claude to perform powerful search queries against your Solr indexes, combining both keyword and vector search capabilities.

## Features

- **MCP Server**: Implements the Model Context Protocol for integration with AI assistants
- **Hybrid Search**: Combines keyword search precision with vector search semantic understanding
- **Vector Embeddings**: Generates embeddings for documents using Ollama with nomic-embed-text
- **Unified Collections**: Store both document content and vector embeddings in the same collection
- **Docker Integration**: Easy setup with Docker and docker-compose
- **Optimized Vector Search**: Efficiently handles combined vector and SQL queries by pushing down SQL filters to the vector search stage, ensuring optimal performance even with large result sets and pagination
- **Highlighting**: Show WHY documents matched with highlighted snippets of matched terms
- **Stats Component**: Compute statistical aggregations (min, max, mean, sum, stddev) on numeric fields
- **Terms Component**: Explore indexed terms for autocomplete, vocabulary exploration, and query expansion
- **Schema API**: Dynamically add, list, get, and delete fields from collection schemas

## Architecture

### Vector Search Optimization

The system employs an important optimization for combined vector and SQL queries. When executing a query that includes both vector similarity search and SQL filters:

1. SQL filters (WHERE clauses) are pushed down to the vector search stage
2. This ensures that vector similarity calculations are only performed on documents that will match the final SQL criteria
3. Significantly improves performance for queries with:
   - Selective WHERE clauses
   - Pagination (LIMIT/OFFSET)
   - Large result sets

This optimization reduces computational overhead and network transfer by minimizing the number of vector similarity calculations needed.

## Quick Start

### Using Makefile (Recommended)

The easiest way to get started:

```bash
# Complete setup in one command
make full-setup

# Start the MCP server
make server
```

See [MAKEFILE.md](MAKEFILE.md) for all available commands.

### Manual Setup

1. Clone this repository
2. Install uv (fast Python package manager):
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```
3. Start SolrCloud with Docker:
   ```bash
   docker-compose up -d
   ```
4. Install dependencies:
   ```bash
   uv sync --extra test
   ```
5. Process and index the sample document:
   ```bash
   uv run python scripts/process_markdown.py data/bitcoin-whitepaper.md --output data/processed/bitcoin_sections.json
   uv run python scripts/create_unified_collection.py unified
   uv run python scripts/unified_index.py data/processed/bitcoin_sections.json --collection unified
   ```
6. Run the MCP server:
   ```bash
   uv run solr-mcp
   ```

For more detailed setup and usage instructions, see the [QUICKSTART.md](QUICKSTART.md) guide.

## Available Tools

### Query Tools

- **solr_select**: Execute SQL queries against Solr collections
- **solr_query**: Standard Solr queries with highlighting and stats support
- **solr_vector_select**: SQL queries filtered by vector similarity
- **solr_semantic_select**: SQL queries filtered by semantic similarity (text → vector)
- **solr_terms**: Explore indexed terms with prefix/regex filtering

### Schema Management

- **solr_schema_add_field**: Add new fields to collection schemas
- **solr_schema_list_fields**: List all fields in a schema
- **solr_schema_get_field**: Get details of a specific field
- **solr_schema_delete_field**: Remove fields from schemas

### Collection Management

- **solr_list_collections**: List all available Solr collections
- **solr_list_fields**: List fields with copyField relationships

### Indexing Tools

- **solr_add_documents**: Add or update documents in a collection
- **solr_delete_documents**: Delete documents by ID or query
- **solr_commit**: Commit pending changes to a collection (supports soft/hard commits)
- **solr_atomic_update**: Atomically update specific fields without reindexing entire documents
- **solr_realtime_get**: Get documents in real-time, including uncommitted changes

### Highlighting & Stats

The `solr_query` tool supports:
- **Highlighting**: Show matched terms in context with configurable snippet size and count
- **Stats Component**: Compute min, max, mean, sum, stddev on numeric fields
- Combine both features in a single query for rich search results

### Advanced Indexing Features

- **Atomic Updates**: Update specific fields without reindexing entire documents (set, inc, add, remove operations)
- **Optimistic Concurrency**: Version-based locking with `_version_` field to prevent concurrent update conflicts
- **Soft vs Hard Commits**: Choose between fast visibility (soft) or durability (hard) for your use case
- **Real-Time Get**: Retrieve documents immediately, even before commit, for near real-time applications

## Requirements

- Python 3.10 or higher
- [uv](https://github.com/astral-sh/uv) (fast Python package manager)
- Docker and Docker Compose
- SolrCloud 9.x
- Ollama (for embedding generation)

## Installation

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
make install
# or
uv sync --extra test
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Testing

This project includes comprehensive test coverage:

- **540+ automated tests** (unit, integration, and E2E)
- **66%+ code coverage** with mypy type safety
- **Full integration tests** with Docker-based Solr cluster
- **MCP protocol compliance** tests

See [docs/TESTING.md](docs/TESTING.md) for complete testing documentation, including:
- Quick start guide: [docs/TESTING_QUICK_START.md](docs/TESTING_QUICK_START.md)
- Integration testing: [docs/INTEGRATION_TESTING.md](docs/INTEGRATION_TESTING.md)
- Claude Desktop testing: [docs/MCP_TESTING.md](docs/MCP_TESTING.md)

To run all tests:
```bash
./scripts/run_full_integration_tests.sh
```

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.