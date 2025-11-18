"""Unit tests for fast_file_find tool."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from solr_mcp.tools.fast_file_find import execute_fast_file_find


@pytest.fixture
def mock_mcp():
    """Create mock MCP server."""
    mcp = MagicMock()
    mcp.logger = MagicMock()
    mcp.solr_client = MagicMock()
    mcp.solr_client.execute_raw_query = AsyncMock()
    return mcp


@pytest.mark.asyncio
async def test_execute_fast_file_find_basic(mock_mcp):
    """Test basic file find using Solr."""
    # Arrange
    mock_response = {
        "response": {
            "numFound": 10,
            "docs": [
                {
                    "source": "solr_mcp/tools/fast_file_find.py",
                    "title": "fast_file_find.py",
                    "category_ss": ["source"],
                    "tags_ss": ["py"],
                    "date_indexed_dt": "2024-01-15T10:00:00Z",
                },
                {
                    "source": "solr_mcp/tools/fast_codebase_search.py",
                    "title": "fast_codebase_search.py",
                    "category_ss": ["source"],
                    "tags_ss": ["py"],
                    "date_indexed_dt": "2024-01-15T10:00:00Z",
                },
            ],
        },
    }
    mock_mcp.solr_client.execute_raw_query.return_value = mock_response

    # Act
    result = await execute_fast_file_find(
        mcp=mock_mcp,
        pattern="*.py",
        collection="codebase",
    )

    # Assert
    assert result["success"] is True
    assert result["pattern"] == "*.py"
    assert result["total_found"] == 10
    assert result["returned_results"] == 2
    assert result["search_method"] == "solr"
    assert "10-50x faster" in result["performance_note"]
    assert len(result["files"]) == 2
    assert result["files"][0]["path"] == "solr_mcp/tools/fast_file_find.py"
    assert result["files"][0]["name"] == "fast_file_find.py"
    assert result["files"][0]["categories"] == ["source"]
    assert result["files"][0]["file_type"] == ["py"]


@pytest.mark.asyncio
async def test_execute_fast_file_find_with_file_type(mock_mcp):
    """Test file find with file type filter."""
    # Arrange
    mock_response = {
        "response": {
            "numFound": 5,
            "docs": [
                {
                    "source": "tests/test_something.py",
                    "title": "test_something.py",
                    "category_ss": ["tests"],
                    "tags_ss": ["py"],
                    "date_indexed_dt": "2024-01-15T10:00:00Z",
                }
            ],
        },
    }
    mock_mcp.solr_client.execute_raw_query.return_value = mock_response

    # Act
    result = await execute_fast_file_find(
        mcp=mock_mcp,
        pattern="test_*",
        file_type="py",
        collection="codebase",
    )

    # Assert
    assert result["success"] is True
    assert result["file_type"] == "py"
    assert result["total_found"] == 5

    # Verify query included file type filter
    call_args = mock_mcp.solr_client.execute_raw_query.call_args
    assert "tags_ss:py" in call_args[1]["params"]["q"]


@pytest.mark.asyncio
async def test_execute_fast_file_find_with_category(mock_mcp):
    """Test file find with category filter."""
    # Arrange
    mock_response = {
        "response": {
            "numFound": 3,
            "docs": [
                {
                    "source": "tests/test_file.py",
                    "title": "test_file.py",
                    "category_ss": ["tests"],
                    "tags_ss": ["py"],
                    "date_indexed_dt": "2024-01-15T10:00:00Z",
                }
            ],
        },
    }
    mock_mcp.solr_client.execute_raw_query.return_value = mock_response

    # Act
    result = await execute_fast_file_find(
        mcp=mock_mcp,
        pattern="*.py",
        category="tests",
        collection="codebase",
    )

    # Assert
    assert result["success"] is True
    assert result["category"] == "tests"
    assert result["total_found"] == 3

    # Verify query included category filter
    call_args = mock_mcp.solr_client.execute_raw_query.call_args
    assert "category_ss:tests" in call_args[1]["params"]["q"]


@pytest.mark.asyncio
async def test_execute_fast_file_find_with_file_type_and_category(mock_mcp):
    """Test file find with both file type and category filters."""
    # Arrange
    mock_response = {
        "response": {
            "numFound": 2,
            "docs": [],
        },
    }
    mock_mcp.solr_client.execute_raw_query.return_value = mock_response

    # Act
    result = await execute_fast_file_find(
        mcp=mock_mcp,
        pattern="test_*.py",
        file_type="py",
        category="tests",
    )

    # Assert
    assert result["success"] is True

    # Verify query included both filters
    call_args = mock_mcp.solr_client.execute_raw_query.call_args
    query = call_args[1]["params"]["q"]
    assert "tags_ss:py" in query
    assert "category_ss:tests" in query


@pytest.mark.asyncio
async def test_execute_fast_file_find_max_results(mock_mcp):
    """Test file find with max_results limit."""
    # Arrange
    mock_response = {
        "response": {
            "numFound": 200,
            "docs": [
                {
                    "source": f"file{i}.py",
                    "title": f"file{i}.py",
                    "category_ss": [],
                    "tags_ss": [],
                    "date_indexed_dt": "2024-01-15T10:00:00Z",
                }
                for i in range(50)
            ],
        },
    }
    mock_mcp.solr_client.execute_raw_query.return_value = mock_response

    # Act
    result = await execute_fast_file_find(
        mcp=mock_mcp,
        pattern="*.py",
        max_results=50,
    )

    # Assert
    assert result["success"] is True
    assert result["total_found"] == 200
    assert result["returned_results"] == 50

    # Verify max_results passed to Solr
    call_args = mock_mcp.solr_client.execute_raw_query.call_args
    assert call_args[1]["params"]["rows"] == "50"


@pytest.mark.asyncio
async def test_execute_fast_file_find_pattern_normalization(mock_mcp):
    """Test that pattern is normalized (leading ./ removed)."""
    # Arrange
    mock_response = {
        "response": {"numFound": 0, "docs": []},
    }
    mock_mcp.solr_client.execute_raw_query.return_value = mock_response

    # Act
    result = await execute_fast_file_find(
        mcp=mock_mcp,
        pattern="./path/to/file.py",
    )

    # Assert
    assert result["pattern"] == "path/to/file.py"

    # Verify query uses normalized pattern
    call_args = mock_mcp.solr_client.execute_raw_query.call_args
    assert "source:*path/to/file.py*" in call_args[1]["params"]["q"]


@pytest.mark.asyncio
async def test_execute_fast_file_find_file_type_with_dot(mock_mcp):
    """Test that file type with leading dot is handled correctly."""
    # Arrange
    mock_response = {
        "response": {"numFound": 0, "docs": []},
    }
    mock_mcp.solr_client.execute_raw_query.return_value = mock_response

    # Act
    result = await execute_fast_file_find(
        mcp=mock_mcp,
        pattern="*.py",
        file_type=".py",  # Leading dot should be stripped
    )

    # Assert - the dot is stripped internally
    assert result["file_type"] == "py"

    # Verify query uses stripped version
    call_args = mock_mcp.solr_client.execute_raw_query.call_args
    assert "tags_ss:py" in call_args[1]["params"]["q"]


@pytest.mark.asyncio
async def test_execute_fast_file_find_title_list_handling(mock_mcp):
    """Test handling of title field when it's a list."""
    # Arrange
    mock_response = {
        "response": {
            "numFound": 2,
            "docs": [
                {
                    "source": "file1.py",
                    "title": ["file1.py", "alternate"],  # List
                    "category_ss": [],
                    "tags_ss": [],
                },
                {
                    "source": "file2.py",
                    "title": [],  # Empty list
                    "category_ss": [],
                    "tags_ss": [],
                },
            ],
        },
    }
    mock_mcp.solr_client.execute_raw_query.return_value = mock_response

    # Act
    result = await execute_fast_file_find(
        mcp=mock_mcp,
        pattern="*.py",
    )

    # Assert
    assert result["success"] is True
    assert result["files"][0]["name"] == "file1.py"  # First item from list
    assert result["files"][1]["name"] == "unknown"  # Empty list


@pytest.mark.asyncio
async def test_execute_fast_file_find_fallback_to_find(mock_mcp):
    """Test fallback to find when Solr fails."""
    # Arrange
    mock_mcp.solr_client.execute_raw_query.side_effect = Exception("Solr unavailable")

    # Act
    with patch("solr_mcp.tools.fast_file_find.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            stdout="./file1.py\n./path/to/file2.py\n",
            returncode=0,
        )

        result = await execute_fast_file_find(
            mcp=mock_mcp,
            pattern="*.py",
        )

    # Assert
    assert result["success"] is True
    assert result["search_method"] == "find"
    assert "Solr unavailable" in result["performance_note"]
    assert len(result["files"]) == 2
    assert result["files"][0]["path"] == "./file1.py"
    assert result["files"][0]["name"] == "file1.py"
    assert result["files"][1]["path"] == "./path/to/file2.py"
    assert result["files"][1]["name"] == "file2.py"

    # Verify warning logged
    mock_mcp.logger.warning.assert_called_once()


@pytest.mark.asyncio
async def test_execute_fast_file_find_fallback_with_file_type(mock_mcp):
    """Test find fallback with file type filter."""
    # Arrange
    mock_mcp.solr_client.execute_raw_query.side_effect = Exception("Solr error")

    # Act - Test with pattern WITHOUT wildcard
    with patch("solr_mcp.tools.fast_file_find.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            stdout="./test.py\n",
            returncode=0,
        )

        result = await execute_fast_file_find(
            mcp=mock_mcp,
            pattern="test",  # No wildcard
            file_type="py",
        )

    # Assert
    assert result["success"] is True
    assert result["file_type"] == "py"

    # Verify find called with correct name pattern
    # Pattern without * and with file_type should be: *test*.py
    mock_run.assert_called_once()
    call_args = mock_run.call_args[0][0]
    assert "-name" in call_args
    name_idx = call_args.index("-name")
    assert call_args[name_idx + 1] == "*test*.py"


@pytest.mark.asyncio
async def test_execute_fast_file_find_fallback_pattern_handling(mock_mcp):
    """Test find fallback pattern handling with and without wildcards."""
    # Arrange
    mock_mcp.solr_client.execute_raw_query.side_effect = Exception("Solr error")

    # Test with wildcard pattern
    with patch("solr_mcp.tools.fast_file_find.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="", returncode=0)

        await execute_fast_file_find(
            mcp=mock_mcp,
            pattern="*.py",
            file_type="py",
        )

        # Pattern with * should be used as-is
        call_args = mock_run.call_args[0][0]
        name_idx = call_args.index("-name")
        assert call_args[name_idx + 1] == "*.py"

    # Test without wildcard pattern
    with patch("solr_mcp.tools.fast_file_find.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="", returncode=0)

        await execute_fast_file_find(
            mcp=mock_mcp,
            pattern="test",
            file_type="py",
        )

        # Pattern without * should get wrapped: *test*.py
        call_args = mock_run.call_args[0][0]
        name_idx = call_args.index("-name")
        assert call_args[name_idx + 1] == "*test*.py"


@pytest.mark.asyncio
async def test_execute_fast_file_find_fallback_timeout(mock_mcp):
    """Test find fallback timeout handling."""
    # Arrange
    mock_mcp.solr_client.execute_raw_query.side_effect = Exception("Solr error")

    # Act
    with patch("solr_mcp.tools.fast_file_find.subprocess.run") as mock_run:
        import subprocess

        mock_run.side_effect = subprocess.TimeoutExpired(cmd="find", timeout=30)

        result = await execute_fast_file_find(
            mcp=mock_mcp,
            pattern="*.py",
        )

    # Assert
    assert result["success"] is False
    assert "timed out" in result["error"]
    assert result["pattern"] == "*.py"


@pytest.mark.asyncio
async def test_execute_fast_file_find_fallback_error(mock_mcp):
    """Test find fallback error handling."""
    # Arrange
    mock_mcp.solr_client.execute_raw_query.side_effect = Exception("Solr error")

    # Act
    with patch("solr_mcp.tools.fast_file_find.subprocess.run") as mock_run:
        mock_run.side_effect = Exception("find failed")

        result = await execute_fast_file_find(
            mcp=mock_mcp,
            pattern="*.py",
        )

    # Assert
    assert result["success"] is False
    assert "find failed" in result["error"]


@pytest.mark.asyncio
async def test_execute_fast_file_find_fallback_max_results(mock_mcp):
    """Test that find fallback respects max_results."""
    # Arrange
    mock_mcp.solr_client.execute_raw_query.side_effect = Exception("Solr error")

    # Act
    with patch("solr_mcp.tools.fast_file_find.subprocess.run") as mock_run:
        # Simulate 10 results
        lines = [f"./file{i}.py" for i in range(10)]
        mock_run.return_value = MagicMock(
            stdout="\n".join(lines) + "\n",
            returncode=0,
        )

        result = await execute_fast_file_find(
            mcp=mock_mcp,
            pattern="*.py",
            max_results=5,
        )

    # Assert
    assert result["success"] is True
    assert result["total_found"] == 10
    assert result["returned_results"] == 5  # Limited to max_results


@pytest.mark.asyncio
async def test_execute_fast_file_find_empty_results(mock_mcp):
    """Test file find with no matches."""
    # Arrange
    mock_response = {
        "response": {
            "numFound": 0,
            "docs": [],
        },
    }
    mock_mcp.solr_client.execute_raw_query.return_value = mock_response

    # Act
    result = await execute_fast_file_find(
        mcp=mock_mcp,
        pattern="nonexistent.xyz",
    )

    # Assert
    assert result["success"] is True
    assert result["total_found"] == 0
    assert result["returned_results"] == 0
    assert result["files"] == []


@pytest.mark.asyncio
async def test_execute_fast_file_find_query_structure(mock_mcp):
    """Test that Solr query is structured correctly."""
    # Arrange
    mock_response = {
        "response": {"numFound": 0, "docs": []},
    }
    mock_mcp.solr_client.execute_raw_query.return_value = mock_response

    # Act
    await execute_fast_file_find(
        mcp=mock_mcp,
        pattern="test_*.py",
        file_type="py",
        category="tests",
    )

    # Assert
    call_args = mock_mcp.solr_client.execute_raw_query.call_args
    params = call_args[1]["params"]

    # Verify all query parts are ANDed together
    query = params["q"]
    assert "source:*test_*.py*" in query
    assert "tags_ss:py" in query
    assert "category_ss:tests" in query
    assert query.count(" AND ") == 2  # 3 parts = 2 ANDs

    # Verify other params
    assert params["fl"] == "source,title,category_ss,tags_ss,date_indexed_dt"
    assert params["sort"] == "source asc"
    assert params["wt"] == "json"


@pytest.mark.asyncio
async def test_execute_fast_file_find_fallback_without_file_type(mock_mcp):
    """Test find fallback without file type - pattern handling."""
    # Arrange
    mock_mcp.solr_client.execute_raw_query.side_effect = Exception("Solr error")

    # Test with wildcard
    with patch("solr_mcp.tools.fast_file_find.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="", returncode=0)

        await execute_fast_file_find(
            mcp=mock_mcp,
            pattern="*.py",
        )

        call_args = mock_run.call_args[0][0]
        name_idx = call_args.index("-name")
        assert call_args[name_idx + 1] == "*.py"

    # Test without wildcard
    with patch("solr_mcp.tools.fast_file_find.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="", returncode=0)

        await execute_fast_file_find(
            mcp=mock_mcp,
            pattern="README",
        )

        call_args = mock_run.call_args[0][0]
        name_idx = call_args.index("-name")
        assert call_args[name_idx + 1] == "*README*"
