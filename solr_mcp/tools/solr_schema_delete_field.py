"""Tool for deleting fields from Solr schema."""

from typing import Any

from solr_mcp.tools.tool_decorator import tool


@tool()
async def execute_schema_delete_field(
    mcp,
    collection: str,
    field_name: str,
) -> dict[str, Any]:
    """Delete a field from a Solr collection's schema.

    WARNING: This operation cannot be undone. Ensure the field is not in use
    before deletion. Documents with values in this field will lose that data.

    Args:
        mcp: MCP instance
        collection: Collection name
        field_name: Name of the field to delete

    Returns:
        Dictionary containing:
        - status: Success/failure status
        - field_name: Name of the deleted field
        - collection: Collection name
    """
    return await mcp.solr_client.delete_schema_field(
        collection=collection, field_name=field_name
    )
