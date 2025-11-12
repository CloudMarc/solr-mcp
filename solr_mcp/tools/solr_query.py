"""Tool for executing standard Solr queries with highlighting and stats."""

from typing import Any, Dict, List, Optional

from solr_mcp.tools.tool_decorator import tool


@tool()
async def execute_query(
    mcp,
    collection: str,
    q: str = "*:*",
    fq: Optional[List[str]] = None,
    fl: Optional[str] = None,
    rows: int = 10,
    start: int = 0,
    sort: Optional[str] = None,
    highlight_fields: Optional[List[str]] = None,
    highlight_snippets: int = 3,
    highlight_fragsize: int = 100,
    highlight_method: str = "unified",
    stats_fields: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Execute standard Solr query with highlighting and stats support.

    This tool provides access to Solr's standard query parser with support for
    highlighting (showing WHY documents matched) and statistical aggregations.

    Use this tool when you need:
    - Highlighting to show matched terms in context
    - Statistical aggregations (min, max, mean, sum, stddev, etc.)
    - Standard Solr query syntax with filters

    For SQL queries, use solr_select instead.

    Args:
        mcp: MCP instance
        collection: Collection name to query
        q: Main query string (default: "*:*" for all documents)
        fq: Optional list of filter queries
        fl: Fields to return (comma-separated, default: all stored fields)
        rows: Number of documents to return (default: 10)
        start: Offset for pagination (default: 0)
        sort: Sort specification (e.g., "price asc, score desc")
        highlight_fields: Fields to highlight in results
        highlight_snippets: Number of snippets per field (default: 3)
        highlight_fragsize: Size of each snippet in characters (default: 100)
        highlight_method: Highlighting method - "unified", "original", or "fastVector" (default: "unified")
        stats_fields: Fields to compute statistics for (numeric fields)

    Returns:
        Dictionary containing:
        - num_found: Total number of matching documents
        - docs: List of matching documents
        - highlighting: Dict mapping doc IDs to highlighted snippets (if requested)
        - stats: Statistical aggregations for requested fields (if requested)
        - query_info: Information about the executed query
    """
    return await mcp.solr_client.execute_query(
        collection=collection,
        q=q,
        fq=fq,
        fl=fl,
        rows=rows,
        start=start,
        sort=sort,
        highlight_fields=highlight_fields,
        highlight_snippets=highlight_snippets,
        highlight_fragsize=highlight_fragsize,
        highlight_method=highlight_method,
        stats_fields=stats_fields,
    )
