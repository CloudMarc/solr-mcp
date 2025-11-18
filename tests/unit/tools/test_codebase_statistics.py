"""Unit tests for codebase_statistics tools."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from solr_mcp.tools.codebase_statistics import (
    execute_codebase_analytics,
    execute_codebase_statistics,
)


@pytest.fixture
def mock_mcp():
    """Create mock MCP server."""
    mcp = MagicMock()
    mcp.logger = MagicMock()
    mcp.solr_client = MagicMock()
    mcp.solr_client.execute_raw_query = AsyncMock()
    return mcp


@pytest.mark.asyncio
async def test_execute_codebase_statistics_all_stats(mock_mcp):
    """Test getting all codebase statistics."""
    # Arrange - Mock responses for different queries
    responses = [
        # Total files query (*:*)
        {"response": {"numFound": 150}},
        # Python files query (tags_ss:py)
        {"response": {"numFound": 123}},
        # Files with embeddings query
        {"response": {"numFound": 100}},
        # Category facets
        {
            "response": {"numFound": 150},
            "facet_counts": {
                "facet_fields": {
                    "category_ss": ["source", 80, "tests", 40, "documentation", 30]
                }
            },
        },
        # File type facets
        {
            "response": {"numFound": 150},
            "facet_counts": {
                "facet_fields": {"tags_ss": ["py", 123, "md", 15, "json", 12]}
            },
        },
    ]

    mock_mcp.solr_client.execute_raw_query.side_effect = responses

    # Act
    result = await execute_codebase_statistics(
        mcp=mock_mcp,
        collection="codebase",
        include_categories=True,
        include_file_types=True,
    )

    # Assert
    assert result["success"] is True
    assert result["collection"] == "codebase"

    # Check totals
    assert result["totals"]["total_files"] == 150
    assert result["totals"]["python_files"] == 123
    assert result["totals"]["files_with_embeddings"] == 100

    # Check categories
    assert result["categories"]["source"] == 80
    assert result["categories"]["tests"] == 40
    assert result["categories"]["documentation"] == 30

    # Check file types
    assert result["file_types"]["py"] == 123
    assert result["file_types"]["md"] == 15
    assert result["file_types"]["json"] == 12

    # Check performance note
    assert "100ms" in result["performance_note"]


@pytest.mark.asyncio
async def test_execute_codebase_statistics_no_categories(mock_mcp):
    """Test statistics without categories."""
    # Arrange
    responses = [
        {"response": {"numFound": 150}},
        {"response": {"numFound": 123}},
        {"response": {"numFound": 100}},
        {
            "response": {"numFound": 150},
            "facet_counts": {"facet_fields": {"tags_ss": ["py", 123]}},
        },
    ]

    mock_mcp.solr_client.execute_raw_query.side_effect = responses

    # Act
    result = await execute_codebase_statistics(
        mcp=mock_mcp,
        include_categories=False,
        include_file_types=True,
    )

    # Assert
    assert result["success"] is True
    assert "categories" not in result
    assert "file_types" in result
    assert result["file_types"]["py"] == 123


@pytest.mark.asyncio
async def test_execute_codebase_statistics_no_file_types(mock_mcp):
    """Test statistics without file types."""
    # Arrange
    responses = [
        {"response": {"numFound": 150}},
        {"response": {"numFound": 123}},
        {"response": {"numFound": 100}},
        {
            "response": {"numFound": 150},
            "facet_counts": {
                "facet_fields": {"category_ss": ["source", 80, "tests", 40]}
            },
        },
    ]

    mock_mcp.solr_client.execute_raw_query.side_effect = responses

    # Act
    result = await execute_codebase_statistics(
        mcp=mock_mcp,
        include_categories=True,
        include_file_types=False,
    )

    # Assert
    assert result["success"] is True
    assert "categories" in result
    assert "file_types" not in result
    assert result["categories"]["source"] == 80


@pytest.mark.asyncio
async def test_execute_codebase_statistics_minimal(mock_mcp):
    """Test statistics with minimal options (only totals)."""
    # Arrange
    responses = [
        {"response": {"numFound": 50}},
        {"response": {"numFound": 40}},
        {"response": {"numFound": 30}},
    ]

    mock_mcp.solr_client.execute_raw_query.side_effect = responses

    # Act
    result = await execute_codebase_statistics(
        mcp=mock_mcp,
        include_categories=False,
        include_file_types=False,
    )

    # Assert
    assert result["success"] is True
    assert "totals" in result
    assert "categories" not in result
    assert "file_types" not in result


@pytest.mark.asyncio
async def test_execute_codebase_statistics_error(mock_mcp):
    """Test error handling in statistics."""
    # Arrange
    mock_mcp.solr_client.execute_raw_query.side_effect = Exception("Solr error")

    # Act
    result = await execute_codebase_statistics(mcp=mock_mcp)

    # Assert
    assert result["success"] is False
    assert "Solr error" in result["error"]
    assert result["collection"] == "codebase"


@pytest.mark.asyncio
async def test_execute_codebase_analytics_tech_debt(mock_mcp):
    """Test technical debt analysis."""
    # Arrange - Mock responses for each debt marker
    responses = [
        {"response": {"numFound": 15}},  # TODO
        {"response": {"numFound": 8}},  # FIXME
        {"response": {"numFound": 3}},  # HACK
        {"response": {"numFound": 2}},  # XXX
        {"response": {"numFound": 0}},  # BUG (no results)
    ]

    mock_mcp.solr_client.execute_raw_query.side_effect = responses

    # Act
    result = await execute_codebase_analytics(
        mcp=mock_mcp,
        analysis_type="tech_debt",
        collection="codebase",
    )

    # Assert
    assert result["success"] is True
    assert result["analysis_type"] == "tech_debt"
    assert result["collection"] == "codebase"
    assert result["total_debt_markers"] == 28  # 15+8+3+2
    assert result["by_type"]["TODO"] == 15
    assert result["by_type"]["FIXME"] == 8
    assert result["by_type"]["HACK"] == 3
    assert result["by_type"]["XXX"] == 2
    assert "BUG" not in result["by_type"]  # Zero count not included


@pytest.mark.asyncio
async def test_execute_codebase_analytics_missing_docs(mock_mcp):
    """Test missing documentation analysis."""
    # Arrange
    responses = [
        {"response": {"numFound": 80}},  # Files with code (def/class)
        {"response": {"numFound": 60}},  # Files with docs (Args/Returns)
    ]

    mock_mcp.solr_client.execute_raw_query.side_effect = responses

    # Act
    result = await execute_codebase_analytics(
        mcp=mock_mcp,
        analysis_type="missing_docs",
        collection="codebase",
    )

    # Assert
    assert result["success"] is True
    assert result["analysis_type"] == "missing_docs"
    assert result["files_with_code"] == 80
    assert result["files_with_docs"] == 60
    assert result["documentation_coverage_percent"] == 75.0  # 60/80 * 100


@pytest.mark.asyncio
async def test_execute_codebase_analytics_missing_docs_zero_code(mock_mcp):
    """Test documentation analysis with no code files."""
    # Arrange
    responses = [
        {"response": {"numFound": 0}},  # No files with code
        {"response": {"numFound": 0}},  # No files with docs
    ]

    mock_mcp.solr_client.execute_raw_query.side_effect = responses

    # Act
    result = await execute_codebase_analytics(
        mcp=mock_mcp,
        analysis_type="missing_docs",
    )

    # Assert
    assert result["success"] is True
    assert result["documentation_coverage_percent"] == 0


@pytest.mark.asyncio
async def test_execute_codebase_analytics_error_handling(mock_mcp):
    """Test error handling analysis."""
    # Arrange
    responses = [
        {"response": {"numFound": 45}},  # Files with exception handling
        {"response": {"numFound": 10}},  # ValueError
        {"response": {"numFound": 8}},  # TypeError
        {"response": {"numFound": 0}},  # ConnectionError (not included)
        {"response": {"numFound": 5}},  # SolrError
    ]

    mock_mcp.solr_client.execute_raw_query.side_effect = responses

    # Act
    result = await execute_codebase_analytics(
        mcp=mock_mcp,
        analysis_type="error_handling",
        collection="codebase",
    )

    # Assert
    assert result["success"] is True
    assert result["analysis_type"] == "error_handling"
    assert result["files_with_error_handling"] == 45
    assert result["exception_types_used"]["ValueError"] == 10
    assert result["exception_types_used"]["TypeError"] == 8
    assert result["exception_types_used"]["SolrError"] == 5
    assert "ConnectionError" not in result["exception_types_used"]


@pytest.mark.asyncio
async def test_execute_codebase_analytics_unknown_type(mock_mcp):
    """Test unknown analysis type error."""
    # Act
    result = await execute_codebase_analytics(
        mcp=mock_mcp,
        analysis_type="unknown_analysis",
    )

    # Assert
    assert result["success"] is False
    assert "Unknown analysis type" in result["error"]
    assert "tech_debt" in result["supported_types"]
    assert "missing_docs" in result["supported_types"]
    assert "error_handling" in result["supported_types"]


@pytest.mark.asyncio
async def test_execute_codebase_analytics_error(mock_mcp):
    """Test error handling in analytics."""
    # Arrange
    mock_mcp.solr_client.execute_raw_query.side_effect = Exception("Solr error")

    # Act
    result = await execute_codebase_analytics(
        mcp=mock_mcp,
        analysis_type="tech_debt",
    )

    # Assert
    assert result["success"] is False
    assert "Solr error" in result["error"]
    assert result["analysis_type"] == "tech_debt"


@pytest.mark.asyncio
async def test_execute_codebase_analytics_with_threshold(mock_mcp):
    """Test analytics with threshold parameter (accepted but not used)."""
    # Arrange
    responses = [
        {"response": {"numFound": 5}},  # TODO
        {"response": {"numFound": 0}},  # FIXME
        {"response": {"numFound": 0}},  # HACK
        {"response": {"numFound": 0}},  # XXX
        {"response": {"numFound": 0}},  # BUG
    ]

    mock_mcp.solr_client.execute_raw_query.side_effect = responses

    # Act
    result = await execute_codebase_analytics(
        mcp=mock_mcp,
        analysis_type="tech_debt",
        threshold=10,  # Accepted parameter
    )

    # Assert
    assert result["success"] is True
    assert result["total_debt_markers"] == 5


@pytest.mark.asyncio
async def test_totals_queries_structure(mock_mcp):
    """Test that totals queries are structured correctly."""
    # Arrange
    responses = [
        {"response": {"numFound": 100}},
        {"response": {"numFound": 80}},
        {"response": {"numFound": 50}},
    ]

    mock_mcp.solr_client.execute_raw_query.side_effect = responses

    # Act
    await execute_codebase_statistics(
        mcp=mock_mcp,
        collection="codebase",
        include_categories=False,
        include_file_types=False,
    )

    # Assert - Verify 3 calls were made
    assert mock_mcp.solr_client.execute_raw_query.call_count == 3

    # Check first call (all docs)
    call1 = mock_mcp.solr_client.execute_raw_query.call_args_list[0]
    assert call1[1]["params"]["q"] == "*:*"
    assert call1[1]["params"]["rows"] == "0"

    # Check second call (Python files)
    call2 = mock_mcp.solr_client.execute_raw_query.call_args_list[1]
    assert call2[1]["params"]["q"] == "tags_ss:py"

    # Check third call (files with embeddings)
    call3 = mock_mcp.solr_client.execute_raw_query.call_args_list[2]
    assert call3[1]["params"]["q"] == "embedding:[* TO *]"


@pytest.mark.asyncio
async def test_category_facets_structure(mock_mcp):
    """Test that category facets query is structured correctly."""
    # Arrange
    responses = [
        {"response": {"numFound": 100}},
        {"response": {"numFound": 80}},
        {"response": {"numFound": 50}},
        {
            "response": {"numFound": 100},
            "facet_counts": {
                "facet_fields": {"category_ss": ["source", 60, "tests", 40]}
            },
        },
    ]

    mock_mcp.solr_client.execute_raw_query.side_effect = responses

    # Act
    await execute_codebase_statistics(
        mcp=mock_mcp,
        include_categories=True,
        include_file_types=False,
    )

    # Assert
    call = mock_mcp.solr_client.execute_raw_query.call_args_list[3]
    params = call[1]["params"]
    assert params["facet"] == "true"
    assert params["facet.field"] == "category_ss"
    assert params["facet.limit"] == "20"
    assert params["facet.sort"] == "count"


@pytest.mark.asyncio
async def test_file_type_facets_structure(mock_mcp):
    """Test that file type facets query is structured correctly."""
    # Arrange
    responses = [
        {"response": {"numFound": 100}},
        {"response": {"numFound": 80}},
        {"response": {"numFound": 50}},
        {
            "response": {"numFound": 100},
            "facet_counts": {"facet_fields": {"tags_ss": ["py", 80, "md", 20]}},
        },
    ]

    mock_mcp.solr_client.execute_raw_query.side_effect = responses

    # Act
    await execute_codebase_statistics(
        mcp=mock_mcp,
        include_categories=False,
        include_file_types=True,
    )

    # Assert
    call = mock_mcp.solr_client.execute_raw_query.call_args_list[3]
    params = call[1]["params"]
    assert params["facet"] == "true"
    assert params["facet.field"] == "tags_ss"
    assert params["facet.limit"] == "20"
    assert params["facet.sort"] == "count"


@pytest.mark.asyncio
async def test_tech_debt_queries_structure(mock_mcp):
    """Test that tech debt queries are structured correctly."""
    # Arrange
    responses = [{"response": {"numFound": i}} for i in range(5)]
    mock_mcp.solr_client.execute_raw_query.side_effect = responses

    # Act
    await execute_codebase_analytics(
        mcp=mock_mcp,
        analysis_type="tech_debt",
        collection="codebase",
    )

    # Assert - Should have 5 queries (one per marker)
    assert mock_mcp.solr_client.execute_raw_query.call_count == 5

    # Check that queries search for markers in Python files
    for call in mock_mcp.solr_client.execute_raw_query.call_args_list:
        query = call[1]["params"]["q"]
        assert "tags_ss:py" in query
        assert "content:" in query


@pytest.mark.asyncio
async def test_documentation_queries_structure(mock_mcp):
    """Test that documentation analysis queries are structured correctly."""
    # Arrange
    responses = [
        {"response": {"numFound": 80}},
        {"response": {"numFound": 60}},
    ]
    mock_mcp.solr_client.execute_raw_query.side_effect = responses

    # Act
    await execute_codebase_analytics(
        mcp=mock_mcp,
        analysis_type="missing_docs",
    )

    # Assert - Should have 2 queries
    assert mock_mcp.solr_client.execute_raw_query.call_count == 2

    # Check first query (files with code)
    call1 = mock_mcp.solr_client.execute_raw_query.call_args_list[0]
    query1 = call1[1]["params"]["q"]
    assert "tags_ss:py" in query1
    assert "category_ss:source" in query1
    assert "content:def" in query1 or "content:class" in query1

    # Check second query (files with docs)
    call2 = mock_mcp.solr_client.execute_raw_query.call_args_list[1]
    query2 = call2[1]["params"]["q"]
    assert "tags_ss:py" in query2
    assert "category_ss:source" in query2
    assert "content:Args" in query2 or "content:Returns" in query2


@pytest.mark.asyncio
async def test_error_handling_queries_structure(mock_mcp):
    """Test that error handling analysis queries are structured correctly."""
    # Arrange
    responses = [{"response": {"numFound": i * 10}} for i in range(5)]
    mock_mcp.solr_client.execute_raw_query.side_effect = responses

    # Act
    await execute_codebase_analytics(
        mcp=mock_mcp,
        analysis_type="error_handling",
    )

    # Assert - Should have 5 queries (1 for general + 4 for specific types)
    assert mock_mcp.solr_client.execute_raw_query.call_count == 5

    # Check first query (general exception handling)
    call1 = mock_mcp.solr_client.execute_raw_query.call_args_list[0]
    query1 = call1[1]["params"]["q"]
    assert "tags_ss:py" in query1
    assert (
        "content:except" in query1
        or "content:raise" in query1
        or "content:try" in query1
    )
