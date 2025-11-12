"""Tool for exploring indexed terms using Solr's Terms Component."""

from typing import Any, Dict, Optional

from solr_mcp.tools.tool_decorator import tool


@tool()
async def execute_terms(
    mcp,
    collection: str,
    field: str,
    prefix: Optional[str] = None,
    regex: Optional[str] = None,
    limit: int = 10,
    min_count: int = 1,
    max_count: Optional[int] = None,
) -> Dict[str, Any]:
    """Explore indexed terms in a Solr collection.

    This tool uses Solr's Terms Component to retrieve indexed terms from a field.
    Useful for:
    - Autocomplete/typeahead functionality
    - Exploring the vocabulary of a field
    - Finding terms matching a pattern
    - Query expansion and suggestion

    Args:
        mcp: MCP instance
        collection: Collection name to query
        field: Field name to get terms from
        prefix: Return only terms starting with this prefix
        regex: Return only terms matching this regex pattern
        limit: Maximum number of terms to return (default: 10)
        min_count: Minimum document frequency for terms (default: 1)
        max_count: Maximum document frequency for terms

    Returns:
        Dictionary containing:
        - terms: List of terms with their document frequencies
        - field: Field name queried
        - collection: Collection name
        - total_terms: Total number of matching terms
    """
    return await mcp.solr_client.get_terms(
        collection=collection,
        field=field,
        prefix=prefix,
        regex=regex,
        limit=limit,
        min_count=min_count,
        max_count=max_count,
    )
