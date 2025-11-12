# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial project structure
- MCP server implementation
- Solr client with search, vector search, and hybrid search capabilities
- Embedding generation via Ollama using nomic-embed-text
- Docker configuration for SolrCloud and ZooKeeper
- Demo scripts and utilities for testing
- Bitcoin whitepaper as sample document
- Documentation (README, QUICKSTART, CONTRIBUTING)
- **New Feature: Highlighting Support** - `solr_query` tool now supports highlighting matched terms with configurable snippets, fragment size, and methods (unified, original, fastVector)
- **New Feature: Stats Component** - Compute statistical aggregations (min, max, mean, sum, stddev) on numeric fields via `solr_query` tool
- **New Tool: solr_terms** - Explore indexed terms with prefix/regex filtering for autocomplete and vocabulary exploration
- **New Tool: solr_schema_add_field** - Dynamically add new fields to collection schemas
- **New Tool: solr_schema_list_fields** - List all fields in a collection schema with full details
- **New Tool: solr_schema_get_field** - Get detailed information about a specific schema field
- **New Tool: solr_schema_delete_field** - Remove fields from collection schemas
- **New Client Methods**: `execute_query`, `get_terms`, `add_schema_field`, `get_schema_fields`, `get_schema_field`, `delete_schema_field`
- Comprehensive test coverage for all new features (34 new tests, 503 total tests passing)

### Fixed
- Improved search query transformation for better results
- Fixed phrase proximity searches with `~5` operator
- Proper field naming for Solr compatibility
- Enhanced text analysis for hyphenated terms like "double-spending"
- Improved synonym handling in Solr configuration
- Fixed vector search configuration to use built-in capabilities
- Improved error handling in Ollama embedding client with retries
- Added proper timeout and fallback mechanisms for embedding generation
- Fixed Solr schema URL paths in client implementation
- Enhanced Docker healthcheck for Ollama service

### Changed
- Migrated from FastMCP to MCP 1.4.1

## [0.1.0] - 2024-03-17
### Added
- Initial release
- MCP server implementation
- Integration with SolrCloud
- Support for basic search operations
- Vector search capabilities
- Hybrid search functionality
- Embedding generation and indexing