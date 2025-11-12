"""Tool for committing changes to Solr."""

from typing import Any, Dict

from solr_mcp.tools.tool_decorator import tool


@tool()
async def execute_commit(
    mcp,
    collection: str,
    soft: bool = False,
    wait_searcher: bool = True,
    expunge_deletes: bool = False,
) -> Dict[str, Any]:
    """Commit pending changes to a Solr collection.

    Makes all recently indexed documents searchable by committing the transaction.
    Supports both soft commits (visibility without durability) and hard commits
    (full durability to disk).

    Commit Types:
    - Hard Commit (soft=False): Flushes to disk, ensures durability, slower
    - Soft Commit (soft=True): Makes docs visible, no fsync, much faster

    When to use:
    - Soft commits: Near real-time search (every 1-10 seconds)
    - Hard commits: Durability guarantee (every 15-60 seconds)
    - Best practice: Frequent soft commits + periodic hard commits

    Args:
        mcp: SolrMCPServer instance
        collection: Name of the collection to commit
        soft: If True, performs soft commit (visible but not durable)
              If False, performs hard commit (visible and durable)
              Default: False (hard commit)
        wait_searcher: Wait for new searcher to be opened before returning
                       Default: True
        expunge_deletes: Merge segments with deletes away (expensive)
                        Default: False

    Returns:
        Dict containing:
        - status: Success/failure
        - collection: Collection name
        - commit_type: "soft" or "hard"

    Examples:
        # Hard commit (default) - durable to disk
        result = solr_commit(collection="products")

        # Soft commit - make visible immediately without fsync
        result = solr_commit(collection="products", soft=True)

        # Hard commit with delete expunge (cleanup)
        result = solr_commit(
            collection="products",
            soft=False,
            expunge_deletes=True
        )

        # Soft commit without waiting (fastest)
        result = solr_commit(
            collection="products",
            soft=True,
            wait_searcher=False
        )

        # Typical NRT pattern:
        # 1. Add documents without commit
        solr_add_documents(docs=[...], commit=False)

        # 2. Soft commit for immediate visibility
        solr_commit(collection="products", soft=True)

        # 3. Hard commit periodically (e.g., every 60 seconds)
        solr_commit(collection="products", soft=False)
    """
    solr_client = mcp.solr_client
    return await solr_client.commit(
        collection=collection,
        soft=soft,
        wait_searcher=wait_searcher,
        expunge_deletes=expunge_deletes,
    )
