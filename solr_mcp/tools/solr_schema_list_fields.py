"""Tool for listing schema fields with full details."""

from typing import Any, Dict

from solr_mcp.tools.tool_decorator import tool


@tool()
async def execute_schema_list_fields(
    mcp,
    collection: str,
) -> Dict[str, Any]:
    """List all fields in a collection's schema with full details.

    This tool provides comprehensive schema information including field types,
    properties, and configurations. Different from solr_list_fields which shows
    field usage and copyField relationships, this shows the raw schema definition.

    Args:
        mcp: MCP instance
        collection: Collection name

    Returns:
        Dictionary containing:
        - fields: List of field definitions from schema
        - collection: Collection name
        - total_fields: Total number of fields
    """
    return await mcp.solr_client.get_schema_fields(collection=collection)
