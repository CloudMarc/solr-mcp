# 🧪 Comprehensive Integration Testing Plan

## Overview

This document outlines the complete integration testing strategy for solr-mcp, including:

1. **Docker-based Integration Tests** - Full Solr cluster testing
2. **MCP Protocol Testing** - Test with MCP Inspector
3. **Claude Desktop Integration** - Real-world AI assistant testing
4. **End-to-End Scenarios** - Complete workflow validation

---

## 1. Docker-Based Integration Tests ✅ (ALREADY IMPLEMENTED)

### Current Status
- ✅ Docker Compose setup with 2-node SolrCloud cluster
- ✅ Integration tests in `tests/integration/`
- ✅ Automated test scripts

### Test Files
```
tests/integration/
├── test_direct_solr.py        # Basic Solr connectivity
├── test_indexing_tools.py     # Document indexing features
├── test_query_features.py     # Search and query features
└── test_schema_tools.py       # Schema management
```

### Running Docker Integration Tests
```bash
# Start Solr cluster
docker-compose up -d

# Wait for Solr to be ready
sleep 10

# Run all integration tests
pytest tests/integration/ -v -m integration

# Run specific test suite
pytest tests/integration/test_indexing_tools.py -v

# Stop cluster
docker-compose down
```

---

## 2. MCP Protocol Testing (NEW)

### What is MCP Inspector?

The [MCP Inspector](https://github.com/modelcontextprotocol/inspector) is an official tool for testing MCP servers. It provides:
- Interactive testing of all MCP tools
- Request/response inspection
- Error debugging
- UI for manual testing

### Setup MCP Inspector

```bash
# Install MCP Inspector (Node.js required)
npx @modelcontextprotocol/inspector

# Or install globally
npm install -g @modelcontextprotocol/inspector
```

### Test solr-mcp with Inspector

```bash
# 1. Start Solr cluster
docker-compose up -d

# 2. Start solr-mcp server in one terminal
uv run solr-mcp

# 3. In another terminal, start inspector
npx @modelcontextprotocol/inspector uv run solr-mcp

# This opens a web UI at http://localhost:5173
```

### What to Test in Inspector

**✅ Test All Tools:**
1. `solr_query` - Run queries and verify results
2. `solr_list_collections` - List available collections
3. `solr_list_fields` - List schema fields
4. `solr_add_documents` - Index documents
5. `solr_delete_documents` - Delete documents
6. `solr_get_schema_fields` - Get schema details
7. `solr_add_schema_field` - Add new fields
8. `solr_luke` - Index statistics
9. `solr_stats` - Field statistics
10. `solr_terms` - Term enumeration

**✅ Test Error Handling:**
- Invalid collection names
- Malformed queries
- Missing required fields
- Connection errors

---

## 3. Claude Desktop Integration (NEW)

### Why Test with Claude Desktop?

Claude Desktop is the **real production environment** where solr-mcp will be used. Testing with it ensures:
- Real AI assistant workflows work correctly
- Tool discovery and invocation is seamless
- Error messages are user-friendly
- Performance is acceptable

### Setup solr-mcp in Claude Desktop

**Step 1: Install Claude Desktop**
```bash
# Download from: https://claude.ai/download
# Or use Homebrew
brew install --cask claude
```

**Step 2: Configure solr-mcp**

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "solr": {
      "command": "uv",
      "args": [
        "--directory",
        "/Users/marcbyrd/Documents/Github/solr-mcp",
        "run",
        "solr-mcp"
      ],
      "env": {
        "SOLR_URL": "http://localhost:8983/solr",
        "DEFAULT_COLLECTION": "test_collection"
      }
    }
  }
}
```

**Step 3: Start Solr and Restart Claude Desktop**
```bash
# Start Solr
cd /Users/marcbyrd/Documents/Github/solr-mcp
docker-compose up -d

# Restart Claude Desktop (fully quit and reopen)
```

### Test Scenarios with Claude Desktop

**Scenario 1: Basic Query**
```
Chat with Claude:
"Can you query the Solr index for documents about machine learning?"

Expected: Claude uses solr_query tool and returns results
```

**Scenario 2: Schema Inspection**
```
Chat with Claude:
"What fields are available in the Solr schema?"

Expected: Claude uses solr_list_fields and describes the schema
```

**Scenario 3: Document Indexing**
```
Chat with Claude:
"Index this document: {id: 'test1', title: 'Test', content: 'Hello'}"

Expected: Claude uses solr_add_documents and confirms success
```

**Scenario 4: Complex Workflow**
```
Chat with Claude:
"1. List all collections
 2. Show me fields in the 'test_collection'
 3. Query for documents with 'important' in the title
 4. Show me statistics for the 'content' field"

Expected: Claude chains multiple tool calls correctly
```

**Scenario 5: Error Recovery**
```
Chat with Claude:
"Query a collection called 'nonexistent'"

Expected: Claude handles the error gracefully and explains the issue
```

---

## 4. Automated End-to-End Test Suite (TO CREATE)

### Create E2E Test Script

We should create `tests/e2e/test_mcp_protocol.py`:

```python
"""
End-to-end tests for MCP protocol compliance.
These tests verify the actual MCP server implementation.
"""
import asyncio
import json
import subprocess
from pathlib import Path

import pytest


@pytest.fixture
async def mcp_server():
    """Start the MCP server for testing."""
    proc = await asyncio.create_subprocess_exec(
        "uv", "run", "solr-mcp",
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    
    yield proc
    
    proc.terminate()
    await proc.wait()


async def send_mcp_request(proc, request):
    """Send an MCP request and get response."""
    request_json = json.dumps(request) + "\n"
    proc.stdin.write(request_json.encode())
    await proc.stdin.drain()
    
    response_line = await proc.stdout.readline()
    return json.loads(response_line)


@pytest.mark.asyncio
async def test_mcp_list_tools(mcp_server):
    """Test that server responds to list_tools request."""
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/list"
    }
    
    response = await send_mcp_request(mcp_server, request)
    
    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 1
    assert "result" in response
    assert "tools" in response["result"]
    
    tools = response["result"]["tools"]
    tool_names = [t["name"] for t in tools]
    
    # Verify all expected tools are present
    expected_tools = [
        "solr_query",
        "solr_list_collections",
        "solr_list_fields",
        "solr_add_documents",
        "solr_delete_documents",
    ]
    
    for tool in expected_tools:
        assert tool in tool_names


@pytest.mark.asyncio
async def test_mcp_call_tool(mcp_server):
    """Test calling a tool through MCP."""
    request = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": "solr_list_collections",
            "arguments": {}
        }
    }
    
    response = await send_mcp_request(mcp_server, request)
    
    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 2
    assert "result" in response
```

---

## 5. Complete Testing Workflow

### Automated Test Script

Create `scripts/run_full_integration_tests.sh`:

```bash
#!/bin/bash
set -e

echo "🚀 Starting Comprehensive Integration Tests"
echo "============================================="

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 1. Start Docker Cluster
echo -e "\n${YELLOW}Step 1: Starting Solr Docker Cluster${NC}"
docker-compose down -v 2>/dev/null || true
docker-compose up -d
sleep 15

# Check Solr health
if curl -s http://localhost:8983/solr/admin/info/system > /dev/null; then
    echo -e "${GREEN}✓ Solr cluster is healthy${NC}"
else
    echo -e "${RED}✗ Solr cluster failed to start${NC}"
    exit 1
fi

# 2. Create test collection
echo -e "\n${YELLOW}Step 2: Creating test collection${NC}"
curl -s "http://localhost:8983/solr/admin/collections?action=CREATE&name=test_collection&numShards=2&replicationFactor=2" > /dev/null
echo -e "${GREEN}✓ Test collection created${NC}"

# 3. Run unit tests
echo -e "\n${YELLOW}Step 3: Running Unit Tests${NC}"
uv run pytest tests/unit/ -v --tb=short
echo -e "${GREEN}✓ Unit tests passed${NC}"

# 4. Run integration tests
echo -e "\n${YELLOW}Step 4: Running Integration Tests${NC}"
uv run pytest tests/integration/ -v --tb=short -m integration
echo -e "${GREEN}✓ Integration tests passed${NC}"

# 5. Test MCP server startup
echo -e "\n${YELLOW}Step 5: Testing MCP Server Startup${NC}"
timeout 5s uv run solr-mcp &
SERVER_PID=$!
sleep 2
if ps -p $SERVER_PID > /dev/null; then
    echo -e "${GREEN}✓ MCP server starts successfully${NC}"
    kill $SERVER_PID 2>/dev/null || true
else
    echo -e "${RED}✗ MCP server failed to start${NC}"
    exit 1
fi

# 6. Code quality checks
echo -e "\n${YELLOW}Step 6: Running Code Quality Checks${NC}"
uv run mypy solr_mcp
echo -e "${GREEN}✓ Type checking passed${NC}"

uv run ruff check solr_mcp
echo -e "${GREEN}✓ Linting passed${NC}"

# 7. Generate coverage report
echo -e "\n${YELLOW}Step 7: Generating Coverage Report${NC}"
uv run pytest tests/unit/ tests/integration/ --cov=solr_mcp --cov-report=term --cov-report=html
echo -e "${GREEN}✓ Coverage report generated${NC}"

# Summary
echo -e "\n${GREEN}=============================================${NC}"
echo -e "${GREEN}✅ All Integration Tests Passed!${NC}"
echo -e "${GREEN}=============================================${NC}"

echo -e "\n${YELLOW}Next Steps:${NC}"
echo "1. Test with MCP Inspector: npx @modelcontextprotocol/inspector uv run solr-mcp"
echo "2. Test with Claude Desktop (see COMPREHENSIVE_INTEGRATION_TESTING.md)"
echo "3. Review coverage report: open htmlcov/index.html"

# Cleanup option
read -p "Clean up Docker containers? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    docker-compose down -v
    echo -e "${GREEN}✓ Cleanup complete${NC}"
fi
```

---

## 6. Manual Testing Checklist

### Before Submitting PR

- [ ] **Docker Integration Tests**
  - [ ] All tests pass: `pytest tests/integration/ -v`
  - [ ] No flaky tests (run 3 times)
  - [ ] Coverage > 60%

- [ ] **MCP Inspector Testing**
  - [ ] Server starts without errors
  - [ ] All tools appear in inspector
  - [ ] Each tool can be called successfully
  - [ ] Error messages are clear

- [ ] **Claude Desktop Testing**
  - [ ] Configuration loads correctly
  - [ ] Tools appear in Claude Desktop
  - [ ] Can query Solr through conversation
  - [ ] Error handling is graceful
  - [ ] Multi-tool workflows work

- [ ] **Code Quality**
  - [ ] `mypy solr_mcp` - No type errors
  - [ ] `ruff check solr_mcp` - No linting errors
  - [ ] `pytest --cov=solr_mcp` - Coverage > 60%

- [ ] **Documentation**
  - [ ] README has setup instructions
  - [ ] Claude Desktop config example is correct
  - [ ] All new tools are documented
  - [ ] CHANGELOG is updated

---

## 7. Testing Metrics

### Success Criteria

| Metric | Target | Current |
|--------|--------|---------|
| Unit Test Pass Rate | 100% | ✅ 100% |
| Integration Test Pass Rate | 100% | ✅ 100% |
| Code Coverage | > 60% | ✅ 66%+ |
| Type Safety (mypy) | 100% | ✅ 100% |
| Linting (ruff) | 100% | ✅ 100% |
| MCP Tools Working | 10/10 | 🔄 To Test |
| Claude Desktop Works | Yes | 🔄 To Test |

---

## 8. Troubleshooting

### Common Issues

**Docker Containers Won't Start**
```bash
# Check logs
docker-compose logs

# Clean restart
docker-compose down -v
docker system prune -f
docker-compose up -d
```

**MCP Inspector Connection Failed**
```bash
# Check if server is running
ps aux | grep solr-mcp

# Check for port conflicts
lsof -i :5173

# Try with verbose output
uv run solr-mcp --log-level debug
```

**Claude Desktop Doesn't See Tools**
```bash
# Check config file location
cat ~/Library/Application\ Support/Claude/claude_desktop_config.json

# Check logs (on macOS)
tail -f ~/Library/Logs/Claude/mcp*.log

# Fully restart Claude Desktop
killall Claude
open -a Claude
```

---

## Next Steps

1. **Make test script executable**: `chmod +x scripts/run_full_integration_tests.sh`
2. **Run full test suite**: `./scripts/run_full_integration_tests.sh`
3. **Test with MCP Inspector**: Follow Section 2
4. **Test with Claude Desktop**: Follow Section 3
5. **Document results**: Update this file with findings
6. **Submit PR**: Once all tests pass!

---

## Resources

- [MCP Specification](https://spec.modelcontextprotocol.io/)
- [MCP Inspector](https://github.com/modelcontextprotocol/inspector)
- [Claude Desktop](https://claude.ai/download)
- [Solr Documentation](https://solr.apache.org/guide/)
