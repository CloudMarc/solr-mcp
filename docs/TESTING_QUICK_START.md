# 🚀 Testing Quick Start Guide

## TL;DR - Run All Tests Now

```bash
# Run everything
./scripts/run_full_integration_tests.sh

# If all passes, test with Claude Desktop
./scripts/setup_claude_desktop.sh
```

That's it! Everything is automated. 🎉

---

## Manual Testing Steps

### 1. Docker Integration Tests (5 minutes)

```bash
# Start Solr
docker-compose up -d

# Run tests
uv run pytest tests/integration/ -v

# Stop Solr
docker-compose down -v
```

### 2. MCP Inspector Testing (10 minutes)

```bash
# Terminal 1: Start Solr
docker-compose up -d

# Terminal 2: Open MCP Inspector
npx @modelcontextprotocol/inspector uv run solr-mcp

# Opens browser at http://localhost:5173
# Test each tool interactively
```

### 3. Claude Desktop Testing (15 minutes)

```bash
# Auto-configure and start
./scripts/setup_claude_desktop.sh

# Then:
# 1. Quit Claude Desktop (Cmd+Q)
# 2. Restart Claude Desktop
# 3. Look for 🔌 icon
# 4. Chat: "Can you list the Solr collections?"
```

---

## Test Coverage by Area

| Area | Test Type | Command | Time |
|------|-----------|---------|------|
| **Unit Tests** | Automated | `pytest tests/unit/` | 30s |
| **Integration** | Automated | `pytest tests/integration/` | 2m |
| **MCP Protocol** | Automated | `pytest tests/e2e/` | 1m |
| **MCP Inspector** | Manual | See above | 10m |
| **Claude Desktop** | Manual | See above | 15m |
| **Code Quality** | Automated | `make check` | 30s |

**Total: ~30 minutes for complete testing**

---

## What Each Test Validates

### Unit Tests (526 tests)
✅ Individual function behavior  
✅ Error handling  
✅ Type safety  
✅ Edge cases  

### Integration Tests (6 tests)
✅ Real Solr connectivity  
✅ Document indexing  
✅ Query execution  
✅ Schema operations  

### E2E MCP Tests (8 tests)
✅ MCP protocol compliance  
✅ JSON-RPC format  
✅ Tool discovery  
✅ Error responses  

### MCP Inspector
✅ Interactive tool testing  
✅ Real-time debugging  
✅ Request/response inspection  

### Claude Desktop
✅ Real AI assistant integration  
✅ Multi-tool workflows  
✅ User experience  
✅ Error messages clarity  

---

## Quick Troubleshooting

### Tests Failing?

```bash
# Check Solr is running
curl http://localhost:8983/solr/admin/info/system

# Check logs
docker-compose logs

# Clean restart
docker-compose down -v
docker-compose up -d
```

### Claude Desktop Not Working?

```bash
# View config
cat ~/Library/Application\ Support/Claude/claude_desktop_config.json

# View logs
tail -f ~/Library/Logs/Claude/mcp*.log

# Reconfigure
./scripts/setup_claude_desktop.sh
```

### MCP Inspector Won't Connect?

```bash
# Check if server starts
uv run solr-mcp

# Check Node.js version
node --version  # Should be 18+

# Try again
npx @modelcontextprotocol/inspector uv run solr-mcp
```

---

## Success Criteria

Before submitting PR, verify:

- [ ] `./scripts/run_full_integration_tests.sh` exits with 0
- [ ] All tools work in MCP Inspector
- [ ] Can chat with Claude Desktop using Solr tools
- [ ] No errors in Claude Desktop logs
- [ ] Coverage > 60%
- [ ] `make check` passes

---

## For the Impatient

```bash
# One command to rule them all
./scripts/run_full_integration_tests.sh && \
./scripts/setup_claude_desktop.sh && \
echo "✅ Ready to submit PR!"
```

Then test in Claude Desktop and you're done! 🚀

---

## Need More Details?

See: [COMPREHENSIVE_INTEGRATION_TESTING.md](./COMPREHENSIVE_INTEGRATION_TESTING.md)
