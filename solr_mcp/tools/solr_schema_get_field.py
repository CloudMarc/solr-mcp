"""Tool for getting details of a specific schema field."""

from typing import Any, Dict

from solr_mcp.tools.tool_decorator import tool


@tool()
async def execute_schema_get_field(
    mcp,
    collection: str,
    field_name: str,
) -> Dict[str, Any]:
    """Get detailed information about a specific field in the schema.

    Args:
        mcp: MCP instance
        collection: Collection name
        field_name: Name of the field to get details for

    Returns:
        Dictionary containing:
        - field: Field definition with all properties
        - collection: Collection name
    """
    return await mcp.solr_client.get_schema_field(
        collection=collection, field_name=field_name
    )
