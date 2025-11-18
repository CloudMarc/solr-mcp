"""
Fast codebase search tool using Solr index.

Provides grep-like functionality but 10-100x faster for large codebases.
Automatically falls back to traditional grep if Solr is unavailable.
"""

import subprocess
from typing import Any, Optional

from solr_mcp.tools.tool_decorator import tool


@tool()
async def execute_fast_codebase_search(
    mcp,
    pattern: str,
    file_type: Optional[str] = None,
    collection: str = "codebase",
    max_results: int = 100,
    use_highlighting: bool = True,
) -> dict[str, Any]:
    """Search file contents in the codebase using Solr index (10-100x faster than grep).

    Use this for content searches in large codebases. Supports pattern matching,
    file type filtering, and highlighting. Automatically falls back to grep if
    Solr index is unavailable.

    Args:
        mcp: SolrMCPServer instance
        pattern: Search pattern (supports Solr query syntax)
        file_type: Filter by file extension (e.g., "py", "js", "md")
        collection: Solr collection to search (default: "codebase")
        max_results: Maximum number of results to return
        use_highlighting: Return highlighted snippets of matches

    Returns:
        Search results with files, matches, and optional highlighting

    Examples:
        Search for "SolrClient" in Python files:
        execute_fast_codebase_search(mcp, pattern="SolrClient", file_type="py")

        Search for function definitions:
        execute_fast_codebase_search(mcp, pattern="async def", file_type="py")
    """
    try:
        # Try Solr search first (fast path)
        results = await _solr_search(
            mcp=mcp,
            pattern=pattern,
            file_type=file_type,
            collection=collection,
            max_results=max_results,
            use_highlighting=use_highlighting,
        )

        results["search_method"] = "solr"
        results["performance_note"] = "Using Solr index (10-100x faster than grep)"

        return results

    except Exception as e:
        # Fall back to grep (slow path)
        mcp.logger.warning(f"Solr search failed ({e}), falling back to grep")

        results = await _grep_fallback(
            pattern=pattern,
            file_type=file_type,
            max_results=max_results,
        )

        results["search_method"] = "grep"
        results["performance_note"] = "Solr unavailable, using grep (slower)"

        return results


async def _solr_search(
    mcp,
    pattern: str,
    file_type: Optional[str],
    collection: str,
    max_results: int,
    use_highlighting: bool,
) -> dict[str, Any]:
    """Execute search using Solr index."""
    # Build query
    query_parts = [f"content:{pattern}"]

    # File type filter
    if file_type:
        file_type = file_type.lstrip(".")
        query_parts.append(f"tags_ss:{file_type}")

    query = " AND ".join(query_parts)

    # Build params
    params: dict[str, Any] = {
        "q": query,
        "rows": str(max_results),
        "fl": "id,source,title,content,category_ss,tags_ss",
        "wt": "json",
    }

    # Add highlighting
    if use_highlighting:
        params.update(
            {
                "hl": "true",
                "hl.fl": "content",
                "hl.snippets": "5",
                "hl.fragsize": "200",
                "hl.simple.pre": "**",
                "hl.simple.post": "**",
            }
        )

    # Execute query
    response = await mcp.solr_client.execute_raw_query(collection=collection, params=params)

    # Parse results
    docs = response.get("response", {}).get("docs", [])
    highlighting = response.get("highlighting", {})
    num_found = response.get("response", {}).get("numFound", 0)

    # Format results
    matches = []
    for doc in docs:
        doc_id = doc.get("id", "")
        source = doc.get("source", "unknown")

        match_entry: dict[str, Any] = {
            "file": source,
            "categories": doc.get("category_ss", []),
            "file_type": doc.get("tags_ss", []),
        }

        # Add highlighting if available
        if use_highlighting and doc_id in highlighting:
            snippets = highlighting[doc_id].get("content", [])
            match_entry["snippets"] = snippets
            match_entry["match_count"] = len(snippets)
        else:
            match_entry["match_count"] = 1

        matches.append(match_entry)

    return {
        "success": True,
        "pattern": pattern,
        "file_type": file_type,
        "total_matches": num_found,
        "returned_results": len(matches),
        "matches": matches,
    }


async def _grep_fallback(
    pattern: str,
    file_type: Optional[str],
    max_results: int,
) -> dict[str, Any]:
    """Fallback to grep when Solr unavailable."""
    # Build grep command
    cmd = ["grep", "-r", "-i", pattern]

    # Add file type filter
    if file_type:
        cmd.extend(["--include", f"*.{file_type.lstrip('.')}"])

    cmd.append(".")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )

        # Parse grep output
        lines = [line for line in result.stdout.split("\n") if line.strip()]
        matches = []

        for line in lines[:max_results]:
            if ":" in line:
                file_path, content = line.split(":", 1)
                matches.append(
                    {
                        "file": file_path.strip(),
                        "snippet": content.strip(),
                    }
                )

        return {
            "success": True,
            "pattern": pattern,
            "file_type": file_type,
            "total_matches": len(lines),
            "returned_results": len(matches),
            "matches": matches,
        }

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": "grep timed out after 30 seconds",
            "pattern": pattern,
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "pattern": pattern,
        }
