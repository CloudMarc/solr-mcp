"""Tool for atomic field updates in Solr documents."""

from typing import Any

from solr_mcp.tools.tool_decorator import tool


@tool()
async def execute_atomic_update(
    mcp,
    collection: str,
    doc_id: str,
    updates: dict[str, dict[str, Any]],
    version: int | None = None,
    commit: bool = False,
    commitWithin: int | None = None,
) -> dict[str, Any]:
    """Atomically update specific fields in a Solr document.

    Atomic updates allow you to update individual fields without reindexing
    the entire document. This is much more efficient than fetching, modifying,
    and reindexing the complete document.

    IMPORTANT: Atomic updates require that all fields are stored in the schema.
    Fields that are indexed-only cannot be atomically updated.

    Supported update operations:
    - set: Replace the field value
    - add: Add value(s) to a multi-valued field
    - remove: Remove value(s) from a multi-valued field
    - removeregex: Remove values matching regex from multi-valued field
    - inc: Increment/decrement a numeric field
    - set-if-null: Set value only if field is currently null

    Args:
        mcp: MCP instance
        collection: Collection name
        doc_id: Document ID to update
        updates: Dictionary of field updates, where each value is an operation dict
                 Example: {"price": {"set": 29.99}, "stock": {"inc": -5}}
        version: Optional document version for optimistic concurrency control
                 Update will fail if version doesn't match current document version
        commit: Whether to commit immediately (default: False)
        commitWithin: Milliseconds within which to auto-commit (optional)

    Returns:
        Dictionary containing:
        - status: Success/failure status
        - doc_id: ID of updated document
        - collection: Collection name
        - version: New document version (if optimistic concurrency used)

    Examples:
        # Replace a field value
        solr_atomic_update(
            collection="products",
            doc_id="PROD-123",
            updates={"price": {"set": 29.99}}
        )

        # Increment a counter
        solr_atomic_update(
            collection="products",
            doc_id="PROD-123",
            updates={"view_count": {"inc": 1}}
        )

        # Add tags to multi-valued field
        solr_atomic_update(
            collection="products",
            doc_id="PROD-123",
            updates={"tags": {"add": ["sale", "featured"]}}
        )

        # Multiple operations at once
        solr_atomic_update(
            collection="products",
            doc_id="PROD-123",
            updates={
                "price": {"set": 24.99},
                "stock": {"inc": -1},
                "tags": {"add": ["popular"]},
                "status": {"set": "active"}
            }
        )

        # With optimistic concurrency control
        solr_atomic_update(
            collection="products",
            doc_id="PROD-123",
            updates={"stock": {"inc": -1}},
            version=42  # Fails if document version isn't 42
        )
    """
    return await mcp.solr_client.atomic_update(
        collection=collection,
        doc_id=doc_id,
        updates=updates,
        version=version,
        commit=commit,
        commitWithin=commitWithin,
    )
