"""Tool for deleting documents from Solr."""

from typing import Any, Dict, List, Optional

from solr_mcp.tools.tool_decorator import tool


@tool()
async def execute_delete_documents(
    mcp,
    collection: str,
    ids: Optional[List[str]] = None,
    query: Optional[str] = None,
    commit: bool = True,
) -> Dict[str, Any]:
    """Delete documents from a Solr collection.

    Deletes documents from the specified Solr collection either by document IDs
    or by a query. You must specify either 'ids' or 'query', but not both.

    Args:
        mcp: SolrMCPServer instance
        collection: Name of the collection to delete from
        ids: List of document IDs to delete (mutually exclusive with query)
        query: Solr query to match documents to delete (mutually exclusive with ids)
        commit: Whether to commit immediately after deleting (default: True)

    Returns:
        Dict containing status, collection name, number affected, and commit info

    Examples:
        # Delete by IDs
        result = await execute_delete_documents(mcp, "my_collection", ids=["doc1", "doc2"])

        # Delete by query
        result = await execute_delete_documents(mcp, "my_collection", query="status:archived")
    """
    solr_client = mcp.solr_client
    return await solr_client.delete_documents(
        collection=collection,
        ids=ids,
        query=query,
        commit=commit,
    )
