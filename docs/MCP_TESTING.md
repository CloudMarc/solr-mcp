# 🤖 Testing solr-mcp with Claude Desktop

## What is This?

This guide shows you how to test your solr-mcp server with **Claude Desktop**, the real AI assistant that will use your MCP server.

## Why Test with Claude Desktop?

1. **Real-world validation** - See how actual users will interact with your tools
2. **User experience testing** - Verify error messages are helpful
3. **Multi-tool workflows** - Test complex scenarios that chain multiple tools
4. **Integration testing** - Ensure everything works end-to-end

---

## Quick Setup (5 minutes)

### Option 1: Automated Setup (Recommended)

```bash
cd /Users/marcbyrd/Documents/Github/solr-mcp
./scripts/setup_claude_desktop.sh
```

This script will:
1. ✅ Check prerequisites (Claude Desktop, Docker, uv)
2. ✅ Start Solr cluster
3. ✅ Create test collection
4. ✅ Configure Claude Desktop
5. ✅ Test MCP server startup

Then:
1. **Fully quit Claude Desktop** (Cmd+Q)
2. **Restart Claude Desktop**
3. Look for the **🔌 icon** in the bottom right
4. Start chatting!

### Option 2: Manual Setup

**Step 1: Install Claude Desktop**
```bash
# Download from https://claude.ai/download
# Or use Homebrew:
brew install --cask claude
```

**Step 2: Configure Claude Desktop**

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

**Step 3: Start Solr**
```bash
cd /Users/marcbyrd/Documents/Github/solr-mcp
docker compose up -d
```

**Step 4: Restart Claude Desktop**
- Fully quit (Cmd+Q, not just close window)
- Restart
- Look for 🔌 icon

---

## Test Scenarios

### Scenario 1: Basic Query ✨

**What to say to Claude:**
```
Can you query the Solr index for documents?
```

**Expected behavior:**
- Claude recognizes this requires the `solr_query` tool
- Asks you what to search for (or uses `*:*` for all docs)
- Executes the query
- Formats and presents the results

**Success criteria:**
- ✅ Query executes without errors
- ✅ Results are displayed clearly
- ✅ Claude explains what was found

---

### Scenario 2: Collection Discovery 📚

**What to say to Claude:**
```
What Solr collections are available?
```

**Expected behavior:**
- Claude uses `solr_list_collections` tool
- Displays the list of collections
- Might offer to explore them further

**Success criteria:**
- ✅ Collections listed correctly
- ✅ "test_collection" is present
- ✅ Clear, formatted output

---

### Scenario 3: Schema Exploration 🔍

**What to say to Claude:**
```
What fields are in the test_collection schema?
```

**Expected behavior:**
- Claude uses `solr_list_fields` or `solr_get_schema_fields`
- Shows field names and types
- Explains what each field might be used for

**Success criteria:**
- ✅ All fields displayed
- ✅ Field types shown
- ✅ Indexed/stored properties visible

---

### Scenario 4: Document Indexing ✍️

**What to say to Claude:**
```
Index this document in test_collection:
{
  "id": "test_001",
  "title": "Testing solr-mcp",
  "content": "This is a test document for Claude Desktop integration",
  "author": "Marc"
}
```

**Expected behavior:**
- Claude uses `solr_add_documents` tool
- Confirms successful indexing
- Might suggest querying to verify

**Success criteria:**
- ✅ Document indexed successfully
- ✅ Confirmation message displayed
- ✅ No errors

---

### Scenario 5: Multi-Tool Workflow 🔄

**What to say to Claude:**
```
1. Show me what collections exist
2. Pick one and show its schema
3. Index a test document
4. Query to verify it was indexed
```

**Expected behavior:**
- Claude executes tools in sequence
- Each step builds on the previous
- Final verification confirms success

**Success criteria:**
- ✅ All steps execute in order
- ✅ Context maintained between steps
- ✅ Final verification successful

---

### Scenario 6: Error Handling 🛡️

**What to say to Claude:**
```
Query a collection called "nonexistent_collection"
```

**Expected behavior:**
- Tool returns an error
- Claude explains the error clearly
- Suggests what went wrong
- Might offer alternatives

**Success criteria:**
- ✅ Error caught gracefully
- ✅ Human-readable explanation
- ✅ No crash or confusion
- ✅ Helpful suggestions provided

---

### Scenario 7: Complex Query 🎯

**What to say to Claude:**
```
Search for documents where:
- title contains "test"
- content has "integration"
- Sort by relevance
- Show me the top 5 results
```

**Expected behavior:**
- Claude translates natural language to Solr query
- Uses proper Solr syntax
- Returns formatted results
- Explains the query logic

**Success criteria:**
- ✅ Correct query syntax generated
- ✅ Results match criteria
- ✅ Proper sorting applied
- ✅ Limited to 5 results

---

### Scenario 8: Statistics & Analytics 📊

**What to say to Claude:**
```
Give me statistics about the content field in test_collection
```

**Expected behavior:**
- Claude uses `solr_stats` tool
- Shows min/max/avg/count
- Presents data clearly
- Might visualize if possible

**Success criteria:**
- ✅ Stats calculated correctly
- ✅ All metrics displayed
- ✅ Easy to understand format

---

### Scenario 9: Term Analysis 🔤

**What to say to Claude:**
```
Show me the top terms in the title field
```

**Expected behavior:**
- Claude uses `solr_terms` tool
- Lists most common terms
- Shows term frequencies
- Explains what this tells us

**Success criteria:**
- ✅ Terms listed correctly
- ✅ Frequencies accurate
- ✅ Useful insights provided

---

### Scenario 10: Index Statistics 📈

**What to say to Claude:**
```
What's the index status for test_collection?
```

**Expected behavior:**
- Claude uses `solr_luke` tool
- Shows document count
- Shows field information
- Presents index health metrics

**Success criteria:**
- ✅ Document count accurate
- ✅ Field details complete
- ✅ No errors or warnings

---

## How to Verify Success

### Look for the 🔌 Icon

In Claude Desktop's interface (bottom right):
- **Green 🔌** = MCP server connected successfully
- **Red ⚠️** = Connection problem

### Check Claude's Responses

Good signs:
- ✅ Claude mentions "using the solr tool"
- ✅ Results appear quickly
- ✅ Data is formatted nicely
- ✅ Errors are explained clearly

Bad signs:
- ❌ "I don't have access to Solr"
- ❌ Long delays or timeouts
- ❌ Confusing error messages
- ❌ Claude can't see the tools

---

## Troubleshooting

### Tools Don't Appear

**Check the config file:**
```bash
cat ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

**Verify it matches the template above.**

**Solution:**
```bash
# Reconfigure
./scripts/setup_claude_desktop.sh

# Or manually edit and restart Claude
```

### "Connection Failed" Errors

**Check if Solr is running:**
```bash
curl http://localhost:8983/solr/admin/info/system
```

**Check if MCP server starts:**
```bash
uv run solr-mcp
# Should start without errors
```

**Solution:**
```bash
# Restart Solr
docker compose restart

# Restart Claude Desktop (fully quit and reopen)
```

### Tools Appear But Don't Work

**Check Claude Desktop logs:**
```bash
tail -f ~/Library/Logs/Claude/mcp*.log
```

**Look for errors like:**
- Connection refused
- Timeout errors
- Authentication issues

**Solution:**
```bash
# Check Solr accessibility
curl http://localhost:8983/solr/admin/collections?action=LIST

# Check MCP server logs
uv run solr-mcp --log-level debug
```

### Slow Responses

**Possible causes:**
- Solr is indexing large amounts of data
- Query is complex
- Network latency

**Solution:**
```bash
# Check Solr performance
curl 'http://localhost:8983/solr/admin/metrics?group=all'

# Restart Solr if needed
docker compose restart solr1 solr2
```

---

## View Logs

### Claude Desktop Logs
```bash
# Main logs
tail -f ~/Library/Logs/Claude/main.log

# MCP-specific logs
tail -f ~/Library/Logs/Claude/mcp*.log
```

### MCP Server Logs
```bash
# Run server with debug logging
uv run solr-mcp --log-level debug
```

### Solr Logs
```bash
# View Solr logs
docker compose logs -f solr1

# Or both nodes
docker compose logs -f solr1 solr2
```

---

## Testing Checklist

Before considering testing complete:

- [ ] **Connection** - 🔌 icon shows green in Claude Desktop
- [ ] **Discovery** - Claude can list collections and fields
- [ ] **Querying** - Can search and get results
- [ ] **Indexing** - Can add documents
- [ ] **Deletion** - Can delete documents
- [ ] **Schema** - Can inspect and modify schema
- [ ] **Statistics** - Can get stats and analytics
- [ ] **Multi-tool** - Can execute workflows with multiple tools
- [ ] **Error Handling** - Errors are caught and explained
- [ ] **Performance** - Responses are reasonably fast (<5s)

---

## Advanced Testing

### Test with Different Collections

```bash
# Create another collection
curl "http://localhost:8983/solr/admin/collections?action=CREATE&name=products&numShards=1&replicationFactor=1"

# Then ask Claude:
"Switch to the products collection and show me its schema"
```

### Test with Large Datasets

```bash
# Index 1000 documents
# Then ask Claude:
"Search through all documents and find ones about [topic]"
```

### Test Error Recovery

```bash
# Stop Solr
docker compose stop solr1 solr2

# Ask Claude to query
# Then restart and try again
docker compose start solr1 solr2
```

---

## Success Metrics

After testing, you should be able to say:

1. ✅ **It works!** - All tools are accessible and functional
2. ✅ **It's fast** - Responses come back quickly
3. ✅ **It's reliable** - Errors are rare and well-handled
4. ✅ **It's intuitive** - Claude understands what to do
5. ✅ **It's helpful** - Users can accomplish real tasks

If you can check all these boxes, **your MCP server is ready for production!** 🎉

---

## Next Steps

Once Claude Desktop testing is successful:

1. **Document** your testing results
2. **Screenshot** Claude Desktop using your tools
3. **Add examples** to your README
4. **Submit your PR** with confidence!

---

## Resources

- [Claude Desktop Download](https://claude.ai/download)
- [MCP Documentation](https://modelcontextprotocol.io/)
- [solr-mcp README](./README.md)
- [Troubleshooting Guide](./COMPREHENSIVE_INTEGRATION_TESTING.md)
