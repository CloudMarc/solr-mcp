"""
Fast file finding tool using Solr index.

Provides find-like functionality but 10-50x faster for large codebases.
Automatically falls back to traditional find if Solr is unavailable.
"""

import subprocess
from pathlib import Path
from typing import Any

from solr_mcp.tools.tool_decorator import tool


@tool()
async def execute_fast_file_find(
    mcp,
    pattern: str,
    file_type: str | None = None,
    category: str | None = None,
    collection: str = "codebase",
    max_results: int = 100,
) -> dict[str, Any]:
    """Find files by name/path using Solr index (10-50x faster than find).

    Use this for file discovery in large codebases. Supports pattern matching,
    file type filtering, and category filtering. Automatically falls back to
    find if Solr index is unavailable.

    Args:
        mcp: SolrMCPServer instance
        pattern: File name or path pattern (supports wildcards)
        file_type: Filter by file extension (e.g., "py", "js", "md")
        category: Filter by category (e.g., "source", "tests", "documentation")
        collection: Solr collection to search (default: "codebase")
        max_results: Maximum number of results to return

    Returns:
        List of matching files with metadata

    Examples:
        Find all Python files:
        execute_fast_file_find(mcp, pattern="*.py")

        Find test files:
        execute_fast_file_find(mcp, pattern="test_*.py", category="tests")

        Find files in specific directory:
        execute_fast_file_find(mcp, pattern="solr_mcp/tools/*")
    """
    try:
        # Try Solr search first (fast path)
        results = await _solr_find(
            mcp=mcp,
            pattern=pattern,
            file_type=file_type,
            category=category,
            collection=collection,
            max_results=max_results,
        )

        results["search_method"] = "solr"
        results["performance_note"] = "Using Solr index (10-50x faster than find)"

        return results

    except Exception as e:
        # Fall back to find (slow path)
        mcp.logger.warning(f"Solr find failed ({e}), falling back to find command")

        results = await _find_fallback(
            pattern=pattern,
            file_type=file_type,
            max_results=max_results,
        )

        results["search_method"] = "find"
        results["performance_note"] = "Solr unavailable, using find (slower)"

        return results


async def _solr_find(
    mcp,
    pattern: str,
    file_type: str | None,
    category: str | None,
    collection: str,
    max_results: int,
) -> dict[str, Any]:
    """Execute file search using Solr index."""
    # Build query
    query_parts = []

    # Convert file pattern to Solr query
    pattern = pattern.lstrip("./")
    solr_pattern = pattern.replace("*", "*")

    # Search in source field
    query_parts.append(f"source:*{solr_pattern}*")

    # File type filter
    if file_type:
        file_type = file_type.lstrip(".")
        query_parts.append(f"tags_ss:{file_type}")

    # Category filter
    if category:
        query_parts.append(f"category_ss:{category}")

    query = " AND ".join(query_parts)

    # Build params
    params = {
        "q": query,
        "rows": str(max_results),
        "fl": "source,title,category_ss,tags_ss,date_indexed_dt",
        "sort": "source asc",
        "wt": "json",
    }

    # Execute query
    response = await mcp.solr_client.execute_raw_query(
        collection=collection, params=params
    )

    # Parse results
    docs = response.get("response", {}).get("docs", [])
    num_found = response.get("response", {}).get("numFound", 0)

    # Format results
    files = []
    for doc in docs:
        title = doc.get("title", "unknown")
        if isinstance(title, list):
            title = title[0] if title else "unknown"

        file_entry: dict[str, Any] = {
            "path": doc.get("source", "unknown"),
            "name": title,
            "categories": doc.get("category_ss", []),
            "file_type": doc.get("tags_ss", []),
            "indexed_at": doc.get("date_indexed_dt"),
        }
        files.append(file_entry)

    return {
        "success": True,
        "pattern": pattern,
        "file_type": file_type,
        "category": category,
        "total_found": num_found,
        "returned_results": len(files),
        "files": files,
    }


async def _find_fallback(
    pattern: str,
    file_type: str | None,
    max_results: int,
) -> dict[str, Any]:
    """Fallback to find command when Solr unavailable."""
    # Build find command
    cmd = ["find", ".", "-type", "f"]

    # Add name pattern
    if file_type:
        if "*" in pattern:
            name_pattern = pattern
        else:
            name_pattern = f"*{pattern}*.{file_type.lstrip('.')}"
    else:
        name_pattern = pattern if "*" in pattern else f"*{pattern}*"

    cmd.extend(["-name", name_pattern])

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )

        # Parse find output
        lines = [line.strip() for line in result.stdout.split("\n") if line.strip()]

        files = []
        for line in lines[:max_results]:
            p = Path(line)
            files.append(
                {
                    "path": line,
                    "name": p.name,
                }
            )

        return {
            "success": True,
            "pattern": pattern,
            "file_type": file_type,
            "total_found": len(lines),
            "returned_results": len(files),
            "files": files,
        }

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": "find timed out after 30 seconds",
            "pattern": pattern,
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "pattern": pattern,
        }
