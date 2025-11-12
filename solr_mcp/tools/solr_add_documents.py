"""Tool for adding documents to Solr."""

from typing import Any

from solr_mcp.tools.tool_decorator import tool


@tool()
async def execute_add_documents(
    mcp,
    collection: str,
    documents: list[dict[str, Any]],
    commit: bool = True,
    commit_within: int | None = None,
    overwrite: bool = True,
) -> dict[str, Any]:
    """Add or update documents in a Solr collection.

    Adds one or more documents to the specified Solr collection. Documents with
    existing IDs will be updated (overwritten) by default.

    Args:
        mcp: SolrMCPServer instance
        collection: Name of the collection to add documents to
        documents: List of documents to add (each document is a dict with field-value pairs)
        commit: Whether to commit immediately after adding (default: True)
        commit_within: Optional time in milliseconds to auto-commit (alternative to commit)
        overwrite: Whether to overwrite existing documents with same ID (default: True)

    Returns:
        Dict containing status, collection name, number of documents added, and commit info

    Example:
        documents = [
            {"id": "doc1", "title": "First Document", "content": "This is the first document"},
            {"id": "doc2", "title": "Second Document", "content": "This is the second document"}
        ]
        result = await execute_add_documents(mcp, "my_collection", documents)
    """
    solr_client = mcp.solr_client
    return await solr_client.add_documents(
        collection=collection,
        documents=documents,
        commit=commit,
        commit_within=commit_within,
        overwrite=overwrite,
    )
