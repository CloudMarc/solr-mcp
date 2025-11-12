"""Tests for Phase 1 indexing features: atomic updates, commits, and realtime get."""

import pytest

from solr_mcp.solr.exceptions import IndexingError, SolrError
from solr_mcp.tools.solr_atomic_update import execute_atomic_update
from solr_mcp.tools.solr_commit import execute_commit
from solr_mcp.tools.solr_realtime_get import execute_realtime_get


# Tests for solr_atomic_update
@pytest.mark.asyncio
async def test_atomic_update_set_operation(mock_server):
    """Test atomic update with set operation."""
    expected_result = {
        "status": "success",
        "doc_id": "PROD-123",
        "collection": "products",
        "version": 42,
        "updates_applied": 1,
    }

    mock_server.solr_client.atomic_update.return_value = expected_result

    result = await execute_atomic_update(
        mock_server,
        collection="products",
        doc_id="PROD-123",
        updates={"price": {"set": 29.99}},
    )

    assert result["status"] == "success"
    assert result["doc_id"] == "PROD-123"
    assert result["updates_applied"] == 1


@pytest.mark.asyncio
async def test_atomic_update_increment_operation(mock_server):
    """Test atomic update with increment operation."""
    expected_result = {
        "status": "success",
        "doc_id": "PROD-123",
        "collection": "products",
        "version": 43,
        "updates_applied": 1,
    }

    mock_server.solr_client.atomic_update.return_value = expected_result

    result = await execute_atomic_update(
        mock_server,
        collection="products",
        doc_id="PROD-123",
        updates={"view_count": {"inc": 1}},
    )

    assert result["status"] == "success"
    assert result["updates_applied"] == 1


@pytest.mark.asyncio
async def test_atomic_update_add_to_multivalue(mock_server):
    """Test atomic update adding to multi-valued field."""
    expected_result = {
        "status": "success",
        "doc_id": "PROD-123",
        "collection": "products",
        "version": 44,
        "updates_applied": 1,
    }

    mock_server.solr_client.atomic_update.return_value = expected_result

    result = await execute_atomic_update(
        mock_server,
        collection="products",
        doc_id="PROD-123",
        updates={"tags": {"add": ["sale", "featured"]}},
    )

    assert result["status"] == "success"


@pytest.mark.asyncio
async def test_atomic_update_remove_from_multivalue(mock_server):
    """Test atomic update removing from multi-valued field."""
    expected_result = {
        "status": "success",
        "doc_id": "PROD-123",
        "collection": "products",
        "version": 45,
        "updates_applied": 1,
    }

    mock_server.solr_client.atomic_update.return_value = expected_result

    result = await execute_atomic_update(
        mock_server,
        collection="products",
        doc_id="PROD-123",
        updates={"tags": {"remove": ["old", "discontinued"]}},
    )

    assert result["status"] == "success"


@pytest.mark.asyncio
async def test_atomic_update_multiple_operations(mock_server):
    """Test atomic update with multiple field operations."""
    expected_result = {
        "status": "success",
        "doc_id": "PROD-123",
        "collection": "products",
        "version": 46,
        "updates_applied": 4,
    }

    mock_server.solr_client.atomic_update.return_value = expected_result

    result = await execute_atomic_update(
        mock_server,
        collection="products",
        doc_id="PROD-123",
        updates={
            "price": {"set": 24.99},
            "stock": {"inc": -1},
            "tags": {"add": ["popular"]},
            "status": {"set": "active"},
        },
    )

    assert result["updates_applied"] == 4


@pytest.mark.asyncio
async def test_atomic_update_with_version(mock_server):
    """Test atomic update with optimistic concurrency control."""
    expected_result = {
        "status": "success",
        "doc_id": "PROD-123",
        "collection": "products",
        "version": 43,
        "updates_applied": 1,
    }

    mock_server.solr_client.atomic_update.return_value = expected_result

    result = await execute_atomic_update(
        mock_server,
        collection="products",
        doc_id="PROD-123",
        updates={"stock": {"inc": -1}},
        version=42,  # Optimistic lock
    )

    assert result["status"] == "success"
    assert result["version"] == 43


@pytest.mark.asyncio
async def test_atomic_update_version_conflict(mock_server):
    """Test atomic update with version conflict."""
    error_message = "Version conflict: Document has been modified"
    mock_server.solr_client.atomic_update.side_effect = IndexingError(error_message)

    with pytest.raises(IndexingError, match="Version conflict"):
        await execute_atomic_update(
            mock_server,
            collection="products",
            doc_id="PROD-123",
            updates={"stock": {"inc": -1}},
            version=42,  # Wrong version
        )


@pytest.mark.asyncio
async def test_atomic_update_with_commit(mock_server):
    """Test atomic update with immediate commit."""
    expected_result = {
        "status": "success",
        "doc_id": "PROD-123",
        "collection": "products",
        "version": 47,
        "updates_applied": 1,
    }

    mock_server.solr_client.atomic_update.return_value = expected_result

    result = await execute_atomic_update(
        mock_server,
        collection="products",
        doc_id="PROD-123",
        updates={"price": {"set": 19.99}},
        commit=True,
    )

    assert result["status"] == "success"


@pytest.mark.asyncio
async def test_atomic_update_with_commit_within(mock_server):
    """Test atomic update with commitWithin."""
    expected_result = {
        "status": "success",
        "doc_id": "PROD-123",
        "collection": "products",
        "version": 48,
        "updates_applied": 1,
    }

    mock_server.solr_client.atomic_update.return_value = expected_result

    result = await execute_atomic_update(
        mock_server,
        collection="products",
        doc_id="PROD-123",
        updates={"price": {"set": 19.99}},
        commitWithin=5000,  # Auto-commit within 5 seconds
    )

    assert result["status"] == "success"


# Tests for enhanced solr_commit
@pytest.mark.asyncio
async def test_commit_hard_default(mock_server):
    """Test hard commit (default)."""
    expected_result = {
        "status": "success",
        "collection": "products",
        "commit_type": "hard",
        "committed": True,
    }

    mock_server.solr_client.commit.return_value = expected_result

    result = await execute_commit(mock_server, collection="products")

    assert result["commit_type"] == "hard"
    assert result["committed"] is True


@pytest.mark.asyncio
async def test_commit_soft(mock_server):
    """Test soft commit."""
    expected_result = {
        "status": "success",
        "collection": "products",
        "commit_type": "soft",
        "committed": True,
    }

    mock_server.solr_client.commit.return_value = expected_result

    result = await execute_commit(mock_server, collection="products", soft=True)

    assert result["commit_type"] == "soft"
    assert result["committed"] is True


@pytest.mark.asyncio
async def test_commit_with_wait_searcher(mock_server):
    """Test commit with wait_searcher option."""
    expected_result = {
        "status": "success",
        "collection": "products",
        "commit_type": "hard",
        "committed": True,
    }

    mock_server.solr_client.commit.return_value = expected_result

    result = await execute_commit(
        mock_server, collection="products", soft=False, wait_searcher=True
    )

    assert result["status"] == "success"


@pytest.mark.asyncio
async def test_commit_with_expunge_deletes(mock_server):
    """Test commit with expunge_deletes option."""
    expected_result = {
        "status": "success",
        "collection": "products",
        "commit_type": "hard",
        "committed": True,
    }

    mock_server.solr_client.commit.return_value = expected_result

    result = await execute_commit(
        mock_server, collection="products", soft=False, expunge_deletes=True
    )

    assert result["status"] == "success"


@pytest.mark.asyncio
async def test_commit_soft_without_wait(mock_server):
    """Test soft commit without waiting for searcher."""
    expected_result = {
        "status": "success",
        "collection": "products",
        "commit_type": "soft",
        "committed": True,
    }

    mock_server.solr_client.commit.return_value = expected_result

    result = await execute_commit(
        mock_server, collection="products", soft=True, wait_searcher=False
    )

    assert result["commit_type"] == "soft"


@pytest.mark.asyncio
async def test_commit_error_handling(mock_server):
    """Test commit error handling."""
    error_message = "Commit failed"
    mock_server.solr_client.commit.side_effect = SolrError(error_message)

    with pytest.raises(SolrError, match="Commit failed"):
        await execute_commit(mock_server, collection="products")


# Tests for solr_realtime_get
@pytest.mark.asyncio
async def test_realtime_get_single_doc(mock_server):
    """Test real-time get for single document."""
    expected_result = {
        "docs": [{"id": "PROD-123", "name": "Product 1", "price": 29.99}],
        "num_found": 1,
        "collection": "products",
    }

    mock_server.solr_client.realtime_get.return_value = expected_result

    result = await execute_realtime_get(
        mock_server, collection="products", doc_ids=["PROD-123"]
    )

    assert result["num_found"] == 1
    assert len(result["docs"]) == 1
    assert result["docs"][0]["id"] == "PROD-123"


@pytest.mark.asyncio
async def test_realtime_get_multiple_docs(mock_server):
    """Test real-time get for multiple documents."""
    expected_result = {
        "docs": [
            {"id": "PROD-123", "name": "Product 1"},
            {"id": "PROD-456", "name": "Product 2"},
            {"id": "PROD-789", "name": "Product 3"},
        ],
        "num_found": 3,
        "collection": "products",
    }

    mock_server.solr_client.realtime_get.return_value = expected_result

    result = await execute_realtime_get(
        mock_server,
        collection="products",
        doc_ids=["PROD-123", "PROD-456", "PROD-789"],
    )

    assert result["num_found"] == 3
    assert len(result["docs"]) == 3


@pytest.mark.asyncio
async def test_realtime_get_with_field_list(mock_server):
    """Test real-time get with field list."""
    expected_result = {
        "docs": [{"id": "PROD-123", "name": "Product 1", "price": 29.99}],
        "num_found": 1,
        "collection": "products",
    }

    mock_server.solr_client.realtime_get.return_value = expected_result

    result = await execute_realtime_get(
        mock_server,
        collection="products",
        doc_ids=["PROD-123"],
        fl="id,name,price",
    )

    assert "id" in result["docs"][0]
    assert "name" in result["docs"][0]
    assert "price" in result["docs"][0]


@pytest.mark.asyncio
async def test_realtime_get_nonexistent_doc(mock_server):
    """Test real-time get for non-existent document."""
    expected_result = {
        "docs": [],
        "num_found": 0,
        "collection": "products",
    }

    mock_server.solr_client.realtime_get.return_value = expected_result

    result = await execute_realtime_get(
        mock_server, collection="products", doc_ids=["NONEXISTENT"]
    )

    assert result["num_found"] == 0
    assert len(result["docs"]) == 0


@pytest.mark.asyncio
async def test_realtime_get_partial_results(mock_server):
    """Test real-time get when some docs exist and others don't."""
    expected_result = {
        "docs": [
            {"id": "PROD-123", "name": "Product 1"},
            # PROD-MISSING not in results
            {"id": "PROD-456", "name": "Product 2"},
        ],
        "num_found": 2,
        "collection": "products",
    }

    mock_server.solr_client.realtime_get.return_value = expected_result

    result = await execute_realtime_get(
        mock_server,
        collection="products",
        doc_ids=["PROD-123", "PROD-MISSING", "PROD-456"],
    )

    assert result["num_found"] == 2
    assert len(result["docs"]) == 2


@pytest.mark.asyncio
async def test_realtime_get_error_handling(mock_server):
    """Test realtime get error handling."""
    error_message = "Real-time get failed"
    mock_server.solr_client.realtime_get.side_effect = SolrError(error_message)

    with pytest.raises(SolrError, match="Real-time get failed"):
        await execute_realtime_get(
            mock_server, collection="products", doc_ids=["PROD-123"]
        )


# Integration-style tests combining features
@pytest.mark.asyncio
async def test_workflow_atomic_update_and_realtime_get(mock_server):
    """Test workflow: atomic update followed by realtime get."""
    # Atomic update
    update_result = {
        "status": "success",
        "doc_id": "PROD-123",
        "collection": "products",
        "version": 50,
        "updates_applied": 1,
    }
    mock_server.solr_client.atomic_update.return_value = update_result

    update_response = await execute_atomic_update(
        mock_server,
        collection="products",
        doc_id="PROD-123",
        updates={"price": {"set": 19.99}},
        commit=False,
    )
    assert update_response["status"] == "success"

    # Realtime get (can see uncommitted change)
    get_result = {
        "docs": [{"id": "PROD-123", "price": 19.99}],
        "num_found": 1,
        "collection": "products",
    }
    mock_server.solr_client.realtime_get.return_value = get_result

    get_response = await execute_realtime_get(
        mock_server, collection="products", doc_ids=["PROD-123"]
    )

    assert get_response["docs"][0]["price"] == 19.99


@pytest.mark.asyncio
async def test_workflow_update_soft_commit_hard_commit(mock_server):
    """Test workflow: update, soft commit, hard commit."""
    # Update
    update_result = {
        "status": "success",
        "doc_id": "PROD-123",
        "collection": "products",
        "version": 51,
        "updates_applied": 1,
    }
    mock_server.solr_client.atomic_update.return_value = update_result

    await execute_atomic_update(
        mock_server,
        collection="products",
        doc_id="PROD-123",
        updates={"stock": {"inc": -1}},
        commit=False,
    )

    # Soft commit for visibility
    soft_commit_result = {
        "status": "success",
        "collection": "products",
        "commit_type": "soft",
        "committed": True,
    }
    mock_server.solr_client.commit.return_value = soft_commit_result

    soft_response = await execute_commit(
        mock_server, collection="products", soft=True
    )
    assert soft_response["commit_type"] == "soft"

    # Hard commit for durability
    hard_commit_result = {
        "status": "success",
        "collection": "products",
        "commit_type": "hard",
        "committed": True,
    }
    mock_server.solr_client.commit.return_value = hard_commit_result

    hard_response = await execute_commit(
        mock_server, collection="products", soft=False
    )
    assert hard_response["commit_type"] == "hard"
