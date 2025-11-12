"""Tool for adding fields to Solr schema."""

from typing import Any

from solr_mcp.tools.tool_decorator import tool


@tool()
async def execute_schema_add_field(
    mcp,
    collection: str,
    field_name: str,
    field_type: str,
    stored: bool = True,
    indexed: bool = True,
    required: bool = False,
    multiValued: bool = False,
    docValues: bool | None = None,
) -> dict[str, Any]:
    """Add a new field to a Solr collection's schema.

    This tool allows dynamic schema modification by adding new fields.
    Useful for evolving your data model without manual schema edits.

    Common field types:
    - string: Single-valued string (not analyzed)
    - text_general: Analyzed text field
    - pint, plong, pfloat, pdouble: Numeric types with DocValues
    - pdate: Date field
    - boolean: Boolean field
    - location: Geo-spatial location

    Args:
        mcp: MCP instance
        collection: Collection name
        field_name: Name of the new field
        field_type: Solr field type (e.g., "text_general", "string", "pint")
        stored: Whether to store the field value (default: True)
        indexed: Whether to index the field for searching (default: True)
        required: Whether the field is required (default: False)
        multiValued: Whether field can have multiple values (default: False)
        docValues: Whether to enable docValues for sorting/faceting (default: auto based on type)

    Returns:
        Dictionary containing:
        - status: Success/failure status
        - field: The created field definition
        - collection: Collection name
    """
    return await mcp.solr_client.add_schema_field(
        collection=collection,
        field_name=field_name,
        field_type=field_type,
        stored=stored,
        indexed=indexed,
        required=required,
        multiValued=multiValued,
        docValues=docValues,
    )
