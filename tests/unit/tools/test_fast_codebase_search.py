"""Unit tests for fast_codebase_search tool."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from solr_mcp.tools.fast_codebase_search import (
    execute_fast_codebase_search,
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
async def test_execute_fast_codebase_search_basic(mock_mcp):
    """Test basic codebase search using Solr."""
    # Arrange
    mock_response = {
        "response": {
            "numFound": 5,
            "docs": [
                {
                    "id": "doc1",
                    "source": "file1.py",
                    "category_ss": ["source"],
                    "tags_ss": ["py"],
                },
                {
                    "id": "doc2",
                    "source": "file2.py",
                    "category_ss": ["tests"],
                    "tags_ss": ["py"],
                },
            ],
        },
        "highlighting": {
            "doc1": {"content": ["def **SolrClient**():"]},
            "doc2": {"content": ["class **SolrClient**:"]},
        },
    }
    mock_mcp.solr_client.execute_raw_query.return_value = mock_response

    # Act
    result = await execute_fast_codebase_search(
        mcp=mock_mcp,
        pattern="SolrClient",
        collection="codebase",
    )

    # Assert
    assert result["success"] is True
    assert result["pattern"] == "SolrClient"
    assert result["total_matches"] == 5
    assert result["returned_results"] == 2
    assert result["search_method"] == "solr"
    assert "10-100x faster" in result["performance_note"]
    assert len(result["matches"]) == 2
    assert result["matches"][0]["file"] == "file1.py"
    assert result["matches"][0]["snippets"] == ["def **SolrClient**():"]
    assert result["matches"][1]["file"] == "file2.py"


@pytest.mark.asyncio
async def test_execute_fast_codebase_search_with_file_type(mock_mcp):
    """Test codebase search with file type filter."""
    # Arrange
    mock_response = {
        "response": {
            "numFound": 2,
            "docs": [
                {
                    "id": "doc1",
                    "source": "test.py",
                    "category_ss": ["tests"],
                    "tags_ss": ["py"],
                }
            ],
        },
        "highlighting": {"doc1": {"content": ["async def **test**():"]}},
    }
    mock_mcp.solr_client.execute_raw_query.return_value = mock_response

    # Act
    result = await execute_fast_codebase_search(
        mcp=mock_mcp,
        pattern="test",
        file_type="py",
        collection="codebase",
    )

    # Assert
    assert result["success"] is True
    assert result["file_type"] == "py"
    assert result["total_matches"] == 2

    # Verify query included file type filter
    call_args = mock_mcp.solr_client.execute_raw_query.call_args
    assert call_args[1]["params"]["q"] == "content:test AND tags_ss:py"


@pytest.mark.asyncio
async def test_execute_fast_codebase_search_without_highlighting(mock_mcp):
    """Test codebase search without highlighting."""
    # Arrange
    mock_response = {
        "response": {
            "numFound": 1,
            "docs": [
                {
                    "id": "doc1",
                    "source": "file.py",
                    "category_ss": ["source"],
                    "tags_ss": ["py"],
                }
            ],
        },
    }
    mock_mcp.solr_client.execute_raw_query.return_value = mock_response

    # Act
    result = await execute_fast_codebase_search(
        mcp=mock_mcp,
        pattern="function",
        use_highlighting=False,
    )

    # Assert
    assert result["success"] is True
    assert "snippets" not in result["matches"][0]
    assert result["matches"][0]["match_count"] == 1

    # Verify highlighting not requested
    call_args = mock_mcp.solr_client.execute_raw_query.call_args
    assert "hl" not in call_args[1]["params"]


@pytest.mark.asyncio
async def test_execute_fast_codebase_search_max_results(mock_mcp):
    """Test codebase search with max_results limit."""
    # Arrange
    mock_response = {
        "response": {
            "numFound": 100,
            "docs": [
                {
                    "id": f"doc{i}",
                    "source": f"file{i}.py",
                    "category_ss": [],
                    "tags_ss": [],
                }
                for i in range(50)
            ],
        },
        "highlighting": {},
    }
    mock_mcp.solr_client.execute_raw_query.return_value = mock_response

    # Act
    result = await execute_fast_codebase_search(
        mcp=mock_mcp,
        pattern="test",
        max_results=50,
    )

    # Assert
    assert result["success"] is True
    assert result["total_matches"] == 100
    assert result["returned_results"] == 50

    # Verify max_results passed to Solr
    call_args = mock_mcp.solr_client.execute_raw_query.call_args
    assert call_args[1]["params"]["rows"] == "50"


@pytest.mark.asyncio
async def test_execute_fast_codebase_search_file_type_with_dot(mock_mcp):
    """Test that file type with leading dot is handled correctly."""
    # Arrange
    mock_response = {
        "response": {"numFound": 0, "docs": []},
        "highlighting": {},
    }
    mock_mcp.solr_client.execute_raw_query.return_value = mock_response

    # Act
    result = await execute_fast_codebase_search(
        mcp=mock_mcp,
        pattern="test",
        file_type=".py",  # Leading dot should be stripped
    )

    # Assert - the dot is stripped internally
    assert result["file_type"] == "py"

    # Verify query uses stripped version
    call_args = mock_mcp.solr_client.execute_raw_query.call_args
    assert "tags_ss:py" in call_args[1]["params"]["q"]


@pytest.mark.asyncio
async def test_execute_fast_codebase_search_fallback_to_grep(mock_mcp):
    """Test fallback to grep when Solr fails."""
    # Arrange
    mock_mcp.solr_client.execute_raw_query.side_effect = Exception("Solr unavailable")

    # Act
    with patch("solr_mcp.tools.fast_codebase_search.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            stdout="file1.py:def test_function():\nfile2.py:class TestClass:",
            returncode=0,
        )

        result = await execute_fast_codebase_search(
            mcp=mock_mcp,
            pattern="test",
        )

    # Assert
    assert result["success"] is True
    assert result["search_method"] == "grep"
    assert "Solr unavailable" in result["performance_note"]
    assert len(result["matches"]) == 2
    assert result["matches"][0]["file"] == "file1.py"
    assert result["matches"][0]["snippet"] == "def test_function():"
    assert result["matches"][1]["file"] == "file2.py"
    assert result["matches"][1]["snippet"] == "class TestClass:"

    # Verify warning logged
    mock_mcp.logger.warning.assert_called_once()


@pytest.mark.asyncio
async def test_execute_fast_codebase_search_grep_with_file_type(mock_mcp):
    """Test grep fallback with file type filter."""
    # Arrange
    mock_mcp.solr_client.execute_raw_query.side_effect = Exception("Solr error")

    # Act
    with patch("solr_mcp.tools.fast_codebase_search.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            stdout="test.py:result",
            returncode=0,
        )

        result = await execute_fast_codebase_search(
            mcp=mock_mcp,
            pattern="test",
            file_type="py",
        )

    # Assert
    assert result["success"] is True
    assert result["file_type"] == "py"

    # Verify grep called with --include filter
    mock_run.assert_called_once()
    call_args = mock_run.call_args[0][0]
    assert "--include" in call_args
    assert "*.py" in call_args


@pytest.mark.asyncio
async def test_execute_fast_codebase_search_grep_timeout(mock_mcp):
    """Test grep fallback timeout handling."""
    # Arrange
    mock_mcp.solr_client.execute_raw_query.side_effect = Exception("Solr error")

    # Act
    with patch("solr_mcp.tools.fast_codebase_search.subprocess.run") as mock_run:
        import subprocess

        mock_run.side_effect = subprocess.TimeoutExpired(cmd="grep", timeout=30)

        result = await execute_fast_codebase_search(
            mcp=mock_mcp,
            pattern="test",
        )

    # Assert
    assert result["success"] is False
    assert "timed out" in result["error"]
    assert result["pattern"] == "test"


@pytest.mark.asyncio
async def test_execute_fast_codebase_search_grep_error(mock_mcp):
    """Test grep fallback error handling."""
    # Arrange
    mock_mcp.solr_client.execute_raw_query.side_effect = Exception("Solr error")

    # Act
    with patch("solr_mcp.tools.fast_codebase_search.subprocess.run") as mock_run:
        mock_run.side_effect = Exception("grep failed")

        result = await execute_fast_codebase_search(
            mcp=mock_mcp,
            pattern="test",
        )

    # Assert
    assert result["success"] is False
    assert "grep failed" in result["error"]


@pytest.mark.asyncio
async def test_execute_fast_codebase_search_grep_max_results(mock_mcp):
    """Test that grep fallback respects max_results."""
    # Arrange
    mock_mcp.solr_client.execute_raw_query.side_effect = Exception("Solr error")

    # Act
    with patch("solr_mcp.tools.fast_codebase_search.subprocess.run") as mock_run:
        # Simulate 10 results
        lines = [f"file{i}.py:match{i}" for i in range(10)]
        mock_run.return_value = MagicMock(
            stdout="\n".join(lines),
            returncode=0,
        )

        result = await execute_fast_codebase_search(
            mcp=mock_mcp,
            pattern="test",
            max_results=5,
        )

    # Assert
    assert result["success"] is True
    assert result["total_matches"] == 10
    assert result["returned_results"] == 5  # Limited to max_results


@pytest.mark.asyncio
async def test_execute_fast_codebase_search_grep_no_colon(mock_mcp):
    """Test grep fallback handles lines without colons."""
    # Arrange
    mock_mcp.solr_client.execute_raw_query.side_effect = Exception("Solr error")

    # Act
    with patch("solr_mcp.tools.fast_codebase_search.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            stdout="file1.py:match1\ninvalidline\nfile2.py:match2",
            returncode=0,
        )

        result = await execute_fast_codebase_search(
            mcp=mock_mcp,
            pattern="test",
        )

    # Assert
    assert result["success"] is True
    assert len(result["matches"]) == 2  # Invalid line skipped
    assert result["matches"][0]["file"] == "file1.py"
    assert result["matches"][1]["file"] == "file2.py"


@pytest.mark.asyncio
async def test_execute_fast_codebase_search_empty_results(mock_mcp):
    """Test codebase search with no matches."""
    # Arrange
    mock_response = {
        "response": {
            "numFound": 0,
            "docs": [],
        },
        "highlighting": {},
    }
    mock_mcp.solr_client.execute_raw_query.return_value = mock_response

    # Act
    result = await execute_fast_codebase_search(
        mcp=mock_mcp,
        pattern="nonexistent",
    )

    # Assert
    assert result["success"] is True
    assert result["total_matches"] == 0
    assert result["returned_results"] == 0
    assert result["matches"] == []


@pytest.mark.asyncio
async def test_execute_fast_codebase_search_highlighting_params(mock_mcp):
    """Test that highlighting parameters are set correctly."""
    # Arrange
    mock_response = {
        "response": {"numFound": 0, "docs": []},
        "highlighting": {},
    }
    mock_mcp.solr_client.execute_raw_query.return_value = mock_response

    # Act
    await execute_fast_codebase_search(
        mcp=mock_mcp,
        pattern="test",
        use_highlighting=True,
    )

    # Assert
    call_args = mock_mcp.solr_client.execute_raw_query.call_args
    params = call_args[1]["params"]
    assert params["hl"] == "true"
    assert params["hl.fl"] == "content"
    assert params["hl.snippets"] == "5"
    assert params["hl.fragsize"] == "200"
    assert params["hl.simple.pre"] == "**"
    assert params["hl.simple.post"] == "**"


@pytest.mark.asyncio
async def test_execute_fast_codebase_search_multiple_snippets(mock_mcp):
    """Test handling of multiple snippets per document."""
    # Arrange
    mock_response = {
        "response": {
            "numFound": 1,
            "docs": [
                {
                    "id": "doc1",
                    "source": "file.py",
                    "category_ss": ["source"],
                    "tags_ss": ["py"],
                }
            ],
        },
        "highlighting": {
            "doc1": {
                "content": [
                    "def **test**_one():",
                    "def **test**_two():",
                    "class **Test**Class:",
                ]
            }
        },
    }
    mock_mcp.solr_client.execute_raw_query.return_value = mock_response

    # Act
    result = await execute_fast_codebase_search(
        mcp=mock_mcp,
        pattern="test",
        use_highlighting=True,
    )

    # Assert
    assert result["success"] is True
    assert len(result["matches"]) == 1
    assert result["matches"][0]["match_count"] == 3
    assert len(result["matches"][0]["snippets"]) == 3
