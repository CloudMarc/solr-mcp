# Comparison: Local solr-mcp vs Apache solr-mcp

## Summary

These are **completely different projects** with the same name:

| Aspect | Local (CloudMarc/allenday fork) | Apache Official |
|--------|--------------------------------|-----------------|
| **Language** | Python | Java (Spring Boot) |
| **Framework** | FastMCP, pysolr | Spring AI |
| **Origin** | Fork of allenday/solr-mcp | Apache incubating project |
| **Build System** | uv, pyproject.toml | Gradle |
| **License** | MIT | Apache 2.0 |
| **Maturity** | ~540 tests, 66% coverage | Incubating status |

---

## Detailed Comparison

### 1. **Implementation Language & Stack**

**Local Repository (Python)**
- Language: Python 3.10+
- Framework: FastMCP, MCP SDK
- Dependencies: pysolr, httpx, pydantic, numpy, markdown
- Package Manager: uv (modern Python package manager)
- Server: FastAPI/Uvicorn for HTTP mode, STDIO for Claude Desktop

**Apache Repository (Java)**
- Language: Java 25+
- Framework: Spring Boot 3.5.7, Spring AI 1.1.0 GA
- Build System: Gradle with Kotlin DSL
- Container: Docker images built with Jib
- Server: Spring Boot with STDIO and HTTP transports

### 2. **Features & Capabilities**

**Local Python Version Features:**
- ✅ Hybrid search (keyword + vector)
- ✅ Vector embeddings via Ollama (nomic-embed-text)
- ✅ SQL query support (solr_select, solr_vector_select, solr_semantic_select)
- ✅ Highlighting with configurable snippets
- ✅ Stats component (min, max, mean, sum, stddev)
- ✅ Terms component (autocomplete, vocabulary exploration)
- ✅ Schema API (add, list, get, delete fields)
- ✅ Advanced indexing (atomic updates, optimistic concurrency)
- ✅ Real-time get (retrieve uncommitted documents)
- ✅ Soft/hard commits
- ✅ ZooKeeper integration (Kazoo)
- ✅ Comprehensive testing (540+ tests, integration with Docker)

**Apache Java Version Features:**
- ✅ Search with filtering, faceting, pagination
- ✅ Index documents (JSON, CSV, XML)
- ✅ Collection management
- ✅ Schema inspection
- ✅ STDIO and HTTP transports
- ✅ Docker support with Jib
- ✅ Testcontainers integration
- ⚠️ Less emphasis on vector search (may be present but not highlighted)
- ⚠️ Fewer advanced Solr features documented

### 3. **MCP Tools Available**

**Local Python Version:**
```
Query Tools:
- solr_select (SQL queries)
- solr_query (standard queries + highlighting + stats)
- solr_vector_select (SQL + vector similarity)
- solr_semantic_select (SQL + semantic similarity)
- solr_terms (term exploration)

Schema Management:
- solr_schema_add_field
- solr_schema_list_fields
- solr_schema_get_field
- solr_schema_delete_field

Collection Management:
- solr_list_collections
- solr_list_fields

Indexing:
- solr_add_documents
- solr_delete_documents
- solr_commit
- solr_atomic_update
- solr_realtime_get
```

**Apache Java Version:**
```
- search
- index_documents
- listCollections
- getCollectionStats
- checkHealth
- getSchema
```

### 4. **Architecture & Design**

**Local Python Version:**
- Vector search optimization: SQL filters pushed to vector search stage
- Unified collections (document + embeddings in same collection)
- Emphasis on hybrid search and semantic capabilities
- Extensive testing infrastructure (unit, integration, E2E)
- Makefile-driven workflows

**Apache Java Version:**
- Spring AI integration
- Focus on standard MCP operations
- Docker-first deployment
- Gradle-based build system
- CI/CD with GitHub Actions

### 5. **Documentation & Community**

**Local Python Version:**
- Detailed documentation: README, QUICKSTART, TESTING docs
- 540+ automated tests
- CLAUDE.md for AI context
- Makefile for easy setup (`make full-setup`)
- Fork of allenday/solr-mcp
- Active development (recent commits)

**Apache Java Version:**
- Official Apache incubating project
- Comprehensive docs: ARCHITECTURE, DEVELOPMENT, DEPLOYMENT, TROUBLESHOOTING
- GitHub Issues & Discussions
- Official Docker images: `ghcr.io/apache/solr-mcp:latest`
- Community support via Apache channels

### 6. **Installation & Setup**

**Local Python Version:**
```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Complete setup
make full-setup

# Start server
make server
```

**Apache Java Version:**
```bash
# Build with Gradle
./gradlew build

# Run JAR
java -jar build/libs/solr-mcp-0.0.1-SNAPSHOT.jar

# Or Docker
docker run -i --rm ghcr.io/apache/solr-mcp:latest
```

### 7. **Testing**

**Local Python Version:**
- 540+ automated tests
- 66%+ code coverage
- mypy type safety
- pytest, pytest-asyncio, pytest-cov
- Full integration tests with Docker Solr
- MCP protocol compliance tests

**Apache Java Version:**
- Java-based testing (JUnit likely)
- Testcontainers for integration
- Spring Boot test framework
- (Specific metrics not documented in README)

---

## Key Differences

### What Makes Local Version Unique:
1. **Python ecosystem** - easier for Python developers
2. **Advanced vector search** - semantic search, hybrid queries
3. **SQL query support** - solr_select, vector_select, semantic_select
4. **Extensive testing** - 540+ tests with high coverage
5. **Developer tools** - Makefile, uv, comprehensive test suite
6. **Advanced Solr features** - highlighting, stats, terms, atomic updates

### What Makes Apache Version Unique:
1. **Official Apache project** - governance, community, stability
2. **Java/Spring ecosystem** - enterprise Java stack
3. **Jib Docker images** - optimized containerization
4. **Spring AI integration** - leverages Spring AI capabilities
5. **Apache 2.0 license** - vs MIT license locally
6. **Incubating status** - on path to Apache TLP

---

## Recommendations

### Use Local Python Version If:
- You prefer Python development
- You need advanced vector/semantic search
- You want SQL-based querying
- You need extensive testing infrastructure
- You're building hybrid search applications
- You want to contribute to Python MCP ecosystem

### Use Apache Java Version If:
- You prefer Java/Spring development
- You want official Apache support
- You need enterprise Java ecosystem
- You want long-term Apache community backing
- You prefer Gradle build system
- You're already using Spring AI

---

## Migration Path

If you wanted to align with Apache's approach:
1. These are fundamentally different codebases (Python vs Java)
2. No direct migration path exists
3. Could contribute Python features as separate project
4. Could propose Python version as Apache incubating project
5. Or maintain as independent Python alternative

---

## Conclusion

The local repository is a **feature-rich Python implementation** with advanced vector search, extensive testing, and developer-friendly tooling. The Apache repository is an **official Java/Spring Boot implementation** with enterprise backing and Spring AI integration.

They serve different ecosystems and use cases. The local version excels at hybrid search and has more documented Solr features, while the Apache version provides official community support and enterprise Java integration.
