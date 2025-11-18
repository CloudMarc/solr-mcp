"""Integration tests for Indexing Tools.

Tests the new indexing features: atomic updates, real-time get, commits, etc.
"""

import logging
import os
import sys
import time
import uuid

import pytest
import pytest_asyncio


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from solr_mcp.solr.client import SolrClient
from solr_mcp.solr.config import SolrConfig


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

TEST_COLLECTION = os.getenv("TEST_COLLECTION", "unified")
SOLR_BASE_URL = os.getenv("SOLR_BASE_URL", "http://localhost:8983/solr")


@pytest_asyncio.fixture
async def solr_client():
    """Create SolrClient for testing."""
    config = SolrConfig(
        solr_base_url=SOLR_BASE_URL,
        zookeeper_hosts=["localhost:2181"],
        default_collection=TEST_COLLECTION,
    )
    client = SolrClient(config=config)
    try:
        yield client
    finally:
        if hasattr(client, "close"):
            await client.close()


def generate_test_doc(prefix="test"):
    """Generate a unique test document."""
    doc_id = f"{prefix}_{uuid.uuid4().hex[:8]}"
    return {
        "id": doc_id,
        "title": f"Test Document {doc_id}",
        "text": "This is a test document for integration testing",
        "test_score": 100,
    }


@pytest.mark.asyncio
async def test_add_documents(solr_client):
    """Test adding documents to a collection."""
    doc = generate_test_doc("add_test")

    result = await solr_client.add_documents(
        collection=TEST_COLLECTION, documents=[doc]
    )

    logger.info(f"Add documents result: {result}")
    assert "responseHeader" in result, "Should have response header"
    assert result["responseHeader"]["status"] == 0, "Add should succeed"

    # Commit to make it visible
    await solr_client.commit(TEST_COLLECTION)

    # Verify document was added
    query = f"SELECT * FROM {TEST_COLLECTION} WHERE id = '{doc['id']}' LIMIT 10"
    search_result = await solr_client.execute_select_query(query)

    assert "result-set" in search_result, "Should have result-set"
    docs = search_result["result-set"]["docs"]
    assert len(docs) > 0, "Should find the added document"
    assert docs[0]["id"] == doc["id"], "Document ID should match"

    # Cleanup
    await solr_client.delete_documents(TEST_COLLECTION, ids=[doc["id"]])
    await solr_client.commit(TEST_COLLECTION)


@pytest.mark.asyncio
async def test_realtime_get_uncommitted(solr_client):
    """Test real-time get for uncommitted documents."""
    doc = generate_test_doc("rtg_test")

    # Add document without committing
    await solr_client.add_documents(collection=TEST_COLLECTION, documents=[doc])

    # Get document with real-time get (should work even without commit)
    result = await solr_client.realtime_get(TEST_COLLECTION, ids=[doc["id"]])

    logger.info(f"Real-time get result: {result}")
    assert "doc" in result or "response" in result, "Should have document data"

    # Extract the document
    if "doc" in result:
        retrieved_doc = result["doc"]
    else:
        docs = result.get("response", {}).get("docs", [])
        assert len(docs) > 0, "Should retrieve uncommitted document"
        retrieved_doc = docs[0]

    assert retrieved_doc["id"] == doc["id"], "Should retrieve correct document"

    # Cleanup
    await solr_client.delete_documents(TEST_COLLECTION, ids=[doc["id"]])
    await solr_client.commit(TEST_COLLECTION)


@pytest.mark.asyncio
async def test_soft_vs_hard_commit(solr_client):
    """Test soft commit (visibility) vs hard commit (durability)."""
    doc = generate_test_doc("commit_test")

    # Add document
    await solr_client.add_documents(collection=TEST_COLLECTION, documents=[doc])

    # Soft commit (makes visible but not durable)
    soft_result = await solr_client.commit(TEST_COLLECTION, soft_commit=True)
    assert soft_result["responseHeader"]["status"] == 0, "Soft commit should succeed"

    # Document should be searchable after soft commit
    time.sleep(0.5)  # Give it a moment
    query = f"SELECT * FROM {TEST_COLLECTION} WHERE id = '{doc['id']}' LIMIT 10"
    search_result = await solr_client.execute_select_query(query)
    docs = search_result["result-set"]["docs"]
    assert len(docs) > 0, "Document should be visible after soft commit"

    # Hard commit (durability)
    hard_result = await solr_client.commit(TEST_COLLECTION, soft_commit=False)
    assert hard_result["responseHeader"]["status"] == 0, "Hard commit should succeed"

    # Cleanup
    await solr_client.delete_documents(TEST_COLLECTION, ids=[doc["id"]])
    await solr_client.commit(TEST_COLLECTION)


@pytest.mark.asyncio
async def test_atomic_update_set(solr_client):
    """Test atomic update with 'set' operation."""
    doc = generate_test_doc("atomic_set")

    # Add initial document
    await solr_client.add_documents(collection=TEST_COLLECTION, documents=[doc])
    await solr_client.commit(TEST_COLLECTION)

    # Atomic update - set title to new value
    new_title = "Updated Title via Atomic Update"
    update_result = await solr_client.atomic_update(
        collection=TEST_COLLECTION,
        doc_id=doc["id"],
        updates={"title": {"set": new_title}},
    )

    logger.info(f"Atomic update result: {update_result}")
    assert update_result["responseHeader"]["status"] == 0, "Update should succeed"

    # Commit and verify
    await solr_client.commit(TEST_COLLECTION)

    query = f"SELECT * FROM {TEST_COLLECTION} WHERE id = '{doc['id']}' LIMIT 10"
    search_result = await solr_client.execute_select_query(query)
    docs = search_result["result-set"]["docs"]

    assert len(docs) > 0, "Should find updated document"
    # Solr may return multi-valued fields as lists
    title = docs[0]["title"]
    if isinstance(title, list):
        title = title[0]
    assert title == new_title, "Title should be updated"
    text = docs[0]["text"]
    if isinstance(text, list):
        text = text[0]
    assert text == doc["text"], "Text should remain unchanged"

    # Cleanup
    await solr_client.delete_documents(TEST_COLLECTION, ids=[doc["id"]])
    await solr_client.commit(TEST_COLLECTION)


@pytest.mark.asyncio
async def test_atomic_update_inc(solr_client):
    """Test atomic update with 'inc' (increment) operation."""
    doc = generate_test_doc("atomic_inc")
    doc["test_score"] = 100

    # Add initial document
    await solr_client.add_documents(collection=TEST_COLLECTION, documents=[doc])
    await solr_client.commit(TEST_COLLECTION)

    # Atomic update - increment test_score
    update_result = await solr_client.atomic_update(
        collection=TEST_COLLECTION,
        doc_id=doc["id"],
        updates={"test_score": {"inc": 50}},
    )

    assert update_result["responseHeader"]["status"] == 0, "Update should succeed"

    # Commit and verify
    await solr_client.commit(TEST_COLLECTION)

    query = f"SELECT * FROM {TEST_COLLECTION} WHERE id = '{doc['id']}' LIMIT 10"
    search_result = await solr_client.execute_select_query(query)
    docs = search_result["result-set"]["docs"]

    assert len(docs) > 0, "Should find updated document"
    assert docs[0]["test_score"] == 150, "Score should be incremented"

    # Cleanup
    await solr_client.delete_documents(TEST_COLLECTION, ids=[doc["id"]])
    await solr_client.commit(TEST_COLLECTION)


@pytest.mark.asyncio
async def test_delete_by_id(solr_client):
    """Test deleting documents by ID."""
    doc = generate_test_doc("delete_id")

    # Add document
    await solr_client.add_documents(collection=TEST_COLLECTION, documents=[doc])
    await solr_client.commit(TEST_COLLECTION)

    # Delete by ID
    delete_result = await solr_client.delete_documents(
        collection=TEST_COLLECTION, ids=[doc["id"]]
    )

    logger.info(f"Delete result: {delete_result}")
    assert delete_result["responseHeader"]["status"] == 0, "Delete should succeed"

    # Commit
    await solr_client.commit(TEST_COLLECTION)

    # Verify deletion
    query = f"SELECT id FROM {TEST_COLLECTION} WHERE id = '{doc['id']}' LIMIT 10"
    search_result = await solr_client.execute_select_query(query)
    docs = search_result["result-set"]["docs"]

    # Filter out EOF markers from Solr SQL
    docs = [d for d in docs if "EOF" not in d]
    assert len(docs) == 0, "Document should be deleted"


@pytest.mark.asyncio
async def test_delete_by_query(solr_client):
    """Test deleting documents by query."""
    # Create multiple test documents with a unique marker
    marker = f"delete_query_{uuid.uuid4().hex[:8]}"
    docs = [
        {
            "id": f"{marker}_{i}",
            "title": f"Delete Query Test {i}",
            "text": f"Test document with marker {marker}",
        }
        for i in range(3)
    ]

    # Add documents
    await solr_client.add_documents(collection=TEST_COLLECTION, documents=docs)
    await solr_client.commit(TEST_COLLECTION)

    # Delete by query
    delete_query = f"text:{marker}"
    delete_result = await solr_client.delete_documents(
        collection=TEST_COLLECTION, query=delete_query
    )

    logger.info(f"Delete by query result: {delete_result}")
    assert delete_result["responseHeader"]["status"] == 0, "Delete should succeed"

    # Commit
    await solr_client.commit(TEST_COLLECTION)

    # Verify all documents with marker are deleted
    query = f"SELECT id FROM {TEST_COLLECTION} WHERE text:{marker} LIMIT 10"
    search_result = await solr_client.execute_select_query(query)
    docs_found = search_result["result-set"]["docs"]

    # Filter out EOF markers from Solr SQL
    docs_found = [d for d in docs_found if "EOF" not in d]
    assert len(docs_found) == 0, "All matching documents should be deleted"


@pytest.mark.asyncio
async def test_batch_add_documents(solr_client):
    """Test adding multiple documents in a batch."""
    marker = f"batch_{uuid.uuid4().hex[:8]}"
    docs = [
        {
            "id": f"{marker}_{i}",
            "title": f"Batch Document {i}",
            "text": f"Batch test document {i} with marker {marker}",
        }
        for i in range(10)
    ]

    # Add batch
    result = await solr_client.add_documents(collection=TEST_COLLECTION, documents=docs)

    assert result["responseHeader"]["status"] == 0, "Batch add should succeed"

    # Commit
    await solr_client.commit(TEST_COLLECTION)

    # Verify all documents were added
    query = f"SELECT id FROM {TEST_COLLECTION} WHERE text:{marker} LIMIT 20"
    search_result = await solr_client.execute_select_query(query)
    docs_found = search_result["result-set"]["docs"]

    # Filter out EOF markers from Solr SQL
    docs_found = [d for d in docs_found if "EOF" not in d]
    assert len(docs_found) == 10, "Should add all 10 documents"

    # Cleanup
    ids = [doc["id"] for doc in docs]
    await solr_client.delete_documents(TEST_COLLECTION, ids=ids)
    await solr_client.commit(TEST_COLLECTION)


@pytest.mark.asyncio
async def test_optimistic_concurrency_version(solr_client):
    """Test optimistic concurrency control with _version_ field."""
    doc = generate_test_doc("version_test")

    # Add document
    await solr_client.add_documents(collection=TEST_COLLECTION, documents=[doc])
    await solr_client.commit(TEST_COLLECTION)

    # Get document with version
    rtg_result = await solr_client.realtime_get(TEST_COLLECTION, ids=[doc["id"]])

    if "doc" in rtg_result:
        retrieved_doc = rtg_result["doc"]
    else:
        retrieved_doc = rtg_result["response"]["docs"][0]

    version = retrieved_doc.get("_version_")
    logger.info(f"Document version: {version}")

    assert version is not None, "Document should have a version"

    # Try to update with correct version (should succeed)
    update_result = await solr_client.atomic_update(
        collection=TEST_COLLECTION,
        doc_id=doc["id"],
        updates={"title": {"set": "Updated with version"}},
        version=version,
    )

    assert update_result["responseHeader"]["status"] == 0, (
        "Update with correct version should succeed"
    )

    # Try to update with wrong version (should fail)
    try:
        await solr_client.atomic_update(
            collection=TEST_COLLECTION,
            doc_id=doc["id"],
            updates={"title": {"set": "Should fail"}},
            version=version,  # Using old version
        )
        pytest.fail("Update with old version should fail")
    except Exception as e:
        logger.info(f"Expected version conflict error: {e}")
        # This is expected

    # Cleanup
    await solr_client.delete_documents(TEST_COLLECTION, ids=[doc["id"]])
    await solr_client.commit(TEST_COLLECTION)
