"""Tests for the solr_terms tool."""

import pytest

from solr_mcp.solr.exceptions import SolrError
from solr_mcp.tools.solr_terms import execute_terms


@pytest.mark.asyncio
async def test_execute_terms_basic(mock_server):
    """Test basic terms retrieval."""
    expected_result = {
        "terms": [
            {"term": "machine", "frequency": 45},
            {"term": "learning", "frequency": 42},
            {"term": "data", "frequency": 38},
        ],
        "field": "title",
        "collection": "test_collection",
        "total_terms": 3,
    }

    mock_server.solr_client.get_terms.return_value = expected_result

    result = await execute_terms(
        mock_server, collection="test_collection", field="title", limit=10
    )

    assert result["total_terms"] == 3
    assert result["field"] == "title"
    assert len(result["terms"]) == 3
    assert result["terms"][0]["term"] == "machine"
    assert result["terms"][0]["frequency"] == 45


@pytest.mark.asyncio
async def test_execute_terms_with_prefix(mock_server):
    """Test terms retrieval with prefix filter."""
    expected_result = {
        "terms": [
            {"term": "artificial", "frequency": 12},
            {"term": "artifact", "frequency": 5},
            {"term": "artifice", "frequency": 2},
        ],
        "field": "content",
        "collection": "test_collection",
        "total_terms": 3,
    }

    mock_server.solr_client.get_terms.return_value = expected_result

    result = await execute_terms(
        mock_server, collection="test_collection", field="content", prefix="artif"
    )

    assert all(term["term"].startswith("artif") for term in result["terms"])
    assert result["total_terms"] == 3


@pytest.mark.asyncio
async def test_execute_terms_with_regex(mock_server):
    """Test terms retrieval with regex filter."""
    expected_result = {
        "terms": [
            {"term": "test123", "frequency": 8},
            {"term": "test456", "frequency": 6},
        ],
        "field": "tags",
        "collection": "test_collection",
        "total_terms": 2,
    }

    mock_server.solr_client.get_terms.return_value = expected_result

    result = await execute_terms(
        mock_server, collection="test_collection", field="tags", regex="test[0-9]+"
    )

    assert result["total_terms"] == 2
    assert all("test" in term["term"] for term in result["terms"])


@pytest.mark.asyncio
async def test_execute_terms_with_min_count(mock_server):
    """Test terms retrieval with minimum count filter."""
    expected_result = {
        "terms": [
            {"term": "popular", "frequency": 100},
            {"term": "common", "frequency": 85},
        ],
        "field": "keywords",
        "collection": "test_collection",
        "total_terms": 2,
    }

    mock_server.solr_client.get_terms.return_value = expected_result

    result = await execute_terms(
        mock_server, collection="test_collection", field="keywords", min_count=50
    )

    assert all(term["frequency"] >= 50 for term in result["terms"])


@pytest.mark.asyncio
async def test_execute_terms_with_max_count(mock_server):
    """Test terms retrieval with maximum count filter."""
    expected_result = {
        "terms": [
            {"term": "rare", "frequency": 3},
            {"term": "uncommon", "frequency": 2},
        ],
        "field": "specialty",
        "collection": "test_collection",
        "total_terms": 2,
    }

    mock_server.solr_client.get_terms.return_value = expected_result

    result = await execute_terms(
        mock_server, collection="test_collection", field="specialty", max_count=5
    )

    assert all(term["frequency"] <= 5 for term in result["terms"])


@pytest.mark.asyncio
async def test_execute_terms_with_limit(mock_server):
    """Test terms retrieval with limit."""
    expected_result = {
        "terms": [
            {"term": "term1", "frequency": 50},
            {"term": "term2", "frequency": 45},
            {"term": "term3", "frequency": 40},
        ],
        "field": "title",
        "collection": "test_collection",
        "total_terms": 3,
    }

    mock_server.solr_client.get_terms.return_value = expected_result

    result = await execute_terms(
        mock_server, collection="test_collection", field="title", limit=3
    )

    assert len(result["terms"]) == 3
    assert result["total_terms"] == 3


@pytest.mark.asyncio
async def test_execute_terms_empty_result(mock_server):
    """Test terms retrieval with no matching terms."""
    expected_result = {
        "terms": [],
        "field": "title",
        "collection": "test_collection",
        "total_terms": 0,
    }

    mock_server.solr_client.get_terms.return_value = expected_result

    result = await execute_terms(
        mock_server, collection="test_collection", field="title", prefix="xyz"
    )

    assert result["total_terms"] == 0
    assert len(result["terms"]) == 0


@pytest.mark.asyncio
async def test_execute_terms_error_handling(mock_server):
    """Test error handling in terms retrieval."""
    error_message = "Field does not exist"
    mock_server.solr_client.get_terms.side_effect = SolrError(error_message)

    with pytest.raises(SolrError, match=error_message):
        await execute_terms(
            mock_server, collection="test_collection", field="nonexistent"
        )


@pytest.mark.asyncio
async def test_execute_terms_combined_filters(mock_server):
    """Test terms retrieval with multiple filters combined."""
    expected_result = {
        "terms": [
            {"term": "machine_learning", "frequency": 45},
            {"term": "machine_vision", "frequency": 38},
        ],
        "field": "tags",
        "collection": "test_collection",
        "total_terms": 2,
    }

    mock_server.solr_client.get_terms.return_value = expected_result

    result = await execute_terms(
        mock_server,
        collection="test_collection",
        field="tags",
        prefix="machine",
        min_count=30,
        limit=10,
    )

    assert result["total_terms"] == 2
    assert all(term["term"].startswith("machine") for term in result["terms"])
    assert all(term["frequency"] >= 30 for term in result["terms"])
