"""Tests for SolrClient."""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import aiohttp
import pysolr
import pytest
import requests
from aiohttp import test_utils

from solr_mcp.solr.client import SolrClient
from solr_mcp.solr.exceptions import (
    ConnectionError,
    DocValuesError,
    QueryError,
    SolrError,
    SQLExecutionError,
    SQLParseError,
)


@pytest.mark.asyncio
async def test_init_with_defaults(mock_config):
    """Test initialization with only config."""
    # Set zookeeper_hosts to None to use HTTP provider instead of trying to connect to ZK
    mock_config.zookeeper_hosts = None
    
    client = SolrClient(config=mock_config)
    assert client.config == mock_config


@pytest.mark.asyncio
async def test_init_with_custom_providers(
    client,
    mock_config,
    mock_collection_provider,
    mock_field_manager,
    mock_vector_provider,
    mock_query_builder,
):
    """Test initialization with custom providers."""
    assert client.config == mock_config
    assert client.collection_provider == mock_collection_provider
    assert client.field_manager == mock_field_manager
    assert client.vector_provider == mock_vector_provider
    assert client.query_builder == mock_query_builder


@pytest.mark.asyncio
async def test_get_or_create_client_with_collection(client):
    """Test getting Solr client with specific collection."""
    solr_client = await client._get_or_create_client("test_collection")
    assert solr_client is not None


@pytest.mark.asyncio
async def test_get_or_create_client_with_different_collection(client):
    """Test getting Solr client with a different collection."""
    solr_client = await client._get_or_create_client("another_collection")
    assert solr_client is not None


@pytest.mark.asyncio
async def test_get_or_create_client_no_collection(mock_config):
    """Test error when no collection specified."""
    # Set zookeeper_hosts to None to use HTTP provider instead of trying to connect to ZK
    mock_config.zookeeper_hosts = None
    
    client = SolrClient(config=mock_config)
    with pytest.raises(SolrError):
        await client._get_or_create_client(None)


@pytest.mark.asyncio
async def test_list_collections_success(client):
    """Test successful collection listing."""
    # Mock the collection provider's list_collections method
    expected_collections = ["test_collection"]
    client.collection_provider.list_collections = AsyncMock(
        return_value=expected_collections
    )

    # Test the method
    result = await client.list_collections()
    assert result == expected_collections

    # Verify the collection provider was called
    client.collection_provider.list_collections.assert_called_once()


@pytest.mark.asyncio
async def test_list_fields_schema_error(client):
    """Test schema error handling in list_fields."""
    # Mock field_manager.list_fields to raise an error
    client.field_manager.list_fields = AsyncMock(side_effect=SolrError("Schema error"))

    # Test that the error is propagated
    with pytest.raises(SolrError):
        await client.list_fields("test_collection")


@pytest.mark.asyncio
async def test_execute_select_query_success(client):
    """Test successful SQL query execution."""
    # Mock parser.preprocess_query
    client.query_builder.parser.preprocess_query = Mock(
        return_value="SELECT * FROM test_collection"
    )

    # Mock the parse_and_validate_select
    client.query_builder.parse_and_validate_select = Mock(
        return_value=(Mock(), "test_collection", None)
    )

    # Mock the query executor
    expected_result = {
        "result-set": {"docs": [{"id": "1", "title": "Test"}], "numFound": 1}
    }
    client.query_executor.execute_select_query = AsyncMock(return_value=expected_result)

    # Execute the query
    result = await client.execute_select_query("SELECT * FROM test_collection")

    # Verify the result
    assert result == expected_result
    client.query_executor.execute_select_query.assert_called_once_with(
        query="SELECT * FROM test_collection", collection="test_collection"
    )


@pytest.mark.asyncio
async def test_execute_select_query_docvalues_error(client):
    """Test SQL query with DocValues error."""
    # Mock parser.preprocess_query
    client.query_builder.parser.preprocess_query = Mock(
        return_value="SELECT * FROM test_collection"
    )

    # Mock the parse_and_validate_select
    client.query_builder.parse_and_validate_select = Mock(
        return_value=(Mock(), "test_collection", None)
    )

    # Mock the query executor to raise a DocValuesError
    client.query_executor.execute_select_query = AsyncMock(
        side_effect=DocValuesError("must have DocValues to use this feature", 10)
    )

    # Execute the query and verify the error
    with pytest.raises(DocValuesError):
        await client.execute_select_query("SELECT * FROM test_collection")


@pytest.mark.asyncio
async def test_execute_select_query_parse_error(client):
    """Test SQL query with parse error."""
    # Mock parser.preprocess_query
    client.query_builder.parser.preprocess_query = Mock(return_value="INVALID SQL")

    # Mock the parse_and_validate_select
    client.query_builder.parse_and_validate_select = Mock(
        return_value=(Mock(), "test_collection", None)
    )

    # Mock the query executor to raise a SQLParseError
    client.query_executor.execute_select_query = AsyncMock(
        side_effect=SQLParseError("parse failed: syntax error", 10)
    )

    # Execute the query and verify the error
    with pytest.raises(SQLParseError):
        await client.execute_select_query("INVALID SQL")


@pytest.mark.asyncio
async def test_list_collections_error(client):
    """Test error handling in list_collections."""
    # Mock the collection provider to raise an error
    client.collection_provider.list_collections = AsyncMock(
        side_effect=Exception("Connection failed")
    )

    # Test that the error is wrapped
    with pytest.raises(SolrError) as exc_info:
        await client.list_collections()
    
    assert "Failed to list collections" in str(exc_info.value)


@pytest.mark.asyncio
async def test_list_fields_success(client):
    """Test successful field listing."""
    # Mock the field_manager's list_fields method
    expected_fields = [{"name": "id", "type": "string"}, {"name": "title", "type": "text_general"}]
    client.field_manager.list_fields = AsyncMock(return_value=expected_fields)

    # Test the method
    result = await client.list_fields("test_collection")
    assert result == expected_fields

    # Verify the field manager was called
    client.field_manager.list_fields.assert_called_once_with("test_collection")


@pytest.mark.asyncio
async def test_list_fields_error(client):
    """Test error handling in list_fields."""
    # Mock field_manager.list_fields to raise a generic error
    client.field_manager.list_fields = AsyncMock(side_effect=Exception("Network error"))

    # Test that the error is wrapped
    with pytest.raises(SolrError) as exc_info:
        await client.list_fields("test_collection")
    
    assert "Failed to list fields for collection 'test_collection'" in str(exc_info.value)


@pytest.mark.asyncio
async def test_execute_select_query_sql_execution_error(client):
    """Test SQL query with execution error."""
    # Mock parser.preprocess_query
    client.query_builder.parser.preprocess_query = Mock(
        return_value="SELECT * FROM test_collection"
    )

    # Mock the parse_and_validate_select
    client.query_builder.parse_and_validate_select = Mock(
        return_value=(Mock(), "test_collection", None)
    )

    # Mock the query executor to raise a SQLExecutionError
    client.query_executor.execute_select_query = AsyncMock(
        side_effect=SQLExecutionError("execution failed", 10)
    )

    # Execute the query and verify the error
    with pytest.raises(SQLExecutionError):
        await client.execute_select_query("SELECT * FROM test_collection")


@pytest.mark.asyncio
async def test_execute_select_query_generic_error(client):
    """Test SQL query with generic error."""
    # Mock parser.preprocess_query
    client.query_builder.parser.preprocess_query = Mock(
        return_value="SELECT * FROM test_collection"
    )

    # Mock the parse_and_validate_select to raise a generic error
    client.query_builder.parse_and_validate_select = Mock(
        side_effect=Exception("Unexpected error")
    )

    # Execute the query and verify the error is wrapped
    with pytest.raises(SQLExecutionError) as exc_info:
        await client.execute_select_query("SELECT * FROM test_collection")
    
    assert "SQL query failed" in str(exc_info.value)


@pytest.mark.asyncio
async def test_execute_vector_select_query_success(client):
    """Test successful vector select query execution."""
    # Mock the AST with limit
    mock_ast = Mock()
    mock_ast.args = {"limit": Mock(expression=Mock(this="5")), "offset": 0}
    
    # Mock parser and validator
    client.query_builder.parse_and_validate_select = Mock(
        return_value=(mock_ast, "test_collection", None)
    )
    
    # Mock vector manager validation
    client.vector_manager.validate_vector_field = AsyncMock(
        return_value=("vector_field", {"dimensions": 384})
    )
    
    # Mock _get_or_create_client
    mock_solr_client = Mock()
    client._get_or_create_client = AsyncMock(return_value=mock_solr_client)
    
    # Mock vector search execution
    mock_vector_response = {
        "response": {
            "docs": [{"id": "doc1", "score": 0.9}, {"id": "doc2", "score": 0.8}],
            "numFound": 2
        }
    }
    client.vector_manager.execute_vector_search = AsyncMock(return_value=mock_vector_response)
    
    # Mock query executor
    expected_result = {
        "result-set": {"docs": [{"id": "doc1"}, {"id": "doc2"}], "numFound": 2}
    }
    client.query_executor.execute_select_query = AsyncMock(return_value=expected_result)
    
    # Execute the query
    query = "SELECT * FROM test_collection"
    vector = [0.1] * 384
    result = await client.execute_vector_select_query(query, vector, "vector_field")
    
    # Verify the result
    assert result == expected_result


@pytest.mark.asyncio
async def test_execute_vector_select_query_no_results(client):
    """Test vector select query with no results."""
    # Mock the AST without limit
    mock_ast = Mock()
    mock_ast.args = {}
    
    # Mock parser and validator
    client.query_builder.parse_and_validate_select = Mock(
        return_value=(mock_ast, "test_collection", None)
    )
    
    # Mock vector manager validation
    client.vector_manager.validate_vector_field = AsyncMock(
        return_value=("vector_field", {"dimensions": 384})
    )
    
    # Mock _get_or_create_client
    mock_solr_client = Mock()
    client._get_or_create_client = AsyncMock(return_value=mock_solr_client)
    
    # Mock vector search with no results
    mock_vector_response = {"response": {"docs": [], "numFound": 0}}
    client.vector_manager.execute_vector_search = AsyncMock(return_value=mock_vector_response)
    
    # Mock query executor
    expected_result = {"result-set": {"docs": [], "numFound": 0}}
    client.query_executor.execute_select_query = AsyncMock(return_value=expected_result)
    
    # Execute the query
    query = "SELECT * FROM test_collection"
    vector = [0.1] * 384
    result = await client.execute_vector_select_query(query, vector)
    
    # Verify the result
    assert result == expected_result
    
    # Verify the query executor was called with WHERE 1=0 (no results)
    call_args = client.query_executor.execute_select_query.call_args
    assert "WHERE 1=0" in call_args.kwargs["query"]


@pytest.mark.asyncio
async def test_execute_vector_select_query_with_where_clause(client):
    """Test vector select query with existing WHERE clause."""
    # Mock the AST
    mock_ast = Mock()
    mock_ast.args = {"limit": Mock(expression=Mock(this="10"))}
    
    # Mock parser and validator
    client.query_builder.parse_and_validate_select = Mock(
        return_value=(mock_ast, "test_collection", None)
    )
    
    # Mock vector manager validation
    client.vector_manager.validate_vector_field = AsyncMock(
        return_value=("vector_field", {"dimensions": 384})
    )
    
    # Mock _get_or_create_client
    mock_solr_client = Mock()
    client._get_or_create_client = AsyncMock(return_value=mock_solr_client)
    
    # Mock vector search
    mock_vector_response = {
        "response": {
            "docs": [{"id": "doc1", "score": 0.9}],
            "numFound": 1
        }
    }
    client.vector_manager.execute_vector_search = AsyncMock(return_value=mock_vector_response)
    
    # Mock query executor
    expected_result = {"result-set": {"docs": [{"id": "doc1"}], "numFound": 1}}
    client.query_executor.execute_select_query = AsyncMock(return_value=expected_result)
    
    # Execute the query with WHERE clause
    query = "SELECT * FROM test_collection WHERE status='active' LIMIT 10"
    vector = [0.1] * 384
    result = await client.execute_vector_select_query(query, vector, "vector_field")
    
    # Verify the result
    assert result == expected_result
    
    # Verify the query executor was called with AND clause
    call_args = client.query_executor.execute_select_query.call_args
    assert "AND id IN" in call_args.kwargs["query"]


@pytest.mark.asyncio
async def test_execute_vector_select_query_error(client):
    """Test error handling in vector select query."""
    # Mock parser to raise an error
    client.query_builder.parse_and_validate_select = Mock(
        side_effect=Exception("Parse error")
    )
    
    # Execute the query and verify error is wrapped
    with pytest.raises(QueryError) as exc_info:
        await client.execute_vector_select_query("SELECT * FROM test_collection", [0.1] * 384)
    
    assert "Error executing vector query" in str(exc_info.value)


@pytest.mark.asyncio
async def test_execute_semantic_select_query_success(client):
    """Test successful semantic select query execution."""
    # Mock the AST
    mock_ast = Mock()
    mock_ast.args = {"limit": Mock(expression=Mock(this="5"))}
    
    # Mock parser and validator
    client.query_builder.parse_and_validate_select = Mock(
        return_value=(mock_ast, "test_collection", None)
    )
    
    # Mock vector manager validation
    client.vector_manager.validate_vector_field = AsyncMock(
        return_value=("vector_field", {"dimensions": 384})
    )
    
    # Mock get_vector
    mock_vector = [0.1] * 384
    client.vector_manager.get_vector = AsyncMock(return_value=mock_vector)
    
    # Mock execute_vector_select_query
    expected_result = {"result-set": {"docs": [{"id": "doc1"}], "numFound": 1}}
    client.execute_vector_select_query = AsyncMock(return_value=expected_result)
    
    # Execute the query
    query = "SELECT * FROM test_collection"
    text = "search query"
    result = await client.execute_semantic_select_query(query, text, "vector_field")
    
    # Verify the result
    assert result == expected_result
    client.execute_vector_select_query.assert_called_once_with(query, mock_vector, "vector_field")


@pytest.mark.asyncio
async def test_execute_semantic_select_query_with_config(client):
    """Test semantic select query with vector provider config."""
    # Mock the AST
    mock_ast = Mock()
    mock_ast.args = {}
    
    # Mock parser and validator
    client.query_builder.parse_and_validate_select = Mock(
        return_value=(mock_ast, "test_collection", None)
    )
    
    # Mock vector manager validation
    client.vector_manager.validate_vector_field = AsyncMock(
        return_value=("vector_field", {"dimensions": 768})
    )
    
    # Mock get_vector
    mock_vector = [0.1] * 768
    client.vector_manager.get_vector = AsyncMock(return_value=mock_vector)
    
    # Mock execute_vector_select_query
    expected_result = {"result-set": {"docs": [], "numFound": 0}}
    client.execute_vector_select_query = AsyncMock(return_value=expected_result)
    
    # Execute the query with config
    query = "SELECT * FROM test_collection"
    text = "search query"
    config = {"model": "custom-model", "base_url": "http://localhost:11434"}
    result = await client.execute_semantic_select_query(query, text, vector_provider_config=config)
    
    # Verify the result
    assert result == expected_result
    
    # Verify vector was retrieved with config
    client.vector_manager.get_vector.assert_called_once_with(text, config)


@pytest.mark.asyncio
async def test_execute_semantic_select_query_error(client):
    """Test error handling in semantic select query."""
    # Mock parser to raise an error
    client.query_builder.parse_and_validate_select = Mock(
        side_effect=Exception("Parse error")
    )
    
    # Execute the query and verify error is wrapped
    with pytest.raises(SolrError) as exc_info:
        await client.execute_semantic_select_query("SELECT * FROM test_collection", "search text")
    
    assert "Semantic search failed" in str(exc_info.value)
