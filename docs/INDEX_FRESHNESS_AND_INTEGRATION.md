# Keeping Solr Index Fresh & Integrating with Claude Code

## The Index Freshness Problem

**Challenge**: Solr's index can become stale as files are modified, added, or deleted.

**Impact**: Search results may not reflect current codebase state.

## Solution Strategies

### Strategy 1: File System Watcher (Recommended for Development)

**How it works**: Monitor file changes in real-time and update Solr index immediately.

```python
#!/usr/bin/env python3
"""
Real-time index updater using file system watcher
"""
import asyncio
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import httpx
from pathlib import Path


class CodebaseWatcher(FileSystemEventHandler):
    """Watch for file changes and update Solr index."""

    def __init__(self, solr_url: str, collection: str):
        self.solr_url = solr_url
        self.collection = collection
        self.update_queue = asyncio.Queue()

    def on_modified(self, event):
        """File was modified."""
        if not event.is_directory and self._should_index(event.src_path):
            asyncio.create_task(self._reindex_file(event.src_path))

    def on_created(self, event):
        """File was created."""
        if not event.is_directory and self._should_index(event.src_path):
            asyncio.create_task(self._reindex_file(event.src_path))

    def on_deleted(self, event):
        """File was deleted."""
        if not event.is_directory:
            asyncio.create_task(self._delete_from_index(event.src_path))

    def _should_index(self, path: str) -> bool:
        """Check if file should be indexed."""
        extensions = {'.py', '.md', '.txt', '.json', '.yaml', '.yml', '.toml'}
        return Path(path).suffix in extensions

    async def _reindex_file(self, path: str):
        """Reindex a single file."""
        try:
            # Read file content
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            # Generate embedding
            async with httpx.AsyncClient(timeout=30.0) as client:
                embed_response = await client.post(
                    "http://localhost:11434/api/embeddings",
                    json={"model": "nomic-embed-text", "prompt": content[:8000]}
                )
                embedding = embed_response.json()["embedding"]

            # Create document
            rel_path = Path(path).relative_to(Path.cwd())
            doc = {
                'id': str(rel_path).replace('/', '_'),
                'source': str(rel_path),
                'title': Path(path).name,
                'content': content,
                'embedding': embedding,
                'vector_model_s': 'nomic-embed-text',
                'dimensions_i': len(embedding)
            }

            # Update in Solr
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(
                    f"{self.solr_url}/{self.collection}/update/json/docs",
                    json=[doc],
                    params={"commit": "true"}
                )

            print(f"✅ Reindexed: {rel_path}")

        except Exception as e:
            print(f"❌ Error reindexing {path}: {e}")

    async def _delete_from_index(self, path: str):
        """Remove file from index."""
        try:
            rel_path = Path(path).relative_to(Path.cwd())
            doc_id = str(rel_path).replace('/', '_')

            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(
                    f"{self.solr_url}/{self.collection}/update",
                    json={"delete": {"id": doc_id}},
                    params={"commit": "true"}
                )

            print(f"🗑️  Deleted from index: {rel_path}")

        except Exception as e:
            print(f"❌ Error deleting {path}: {e}")


def start_watcher(path: str = ".", solr_url: str = "http://localhost:8983/solr",
                  collection: str = "codebase"):
    """Start watching for file changes."""
    event_handler = CodebaseWatcher(solr_url, collection)
    observer = Observer()
    observer.schedule(event_handler, path, recursive=True)
    observer.start()

    print(f"👀 Watching {path} for changes...")
    print(f"📡 Updating Solr collection: {collection}")

    try:
        while True:
            asyncio.sleep(1)
    except KeyboardInterrupt:
        observer.stop()

    observer.join()


if __name__ == '__main__':
    start_watcher()
```

**Pros**:
- ✅ Real-time updates (instant freshness)
- ✅ Minimal overhead
- ✅ No manual intervention

**Cons**:
- ❌ Requires background process
- ❌ Doesn't handle renames well
- ❌ May miss changes if watcher not running

### Strategy 2: Git Hook Integration

**How it works**: Reindex files on git operations (commit, checkout, pull, etc.)

```bash
#!/bin/bash
# .git/hooks/post-commit

# Get changed files from last commit
changed_files=$(git diff-tree --no-commit-id --name-only -r HEAD)

# Reindex each changed file
for file in $changed_files; do
    if [[ -f "$file" ]]; then
        python scripts/reindex_single_file.py "$file"
    fi
done

echo "✅ Solr index updated with committed changes"
```

**Pros**:
- ✅ Automatic on git operations
- ✅ No background process needed
- ✅ Works well with team workflows

**Cons**:
- ❌ Only updates on git operations
- ❌ Doesn't catch unsaved changes
- ❌ Requires hook setup

### Strategy 3: Lazy Reindexing with Staleness Check

**How it works**: Check if file is newer than index before searching, reindex on-demand.

```python
async def smart_search_with_freshness(pattern: str):
    """Search with automatic freshness checking."""

    # Get files matching pattern
    matching_files = await find_matching_files(pattern)

    for file_path in matching_files:
        # Check if file is newer than Solr index
        file_mtime = os.path.getmtime(file_path)

        # Query Solr for this file's index time
        doc = await get_solr_doc(file_path)
        if doc:
            index_time = parse_datetime(doc['date_indexed_dt'])

            # If file is newer, reindex it
            if file_mtime > index_time.timestamp():
                await reindex_file(file_path)

    # Now search with fresh index
    return await solr_search(pattern)
```

**Pros**:
- ✅ Guaranteed fresh results
- ✅ No background process
- ✅ Automatic freshness

**Cons**:
- ❌ Adds latency to first search
- ❌ More complex logic
- ❌ May reindex unnecessarily

### Strategy 4: Periodic Batch Reindexing

**How it works**: Cron job or scheduled task to reindex periodically.

```bash
#!/bin/bash
# Cron: */5 * * * * /path/to/incremental_reindex.sh

# Find files modified in last 10 minutes
find . -name "*.py" -mmin -10 | while read file; do
    python scripts/reindex_single_file.py "$file"
done
```

**Pros**:
- ✅ Simple to set up
- ✅ Predictable resource usage
- ✅ Works for all workflows

**Cons**:
- ❌ Index can be up to N minutes stale
- ❌ May do unnecessary work
- ❌ Requires cron/scheduler

### Strategy 5: Hybrid Approach (Recommended)

**Combine multiple strategies for best results:**

```python
class HybridIndexManager:
    """Manages index freshness using multiple strategies."""

    def __init__(self):
        # Strategy 1: File watcher for real-time updates
        self.watcher = CodebaseWatcher()

        # Strategy 3: Staleness checker for fallback
        self.staleness_checker = StalenessChecker()

        # Track last full reindex
        self.last_full_reindex = None

    async def search(self, pattern: str):
        """Search with automatic freshness management."""

        # Check if watcher is running
        if self.watcher.is_running():
            # Watcher is active, index is fresh
            return await solr_search(pattern)

        # Watcher not running, check staleness
        stale_files = await self.staleness_checker.find_stale_files(pattern)

        if stale_files:
            # Reindex stale files
            await self.reindex_files(stale_files)

        return await solr_search(pattern)

    async def ensure_fresh(self):
        """Ensure index is fresh before search."""

        # Check if we need a full reindex
        if self.needs_full_reindex():
            await self.full_reindex()

        return True

    def needs_full_reindex(self) -> bool:
        """Check if full reindex is needed."""
        if not self.last_full_reindex:
            return True

        # Reindex if more than 1 hour old
        age = time.time() - self.last_full_reindex
        return age > 3600
```

**Pros**:
- ✅ Best of all worlds
- ✅ Handles all scenarios
- ✅ Graceful degradation

**Cons**:
- ❌ More complex
- ❌ More moving parts

## Recommended Implementation

For development environments:

1. **Primary**: File system watcher (Strategy 1)
2. **Backup**: Git hooks (Strategy 2)
3. **Fallback**: Periodic reindex every hour (Strategy 4)

For CI/CD environments:

1. **Full reindex** before tests/deployment
2. **No watcher** needed (one-time index)

## Claude Code Integration Strategies

### Option 1: Teach Claude Code to Use MCP Tools

**Approach**: Claude Code already knows about MCP servers through its configuration.

**How it works**:
1. Configure solr-mcp in Claude Code's MCP settings
2. Claude "learns" the available MCP tools through the protocol
3. Claude chooses when to use MCP tools vs built-in tools

**Configuration**:
```json
// ~/.config/claude-code/mcp.json
{
  "mcpServers": {
    "solr-mcp": {
      "command": "uv",
      "args": ["run", "solr-mcp"],
      "cwd": "/Users/marcbyrd/Documents/Github/solr-mcp"
    }
  }
}
```

**Pros**:
- ✅ No modification to Claude Code needed
- ✅ Claude decides when to use which tool
- ✅ Easy to enable/disable

**Cons**:
- ❌ Claude may not prefer MCP tools over built-ins
- ❌ No guaranteed usage
- ❌ Requires Claude to "learn" when to use MCP

**Reality**: This is how it currently works, but Claude Code may not automatically prefer MCP tools over Glob/Grep.

### Option 2: MCP Tool Preference Hints

**Approach**: Add metadata to MCP tools suggesting when they should be preferred.

**Example**:
```python
@tool(
    name="solr_search_codebase",
    description="Fast codebase search using Solr index",
    preference_hints={
        "faster_than": ["glob", "grep"],
        "use_when": "codebase is indexed",
        "fallback_to": "grep"
    }
)
async def solr_search_codebase(pattern: str):
    """Search codebase using Solr (100x faster than grep)."""
    pass
```

**Pros**:
- ✅ Guides Claude's tool selection
- ✅ No code changes needed
- ✅ Declarative

**Cons**:
- ❌ Requires MCP protocol extension
- ❌ Claude must honor hints
- ❌ Not yet supported

### Option 3: Replace Built-in Tools with MCP Wrappers

**Approach**: Create MCP tools that shadow the built-in Glob/Grep tools.

**Implementation**:
```python
@tool(name="Glob")  # Same name as built-in!
async def solr_backed_glob(pattern: str, path: str = None):
    """
    Find files matching glob pattern.

    Uses Solr index when available (100x faster),
    falls back to filesystem glob.
    """
    # Try Solr first
    try:
        results = await solr_glob_search(pattern, path)
        if results:
            return results
    except SolrUnavailable:
        pass

    # Fall back to traditional glob
    return await filesystem_glob(pattern, path)


@tool(name="Grep")  # Same name as built-in!
async def solr_backed_grep(pattern: str, path: str = None):
    """
    Search file contents for pattern.

    Uses Solr index when available (50x faster),
    falls back to ripgrep/grep.
    """
    # Try Solr first
    try:
        results = await solr_content_search(pattern, path)
        if results:
            return results
    except SolrUnavailable:
        pass

    # Fall back to grep
    return await filesystem_grep(pattern, path)
```

**Pros**:
- ✅ Transparent to Claude Code
- ✅ Guaranteed usage (shadows built-ins)
- ✅ Automatic fallback

**Cons**:
- ❌ May conflict with built-in tools
- ❌ Unclear which tool takes precedence
- ❌ Could be confusing

### Option 4: Smart MCP Proxy Layer

**Approach**: Create an MCP server that intercepts tool calls and routes them appropriately.

```python
class SmartToolRouter:
    """Routes tool calls to fastest implementation."""

    async def route_tool_call(self, tool_name: str, args: dict):
        """Route tool call to best implementation."""

        if tool_name == "Glob":
            # Check if Solr is available and has fresh index
            if await self.is_solr_fresh():
                return await self.solr_glob(**args)
            else:
                return await self.filesystem_glob(**args)

        elif tool_name == "Grep":
            if await self.is_solr_fresh():
                return await self.solr_grep(**args)
            else:
                return await self.ripgrep(**args)

        # Default to original tool
        return await self.call_original_tool(tool_name, args)
```

**Pros**:
- ✅ Intelligent routing
- ✅ Automatic optimization
- ✅ Transparent to user

**Cons**:
- ❌ Complex to implement
- ❌ Requires intercepting MCP protocol
- ❌ May not be possible

## Recommended Approach

### Short-term: Complementary Tools

**Strategy**: Add new MCP tools alongside existing ones.

```python
# New tools that Claude can choose to use
solr_codebase_search()      # Fast content search
solr_file_find()            # Fast file finding
solr_code_stats()           # Instant statistics
solr_semantic_search()      # Vector similarity search
```

**When Claude should use them**:
- Large codebases (>1000 files)
- Complex queries (facets, aggregations)
- Semantic searches
- Statistics/analytics

**When to use built-ins**:
- Small codebases
- Solr not available
- Binary file searches
- File content verification

### Long-term: Auto-Accelerated Tools

**Strategy**: Make Claude Code automatically use Solr when beneficial.

**Possible implementations**:

1. **MCP Server Detection**: Claude Code detects when solr-mcp is available and prefers it
2. **Cost-Based Selection**: Claude chooses tool based on performance characteristics
3. **Hybrid Results**: Combine Solr + traditional tools for best results

## Practical Next Steps

### Step 1: Create File Watcher Service

```bash
# Start the watcher
uv run python scripts/watch_and_index.py &

# Now any file changes are automatically indexed
```

### Step 2: Add Solr-Backed Search Tools to MCP

```python
# solr_mcp/tools/fast_search.py

@mcp_tool()
async def fast_codebase_search(
    pattern: str,
    file_type: str = None,
    use_solr: bool = True
) -> Dict[str, Any]:
    """
    Fast codebase search using Solr index.

    Falls back to grep if Solr unavailable.
    """
    if use_solr:
        try:
            return await solr_search(pattern, file_type)
        except:
            pass

    return await grep_search(pattern, file_type)
```

### Step 3: Configure in Claude Code

```json
{
  "mcpServers": {
    "solr-mcp": {
      "command": "uv",
      "args": ["run", "solr-mcp"],
      "env": {
        "SOLR_URL": "http://localhost:8983/solr",
        "SOLR_COLLECTION": "codebase"
      }
    }
  }
}
```

### Step 4: Let Claude Learn

Claude Code will discover the new tools and start using them when appropriate.

## The Future: Intelligent Tool Selection

**Vision**: Claude Code automatically chooses the best tool for each task.

**Decision matrix**:

| Scenario | Tool Choice | Reason |
|----------|-------------|--------|
| Find 1 file | Glob | Fast enough, no index needed |
| Find 100 files | Solr | Much faster with index |
| Search small repo | Grep | Simple, no setup |
| Search large repo | Solr | 100x faster |
| Get statistics | Solr | Only option for facets |
| Semantic search | Solr | Only option for vectors |
| Verify file content | Read | Need exact content |
| Stale index | Grep | Freshness matters |

## Conclusion

**Index Freshness**: Use file watcher + git hooks + periodic reindex (hybrid approach)

**Claude Code Integration**:
- **Now**: Add complementary MCP tools (Claude chooses when to use)
- **Future**: Auto-acceleration (Claude Code learns to prefer Solr)

**The key insight**: You don't need to "replace" Glob/Grep. Instead, provide better alternatives that Claude will naturally prefer for appropriate tasks.

Start with:
1. ✅ File watcher for automatic index updates
2. ✅ New MCP tools for fast search
3. ✅ Let Claude discover and use them

Claude is smart enough to figure out when to use which tool!
