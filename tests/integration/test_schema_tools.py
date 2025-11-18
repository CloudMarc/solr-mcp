"""Integration tests for Schema Management Tools.

Tests the new schema manipulation features added in this PR.
"""

import logging
import os
import sys

import pytest
import pytest_asyncio


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import contextlib

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


@pytest.mark.asyncio
async def test_schema_list_fields(solr_client):
    """Test listing all fields in a collection schema."""
    result = await solr_client.get_schema_fields(TEST_COLLECTION)

    logger.info(f"Schema list fields returned: {len(result.get('fields', []))} fields")

    assert "fields" in result, "Result should contain 'fields' key"
    assert isinstance(result["fields"], list), "Fields should be a list"
    assert len(result["fields"]) > 0, "Should have at least some fields"

    # Check for common fields
    field_names = [f.get("name") for f in result["fields"]]
    assert "id" in field_names, "Should have 'id' field"
    assert "_version_" in field_names, "Should have '_version_' field"


@pytest.mark.asyncio
async def test_schema_get_specific_field(solr_client):
    """Test getting details of a specific field."""
    result = await solr_client.get_schema_field(TEST_COLLECTION, "id")

    logger.info(f"Schema get field returned: {result}")

    assert "field" in result, "Result should contain 'field' key"
    assert result["field"]["name"] == "id", "Field name should be 'id'"
    assert "type" in result["field"], "Field should have a type"


@pytest.mark.asyncio
async def test_schema_add_and_delete_field(solr_client):
    """Test adding and deleting a custom field."""
    test_field_name = "test_integration_field"

    # First, try to delete if it exists (cleanup from previous runs)
    try:
        await solr_client.delete_schema_field(TEST_COLLECTION, test_field_name)
        logger.info(f"Cleaned up existing field: {test_field_name}")
    except Exception:
        pass  # Field might not exist, that's fine

    # Add a new field
    add_result = await solr_client.add_schema_field(
        collection=TEST_COLLECTION,
        field_name=test_field_name,
        field_type="text_general",
        stored=True,
        indexed=True,
        multiValued=False,
    )

    logger.info(f"Add field result: {add_result}")
    assert "responseHeader" in add_result, "Should have response header"
    assert add_result["responseHeader"]["status"] == 0, "Add should succeed"

    # Verify field was added by getting it
    get_result = await solr_client.get_schema_field(TEST_COLLECTION, test_field_name)
    assert "field" in get_result, "Should be able to get the new field"
    assert get_result["field"]["name"] == test_field_name, "Field name should match"
    assert get_result["field"]["type"] == "text_general", "Field type should match"

    # Delete the field
    delete_result = await solr_client.delete_schema_field(
        TEST_COLLECTION, test_field_name
    )

    logger.info(f"Delete field result: {delete_result}")
    assert "responseHeader" in delete_result, "Should have response header"
    assert delete_result["responseHeader"]["status"] == 0, "Delete should succeed"

    # Verify field was deleted
    try:
        await solr_client.get_schema_field(TEST_COLLECTION, test_field_name)
        pytest.fail("Should not be able to get deleted field")
    except Exception as e:
        logger.info(f"Expected error getting deleted field: {e}")
        # This is expected


@pytest.mark.asyncio
async def test_add_schema_field_with_different_types(solr_client):
    """Test adding fields with different types."""
    test_fields = [
        {"name": "test_int_field", "type": "plong", "cleanup": True},
        {"name": "test_string_field", "type": "string", "cleanup": True},
        {"name": "test_boolean_field", "type": "boolean", "cleanup": True},
    ]

    for field_spec in test_fields:
        field_name = field_spec["name"]
        field_type = field_spec["type"]

        # Cleanup
        with contextlib.suppress(Exception):
            await solr_client.delete_schema_field(TEST_COLLECTION, field_name)

        # Add field
        result = await solr_client.add_schema_field(
            collection=TEST_COLLECTION,
            field_name=field_name,
            field_type=field_type,
            stored=True,
            indexed=True,
        )

        assert result["responseHeader"]["status"] == 0, f"Should add {field_type} field"

        # Verify
        get_result = await solr_client.get_schema_field(TEST_COLLECTION, field_name)
        assert get_result["field"]["type"] == field_type, f"Type should be {field_type}"

        # Cleanup
        if field_spec.get("cleanup"):
            await solr_client.delete_schema_field(TEST_COLLECTION, field_name)


@pytest.mark.asyncio
async def test_schema_error_handling_duplicate_field(solr_client):
    """Test error handling when adding duplicate field."""
    # Try to add 'id' field which already exists
    try:
        await solr_client.add_schema_field(
            collection=TEST_COLLECTION,
            field_name="id",
            field_type="string",
            stored=True,
            indexed=True,
        )
        pytest.fail("Should not be able to add duplicate field")
    except Exception as e:
        logger.info(f"Expected error for duplicate field: {e}")
        # This is expected


@pytest.mark.asyncio
async def test_schema_error_handling_invalid_field_type(solr_client):
    """Test error handling for invalid field type."""
    try:
        await solr_client.add_schema_field(
            collection=TEST_COLLECTION,
            field_name="test_invalid_type",
            field_type="non_existent_type_xyz",
            stored=True,
            indexed=True,
        )
        pytest.fail("Should not be able to add field with invalid type")
    except Exception as e:
        logger.info(f"Expected error for invalid field type: {e}")
        # This is expected


@pytest.mark.asyncio
async def test_schema_multivalue_field(solr_client):
    """Test adding a multi-valued field."""
    field_name = "test_multivalue_field"

    # Cleanup
    with contextlib.suppress(Exception):
        await solr_client.delete_schema_field(TEST_COLLECTION, field_name)

    # Add multi-valued field
    result = await solr_client.add_schema_field(
        collection=TEST_COLLECTION,
        field_name=field_name,
        field_type="string",  # Use string type with multiValued=True
        stored=True,
        indexed=True,
        multiValued=True,
    )

    assert result["responseHeader"]["status"] == 0, "Should add multiValued field"

    # Verify
    get_result = await solr_client.get_schema_field(TEST_COLLECTION, field_name)
    assert get_result["field"].get("multiValued", False), "Field should be multiValued"

    # Cleanup
    await solr_client.delete_schema_field(TEST_COLLECTION, field_name)
