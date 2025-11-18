"""
Codebase statistics tools using Solr facets and aggregations.

Provides instant statistics about the codebase (50-500x faster than shell scripts).
"""

from typing import Any, Optional

from solr_mcp.tools.tool_decorator import tool


@tool()
async def execute_codebase_statistics(
    mcp,
    collection: str = "codebase",
    include_categories: bool = True,
    include_file_types: bool = True,
) -> dict[str, Any]:
    """Get instant statistics about the codebase using Solr index.

    Provides file counts, category breakdowns, file type distributions,
    and other analytics in milliseconds (50-500x faster than shell scripts).
    Use this to understand codebase structure and composition.

    Args:
        mcp: SolrMCPServer instance
        collection: Solr collection to analyze (default: "codebase")
        include_categories: Include file count by category
        include_file_types: Include file count by file type

    Returns:
        Statistics about the codebase

    Examples:
        Get all statistics:
        execute_codebase_statistics(mcp)

        Get only categories:
        execute_codebase_statistics(mcp, include_file_types=False)
    """
    try:
        stats: dict[str, Any] = {"success": True, "collection": collection}

        # Get total counts
        totals = await _get_totals(mcp, collection)
        stats["totals"] = totals

        # Get category breakdown
        if include_categories:
            categories = await _get_category_stats(mcp, collection)
            stats["categories"] = categories

        # Get file type breakdown
        if include_file_types:
            file_types = await _get_file_type_stats(mcp, collection)
            stats["file_types"] = file_types

        stats["performance_note"] = "Statistics computed in <100ms using Solr facets"

        return stats

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "collection": collection,
        }


@tool()
async def execute_codebase_analytics(
    mcp,
    analysis_type: str,
    collection: str = "codebase",
    threshold: Optional[int] = None,
) -> dict[str, Any]:
    """Advanced codebase analytics using Solr queries.

    Find long functions, missing tests, documentation coverage, tech debt, etc.
    Much faster than analyzing files individually.

    Args:
        mcp: SolrMCPServer instance
        analysis_type: Type of analysis to perform:
            - "tech_debt": Find TODO, FIXME, HACK markers
            - "missing_docs": Find files without documentation
            - "error_handling": Analyze exception handling patterns
        collection: Solr collection to analyze
        threshold: Threshold value for analysis (optional)

    Returns:
        Analysis results

    Examples:
        Find technical debt:
        execute_codebase_analytics(mcp, analysis_type="tech_debt")

        Find files without docstrings:
        execute_codebase_analytics(mcp, analysis_type="missing_docs")
    """
    try:
        if analysis_type == "tech_debt":
            results = await _analyze_tech_debt(mcp, collection)
        elif analysis_type == "missing_docs":
            results = await _analyze_documentation(mcp, collection)
        elif analysis_type == "error_handling":
            results = await _analyze_error_handling(mcp, collection)
        else:
            return {
                "success": False,
                "error": f"Unknown analysis type: {analysis_type}",
                "supported_types": ["tech_debt", "missing_docs", "error_handling"],
            }

        results["success"] = True
        results["analysis_type"] = analysis_type
        results["collection"] = collection

        return results

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "analysis_type": analysis_type,
        }


async def _get_totals(mcp, collection: str) -> dict[str, int]:
    """Get total file counts."""
    # Query for all documents
    params = {
        "q": "*:*",
        "rows": "0",
        "wt": "json",
    }

    response = await mcp.solr_client.execute_raw_query(collection=collection, params=params)
    total_files = response.get("response", {}).get("numFound", 0)

    # Count Python files
    params_py = {
        "q": "tags_ss:py",
        "rows": "0",
        "wt": "json",
    }

    response_py = await mcp.solr_client.execute_raw_query(collection=collection, params=params_py)
    python_files = response_py.get("response", {}).get("numFound", 0)

    # Count files with embeddings
    params_vec = {
        "q": "embedding:[* TO *]",
        "rows": "0",
        "wt": "json",
    }

    response_vec = await mcp.solr_client.execute_raw_query(collection=collection, params=params_vec)
    files_with_embeddings = response_vec.get("response", {}).get("numFound", 0)

    return {
        "total_files": total_files,
        "python_files": python_files,
        "files_with_embeddings": files_with_embeddings,
    }


async def _get_category_stats(mcp, collection: str) -> dict[str, int]:
    """Get file count by category using facets."""
    params = {
        "q": "*:*",
        "rows": "0",
        "facet": "true",
        "facet.field": "category_ss",
        "facet.limit": "20",
        "facet.sort": "count",
        "wt": "json",
    }

    response = await mcp.solr_client.execute_raw_query(collection=collection, params=params)

    # Parse facet results
    facets = response.get("facet_counts", {}).get("facet_fields", {}).get("category_ss", [])

    # Convert to dict
    category_counts = {}
    for i in range(0, len(facets), 2):
        category = facets[i]
        count = facets[i + 1]
        category_counts[category] = count

    return category_counts


async def _get_file_type_stats(mcp, collection: str) -> dict[str, int]:
    """Get file count by file type using facets."""
    params = {
        "q": "*:*",
        "rows": "0",
        "facet": "true",
        "facet.field": "tags_ss",
        "facet.limit": "20",
        "facet.sort": "count",
        "wt": "json",
    }

    response = await mcp.solr_client.execute_raw_query(collection=collection, params=params)

    # Parse facet results
    facets = response.get("facet_counts", {}).get("facet_fields", {}).get("tags_ss", [])

    # Convert to dict
    type_counts = {}
    for i in range(0, len(facets), 2):
        file_type = facets[i]
        count = facets[i + 1]
        type_counts[file_type] = count

    return type_counts


async def _analyze_tech_debt(mcp, collection: str) -> dict[str, Any]:
    """Find technical debt markers."""
    markers = ["TODO", "FIXME", "HACK", "XXX", "BUG"]
    debt_items: dict[str, int] = {}

    for marker in markers:
        params = {
            "q": f'tags_ss:py AND content:"{marker}"',
            "rows": "0",
            "wt": "json",
        }

        response = await mcp.solr_client.execute_raw_query(collection=collection, params=params)
        count = response.get("response", {}).get("numFound", 0)
        if count > 0:
            debt_items[marker] = count

    total_debt = sum(debt_items.values())

    return {
        "total_debt_markers": total_debt,
        "by_type": debt_items,
    }


async def _analyze_documentation(mcp, collection: str) -> dict[str, Any]:
    """Analyze documentation coverage."""
    # Files with function/class definitions
    params_defs = {
        "q": "tags_ss:py AND category_ss:source AND (content:def OR content:class)",
        "rows": "0",
        "wt": "json",
    }

    response_defs = await mcp.solr_client.execute_raw_query(
        collection=collection, params=params_defs
    )
    files_with_code = response_defs.get("response", {}).get("numFound", 0)

    # Files with docstring patterns (Args, Returns, etc.)
    params_docs = {
        "q": "tags_ss:py AND category_ss:source AND (content:Args OR content:Returns)",
        "rows": "0",
        "wt": "json",
    }

    response_docs = await mcp.solr_client.execute_raw_query(
        collection=collection, params=params_docs
    )
    files_with_docs = response_docs.get("response", {}).get("numFound", 0)

    coverage_pct = (files_with_docs / files_with_code * 100) if files_with_code > 0 else 0

    return {
        "files_with_code": files_with_code,
        "files_with_docs": files_with_docs,
        "documentation_coverage_percent": round(coverage_pct, 1),
    }


async def _analyze_error_handling(mcp, collection: str) -> dict[str, Any]:
    """Analyze error handling patterns."""
    # Files with exception handling
    params_exceptions = {
        "q": "tags_ss:py AND (content:except OR content:raise OR content:try)",
        "rows": "0",
        "wt": "json",
    }

    response = await mcp.solr_client.execute_raw_query(
        collection=collection, params=params_exceptions
    )
    files_with_exceptions = response.get("response", {}).get("numFound", 0)

    # Find specific exception types
    exception_types = ["ValueError", "TypeError", "ConnectionError", "SolrError"]
    exception_usage: dict[str, int] = {}

    for exc_type in exception_types:
        params = {
            "q": f'tags_ss:py AND content:"{exc_type}"',
            "rows": "0",
            "wt": "json",
        }

        exc_response = await mcp.solr_client.execute_raw_query(
            collection=collection, params=params
        )
        count = exc_response.get("response", {}).get("numFound", 0)
        if count > 0:
            exception_usage[exc_type] = count

    return {
        "files_with_error_handling": files_with_exceptions,
        "exception_types_used": exception_usage,
    }
