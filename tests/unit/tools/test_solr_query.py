"""Tests for the solr_query tool with highlighting and stats support."""

import pytest

from solr_mcp.solr.exceptions import QueryError
from solr_mcp.tools.solr_query import execute_query


@pytest.mark.asyncio
async def test_execute_query_basic(mock_server):
    """Test basic query without highlighting or stats."""
    expected_result = {
        "num_found": 10,
        "docs": [{"id": "1", "title": "Test"}, {"id": "2", "title": "Test 2"}],
        "start": 0,
        "query_info": {"q": "test", "rows": 10, "collection": "test_collection"},
    }

    mock_server.solr_client.execute_query.return_value = expected_result

    result = await execute_query(
        mock_server, collection="test_collection", q="test", rows=10
    )

    assert result["num_found"] == 10
    assert len(result["docs"]) == 2
    assert result["query_info"]["q"] == "test"
    mock_server.solr_client.execute_query.assert_called_once()


@pytest.mark.asyncio
async def test_execute_query_with_highlighting(mock_server):
    """Test query with highlighting enabled."""
    expected_result = {
        "num_found": 5,
        "docs": [{"id": "1", "title": "Machine Learning"}],
        "start": 0,
        "query_info": {
            "q": "machine learning",
            "rows": 10,
            "collection": "test_collection",
        },
        "highlighting": {
            "1": {
                "title": ["<em>Machine Learning</em> Fundamentals"],
                "content": ["Introduction to <em>machine learning</em> algorithms"],
            }
        },
    }

    mock_server.solr_client.execute_query.return_value = expected_result

    result = await execute_query(
        mock_server,
        collection="test_collection",
        q="machine learning",
        highlight_fields=["title", "content"],
        highlight_snippets=3,
        highlight_fragsize=100,
    )

    assert "highlighting" in result
    assert "1" in result["highlighting"]
    assert "title" in result["highlighting"]["1"]
    assert "<em>Machine Learning</em>" in result["highlighting"]["1"]["title"][0]


@pytest.mark.asyncio
async def test_execute_query_with_stats(mock_server):
    """Test query with stats component."""
    expected_result = {
        "num_found": 100,
        "docs": [{"id": "1", "price": 10.99}, {"id": "2", "price": 25.50}],
        "start": 0,
        "query_info": {"q": "*:*", "rows": 10, "collection": "products"},
        "stats": {
            "price": {
                "min": 5.99,
                "max": 99.99,
                "count": 100,
                "missing": 0,
                "sum": 3450.5,
                "mean": 34.505,
                "stddev": 15.32,
            }
        },
    }

    mock_server.solr_client.execute_query.return_value = expected_result

    result = await execute_query(
        mock_server,
        collection="products",
        q="*:*",
        stats_fields=["price"],
    )

    assert "stats" in result
    assert "price" in result["stats"]
    assert result["stats"]["price"]["min"] == 5.99
    assert result["stats"]["price"]["max"] == 99.99
    assert result["stats"]["price"]["mean"] == 34.505


@pytest.mark.asyncio
async def test_execute_query_with_filters(mock_server):
    """Test query with filter queries."""
    expected_result = {
        "num_found": 20,
        "docs": [{"id": "1", "category": "electronics", "price": 299.99}],
        "start": 0,
        "query_info": {"q": "*:*", "rows": 10, "collection": "products"},
    }

    mock_server.solr_client.execute_query.return_value = expected_result

    result = await execute_query(
        mock_server,
        collection="products",
        q="*:*",
        fq=["category:electronics", "price:[100 TO 500]"],
        rows=10,
    )

    assert result["num_found"] == 20
    assert result["docs"][0]["category"] == "electronics"


@pytest.mark.asyncio
async def test_execute_query_with_pagination(mock_server):
    """Test query with pagination parameters."""
    expected_result = {
        "num_found": 100,
        "docs": [{"id": "11"}, {"id": "12"}],
        "start": 10,
        "query_info": {"q": "*:*", "rows": 2, "collection": "test_collection"},
    }

    mock_server.solr_client.execute_query.return_value = expected_result

    result = await execute_query(
        mock_server, collection="test_collection", q="*:*", rows=2, start=10
    )

    assert result["start"] == 10
    assert result["query_info"]["rows"] == 2


@pytest.mark.asyncio
async def test_execute_query_with_sort(mock_server):
    """Test query with sorting."""
    expected_result = {
        "num_found": 50,
        "docs": [{"id": "1", "price": 5.99}, {"id": "2", "price": 10.99}],
        "start": 0,
        "query_info": {"q": "*:*", "rows": 10, "collection": "products"},
    }

    mock_server.solr_client.execute_query.return_value = expected_result

    result = await execute_query(
        mock_server, collection="products", q="*:*", sort="price asc"
    )

    assert result["docs"][0]["price"] < result["docs"][1]["price"]


@pytest.mark.asyncio
async def test_execute_query_with_field_list(mock_server):
    """Test query with field list."""
    expected_result = {
        "num_found": 10,
        "docs": [{"id": "1", "title": "Test"}, {"id": "2", "title": "Test 2"}],
        "start": 0,
        "query_info": {"q": "*:*", "rows": 10, "collection": "test_collection"},
    }

    mock_server.solr_client.execute_query.return_value = expected_result

    result = await execute_query(
        mock_server, collection="test_collection", q="*:*", fl="id,title"
    )

    # Verify only requested fields are present
    assert "id" in result["docs"][0]
    assert "title" in result["docs"][0]


@pytest.mark.asyncio
async def test_execute_query_highlighting_and_stats_combined(mock_server):
    """Test query with both highlighting and stats enabled."""
    expected_result = {
        "num_found": 25,
        "docs": [{"id": "1", "title": "Data Science", "price": 49.99}],
        "start": 0,
        "query_info": {"q": "data", "rows": 10, "collection": "books"},
        "highlighting": {
            "1": {
                "title": ["<em>Data</em> Science Handbook"],
                "description": ["Introduction to <em>data</em> analysis"],
            }
        },
        "stats": {
            "price": {
                "min": 19.99,
                "max": 79.99,
                "mean": 45.50,
            }
        },
    }

    mock_server.solr_client.execute_query.return_value = expected_result

    result = await execute_query(
        mock_server,
        collection="books",
        q="data",
        highlight_fields=["title", "description"],
        stats_fields=["price"],
    )

    assert "highlighting" in result
    assert "stats" in result
    assert result["num_found"] == 25


@pytest.mark.asyncio
async def test_execute_query_error_handling(mock_server):
    """Test error handling in query execution."""
    error_message = "Query syntax error"
    mock_server.solr_client.execute_query.side_effect = QueryError(error_message)

    with pytest.raises(QueryError, match=error_message):
        await execute_query(mock_server, collection="test_collection", q="invalid:")


@pytest.mark.asyncio
async def test_execute_query_highlighting_methods(mock_server):
    """Test different highlighting methods."""
    for method in ["unified", "original", "fastVector"]:
        expected_result = {
            "num_found": 5,
            "docs": [{"id": "1"}],
            "start": 0,
            "query_info": {"q": "test", "rows": 10, "collection": "test_collection"},
            "highlighting": {"1": {"content": ["<em>test</em> content"]}},
        }

        mock_server.solr_client.execute_query.return_value = expected_result

        result = await execute_query(
            mock_server,
            collection="test_collection",
            q="test",
            highlight_fields=["content"],
            highlight_method=method,
        )

        assert "highlighting" in result
