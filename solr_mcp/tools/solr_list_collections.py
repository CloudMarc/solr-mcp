"""Tool for listing Solr collections."""

from solr_mcp.tools.tool_decorator import tool


@tool()
async def execute_list_collections(mcp) -> list[str]:
    """List all available Solr collections.

    Lists all collections available in the Solr cluster.

    Args:
        mcp: SolrMCPServer instance

    Returns:
        List of collection names
    """
    solr_client = mcp.solr_client
    return await solr_client.list_collections()
