"""Tool for real-time get of Solr documents."""

from typing import Any

from solr_mcp.tools.tool_decorator import tool


@tool()
async def execute_realtime_get(
    mcp,
    collection: str,
    doc_ids: list[str],
    fl: str | None = None,
) -> dict[str, Any]:
    """Get documents in real-time, including uncommitted changes.

    Real-Time Get (RTG) retrieves the latest version of documents immediately,
    even if they haven't been committed yet. This provides read-your-own-writes
    consistency, allowing you to see changes immediately after indexing.

    Unlike regular search, RTG:
    - Returns uncommitted documents
    - Bypasses the searcher
    - Always returns the latest version
    - Works by document ID only (no query)

    Use cases:
    - Verify documents were indexed correctly
    - Read-your-own-writes pattern
    - Get latest version without waiting for commit
    - Preview changes before making them visible to search

    Args:
        mcp: MCP instance
        collection: Collection name
        doc_ids: List of document IDs to retrieve
        fl: Optional comma-separated list of fields to return
            If not specified, returns all stored fields

    Returns:
        Dictionary containing:
        - docs: List of retrieved documents (may be fewer than requested if some don't exist)
        - num_found: Number of documents found
        - collection: Collection name

    Examples:
        # Get single document
        result = solr_realtime_get(
            collection="products",
            doc_ids=["PROD-123"]
        )

        # Get multiple documents
        result = solr_realtime_get(
            collection="products",
            doc_ids=["PROD-123", "PROD-456", "PROD-789"]
        )

        # Get specific fields only
        result = solr_realtime_get(
            collection="products",
            doc_ids=["PROD-123"],
            fl="id,name,price,stock"
        )

        # Verify document after adding (before commit)
        solr_add_documents(docs=[{"id": "NEW-1", "name": "New Product"}], commit=False)
        result = solr_realtime_get(collection="products", doc_ids=["NEW-1"])
        # Returns the document immediately, even though not committed
    """
    return await mcp.solr_client.realtime_get(
        collection=collection,
        doc_ids=doc_ids,
        fl=fl,
    )
