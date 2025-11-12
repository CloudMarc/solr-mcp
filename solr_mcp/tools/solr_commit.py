"""Tool for committing changes to Solr."""

from typing import Any, Dict

from solr_mcp.tools.tool_decorator import tool


@tool()
async def execute_commit(
    mcp,
    collection: str,
) -> Dict[str, Any]:
    """Commit pending changes to a Solr collection.

    Makes all recently indexed documents searchable by committing the transaction.
    This is useful when documents were added with commit=False for batch operations.

    Args:
        mcp: SolrMCPServer instance
        collection: Name of the collection to commit

    Returns:
        Dict containing status and collection name

    Example:
        # Add documents without committing
        await execute_add_documents(mcp, "my_collection", documents, commit=False)
        # ... add more documents ...
        # Then commit once
        result = await execute_commit(mcp, "my_collection")
    """
    solr_client = mcp.solr_client
    return await solr_client.commit(collection=collection)
