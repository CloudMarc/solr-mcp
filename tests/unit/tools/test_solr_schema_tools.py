"""Tests for the schema API tools."""

import pytest

from solr_mcp.solr.exceptions import SolrError
from solr_mcp.tools.solr_schema_add_field import execute_schema_add_field
from solr_mcp.tools.solr_schema_delete_field import execute_schema_delete_field
from solr_mcp.tools.solr_schema_get_field import execute_schema_get_field
from solr_mcp.tools.solr_schema_list_fields import execute_schema_list_fields


# Tests for solr_schema_add_field
@pytest.mark.asyncio
async def test_schema_add_field_basic(mock_server):
    """Test adding a basic field to schema."""
    expected_result = {
        "status": "success",
        "field": {
            "name": "summary",
            "type": "text_general",
            "stored": True,
            "indexed": True,
            "required": False,
            "multiValued": False,
        },
        "collection": "test_collection",
    }

    mock_server.solr_client.add_schema_field.return_value = expected_result

    result = await execute_schema_add_field(
        mock_server,
        collection="test_collection",
        field_name="summary",
        field_type="text_general",
    )

    assert result["status"] == "success"
    assert result["field"]["name"] == "summary"
    assert result["collection"] == "test_collection"


@pytest.mark.asyncio
async def test_schema_add_field_with_docvalues(mock_server):
    """Test adding a field with docValues enabled."""
    expected_result = {
        "status": "success",
        "field": {
            "name": "price",
            "type": "pfloat",
            "stored": True,
            "indexed": True,
            "required": False,
            "multiValued": False,
            "docValues": True,
        },
        "collection": "products",
    }

    mock_server.solr_client.add_schema_field.return_value = expected_result

    result = await execute_schema_add_field(
        mock_server,
        collection="products",
        field_name="price",
        field_type="pfloat",
        docValues=True,
    )

    assert result["field"]["docValues"] is True
    assert result["field"]["type"] == "pfloat"


@pytest.mark.asyncio
async def test_schema_add_field_multivalued(mock_server):
    """Test adding a multivalued field."""
    expected_result = {
        "status": "success",
        "field": {
            "name": "tags",
            "type": "string",
            "stored": True,
            "indexed": True,
            "required": False,
            "multiValued": True,
        },
        "collection": "test_collection",
    }

    mock_server.solr_client.add_schema_field.return_value = expected_result

    result = await execute_schema_add_field(
        mock_server,
        collection="test_collection",
        field_name="tags",
        field_type="string",
        multiValued=True,
    )

    assert result["field"]["multiValued"] is True


@pytest.mark.asyncio
async def test_schema_add_field_required(mock_server):
    """Test adding a required field."""
    expected_result = {
        "status": "success",
        "field": {
            "name": "user_id",
            "type": "string",
            "stored": True,
            "indexed": True,
            "required": True,
            "multiValued": False,
        },
        "collection": "users",
    }

    mock_server.solr_client.add_schema_field.return_value = expected_result

    result = await execute_schema_add_field(
        mock_server,
        collection="users",
        field_name="user_id",
        field_type="string",
        required=True,
    )

    assert result["field"]["required"] is True


@pytest.mark.asyncio
async def test_schema_add_field_error(mock_server):
    """Test error handling when adding a field."""
    error_message = "Field already exists"
    mock_server.solr_client.add_schema_field.side_effect = SolrError(error_message)

    with pytest.raises(SolrError, match=error_message):
        await execute_schema_add_field(
            mock_server,
            collection="test_collection",
            field_name="existing_field",
            field_type="string",
        )


# Tests for solr_schema_list_fields
@pytest.mark.asyncio
async def test_schema_list_fields_basic(mock_server):
    """Test listing all schema fields."""
    expected_result = {
        "fields": [
            {
                "name": "id",
                "type": "string",
                "stored": True,
                "indexed": True,
            },
            {
                "name": "title",
                "type": "text_general",
                "stored": True,
                "indexed": True,
            },
            {
                "name": "price",
                "type": "pfloat",
                "stored": True,
                "indexed": True,
                "docValues": True,
            },
        ],
        "collection": "test_collection",
        "total_fields": 3,
    }

    mock_server.solr_client.get_schema_fields.return_value = expected_result

    result = await execute_schema_list_fields(mock_server, collection="test_collection")

    assert result["total_fields"] == 3
    assert len(result["fields"]) == 3
    assert result["fields"][0]["name"] == "id"


@pytest.mark.asyncio
async def test_schema_list_fields_empty(mock_server):
    """Test listing fields when collection has no custom fields."""
    expected_result = {
        "fields": [],
        "collection": "empty_collection",
        "total_fields": 0,
    }

    mock_server.solr_client.get_schema_fields.return_value = expected_result

    result = await execute_schema_list_fields(
        mock_server, collection="empty_collection"
    )

    assert result["total_fields"] == 0
    assert len(result["fields"]) == 0


@pytest.mark.asyncio
async def test_schema_list_fields_error(mock_server):
    """Test error handling when listing fields."""
    error_message = "Collection not found"
    mock_server.solr_client.get_schema_fields.side_effect = SolrError(error_message)

    with pytest.raises(SolrError, match=error_message):
        await execute_schema_list_fields(
            mock_server, collection="nonexistent_collection"
        )


# Tests for solr_schema_get_field
@pytest.mark.asyncio
async def test_schema_get_field_basic(mock_server):
    """Test getting a specific field from schema."""
    expected_result = {
        "field": {
            "name": "title",
            "type": "text_general",
            "stored": True,
            "indexed": True,
            "multiValued": False,
        },
        "collection": "test_collection",
    }

    mock_server.solr_client.get_schema_field.return_value = expected_result

    result = await execute_schema_get_field(
        mock_server, collection="test_collection", field_name="title"
    )

    assert result["field"]["name"] == "title"
    assert result["field"]["type"] == "text_general"
    assert result["collection"] == "test_collection"


@pytest.mark.asyncio
async def test_schema_get_field_with_docvalues(mock_server):
    """Test getting a field with docValues."""
    expected_result = {
        "field": {
            "name": "rating",
            "type": "pfloat",
            "stored": True,
            "indexed": True,
            "docValues": True,
        },
        "collection": "products",
    }

    mock_server.solr_client.get_schema_field.return_value = expected_result

    result = await execute_schema_get_field(
        mock_server, collection="products", field_name="rating"
    )

    assert result["field"]["docValues"] is True


@pytest.mark.asyncio
async def test_schema_get_field_not_found(mock_server):
    """Test getting a non-existent field."""
    error_message = "Field 'nonexistent' not found"
    mock_server.solr_client.get_schema_field.side_effect = SolrError(error_message)

    with pytest.raises(SolrError, match=error_message):
        await execute_schema_get_field(
            mock_server, collection="test_collection", field_name="nonexistent"
        )


# Tests for solr_schema_delete_field
@pytest.mark.asyncio
async def test_schema_delete_field_basic(mock_server):
    """Test deleting a field from schema."""
    expected_result = {
        "status": "success",
        "field_name": "old_field",
        "collection": "test_collection",
    }

    mock_server.solr_client.delete_schema_field.return_value = expected_result

    result = await execute_schema_delete_field(
        mock_server, collection="test_collection", field_name="old_field"
    )

    assert result["status"] == "success"
    assert result["field_name"] == "old_field"
    assert result["collection"] == "test_collection"


@pytest.mark.asyncio
async def test_schema_delete_field_error(mock_server):
    """Test error handling when deleting a field."""
    error_message = "Cannot delete required field"
    mock_server.solr_client.delete_schema_field.side_effect = SolrError(error_message)

    with pytest.raises(SolrError, match=error_message):
        await execute_schema_delete_field(
            mock_server, collection="test_collection", field_name="id"
        )


@pytest.mark.asyncio
async def test_schema_delete_field_not_found(mock_server):
    """Test deleting a non-existent field."""
    error_message = "Field 'nonexistent' not found"
    mock_server.solr_client.delete_schema_field.side_effect = SolrError(error_message)

    with pytest.raises(SolrError, match=error_message):
        await execute_schema_delete_field(
            mock_server, collection="test_collection", field_name="nonexistent"
        )


# Integration-style tests
@pytest.mark.asyncio
async def test_schema_workflow_add_list_get_delete(mock_server):
    """Test complete schema workflow: add, list, get, delete."""
    # Add field
    add_result = {
        "status": "success",
        "field": {"name": "temp_field", "type": "string"},
        "collection": "test_collection",
    }
    mock_server.solr_client.add_schema_field.return_value = add_result

    result = await execute_schema_add_field(
        mock_server,
        collection="test_collection",
        field_name="temp_field",
        field_type="string",
    )
    assert result["status"] == "success"

    # List fields
    list_result = {
        "fields": [{"name": "temp_field", "type": "string"}],
        "collection": "test_collection",
        "total_fields": 1,
    }
    mock_server.solr_client.get_schema_fields.return_value = list_result

    result = await execute_schema_list_fields(mock_server, collection="test_collection")
    assert "temp_field" in [f["name"] for f in result["fields"]]

    # Get field
    get_result = {
        "field": {"name": "temp_field", "type": "string"},
        "collection": "test_collection",
    }
    mock_server.solr_client.get_schema_field.return_value = get_result

    result = await execute_schema_get_field(
        mock_server, collection="test_collection", field_name="temp_field"
    )
    assert result["field"]["name"] == "temp_field"

    # Delete field
    delete_result = {
        "status": "success",
        "field_name": "temp_field",
        "collection": "test_collection",
    }
    mock_server.solr_client.delete_schema_field.return_value = delete_result

    result = await execute_schema_delete_field(
        mock_server, collection="test_collection", field_name="temp_field"
    )
    assert result["status"] == "success"
