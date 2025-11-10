"""Unit tests for QueryExecutor class."""

import json
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import aiohttp
import pytest
import requests

from solr_mcp.solr.exceptions import (
    DocValuesError,
    QueryError,
    SQLExecutionError,
    SQLParseError,
)
from solr_mcp.solr.query.executor import QueryExecutor
from solr_mcp.solr.vector.results import VectorSearchResults


@pytest.fixture
def executor():
    """Create a QueryExecutor instance."""
    return QueryExecutor("http://localhost:8983/solr")


@pytest.fixture
def mock_vector_results():
    """Create mock VectorSearchResults."""
    return VectorSearchResults(
        results=[],
        total_found=3,
        top_k=10,
    )


def create_mock_aiohttp_response(status, headers, text_data):
    """Helper to create a properly mocked aiohttp response with async context manager support."""
    mock_response = AsyncMock()
    mock_response.status = status
    mock_response.headers = headers
    mock_response.text = AsyncMock(return_value=text_data)
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=None)
    return mock_response


def create_mock_aiohttp_session(mock_response):
    """Helper to create a properly mocked aiohttp ClientSession with async context manager support."""
    mock_session = AsyncMock()
    mock_session.post = Mock(return_value=mock_response)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    return mock_session


class TestQueryExecutorInit:
    """Test QueryExecutor initialization."""

    def test_init_basic(self):
        """Test basic initialization."""
        executor = QueryExecutor("http://localhost:8983/solr")
        assert executor.base_url == "http://localhost:8983/solr"

    def test_init_strips_trailing_slash(self):
        """Test that trailing slash is removed."""
        executor = QueryExecutor("http://localhost:8983/solr/")
        assert executor.base_url == "http://localhost:8983/solr"

    def test_init_multiple_trailing_slashes(self):
        """Test that multiple trailing slashes are removed."""
        executor = QueryExecutor("http://localhost:8983/solr///")
        assert executor.base_url == "http://localhost:8983/solr"


class TestExecuteSelectQuery:
    """Test execute_select_query method."""

    @pytest.mark.asyncio
    async def test_execute_select_query_success(self, executor):
        """Test successful SQL query execution."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "result-set": {
                "docs": [
                    {"id": "1", "title": "Test Doc 1"},
                    {"id": "2", "title": "Test Doc 2"},
                ]
            }
        }

        with patch("requests.post", return_value=mock_response) as mock_post:
            result = await executor.execute_select_query(
                "SELECT * FROM test_collection", "test_collection"
            )

            # Verify request was made correctly
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert call_args[0][0] == "http://localhost:8983/solr/test_collection/sql?aggregationMode=facet"
            assert call_args[1]["data"] == {"stmt": "SELECT * FROM test_collection"}
            assert call_args[1]["headers"] == {"Content-Type": "application/x-www-form-urlencoded"}

            # Verify result
            assert "result-set" in result
            assert result["result-set"]["numFound"] == 2
            assert len(result["result-set"]["docs"]) == 2

    @pytest.mark.asyncio
    async def test_execute_select_query_strips_whitespace(self, executor):
        """Test that query whitespace is stripped."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result-set": {"docs": []}}

        with patch("requests.post", return_value=mock_response) as mock_post:
            await executor.execute_select_query(
                "  SELECT * FROM test_collection  ", "test_collection"
            )

            call_args = mock_post.call_args
            assert call_args[1]["data"]["stmt"] == "SELECT * FROM test_collection"

    @pytest.mark.asyncio
    async def test_execute_select_query_http_error(self, executor):
        """Test handling of HTTP error responses."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"

        with patch("requests.post", return_value=mock_response):
            with pytest.raises(SQLExecutionError) as exc_info:
                await executor.execute_select_query(
                    "SELECT * FROM test_collection", "test_collection"
                )
            assert "SQL query failed with status 400" in str(exc_info.value)
            assert "Bad Request" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_execute_select_query_docvalues_error(self, executor):
        """Test handling of DocValues error in response."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "result-set": {
                "docs": [
                    {
                        "EXCEPTION": "Field 'title' must have DocValues to use this feature",
                        "RESPONSE_TIME": 42,
                    }
                ]
            }
        }

        with patch("requests.post", return_value=mock_response):
            with pytest.raises(DocValuesError) as exc_info:
                await executor.execute_select_query(
                    "SELECT * FROM test_collection", "test_collection"
                )
            assert "must have DocValues" in str(exc_info.value)
            assert exc_info.value.response_time == 42
            assert exc_info.value.error_type == "MISSING_DOCVALUES"

    @pytest.mark.asyncio
    async def test_execute_select_query_parse_error(self, executor):
        """Test handling of SQL parse error in response."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "result-set": {
                "docs": [
                    {
                        "EXCEPTION": "parse failed: Syntax error near SELECT",
                        "RESPONSE_TIME": 10,
                    }
                ]
            }
        }

        with patch("requests.post", return_value=mock_response):
            with pytest.raises(SQLParseError) as exc_info:
                await executor.execute_select_query(
                    "INVALID SQL", "test_collection"
                )
            assert "parse failed" in str(exc_info.value)
            assert exc_info.value.response_time == 10
            assert exc_info.value.error_type == "PARSE_ERROR"

    @pytest.mark.asyncio
    async def test_execute_select_query_generic_sql_error(self, executor):
        """Test handling of generic SQL execution error."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "result-set": {
                "docs": [
                    {
                        "EXCEPTION": "Unknown error occurred",
                        "RESPONSE_TIME": 100,
                    }
                ]
            }
        }

        with patch("requests.post", return_value=mock_response):
            with pytest.raises(SQLExecutionError) as exc_info:
                await executor.execute_select_query(
                    "SELECT * FROM test_collection", "test_collection"
                )
            assert "Unknown error occurred" in str(exc_info.value)
            assert exc_info.value.response_time == 100
            assert exc_info.value.error_type == "SOLR_SQL_ERROR"

    @pytest.mark.asyncio
    async def test_execute_select_query_exception_without_response_time(self, executor):
        """Test handling of exception without RESPONSE_TIME."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "result-set": {
                "docs": [
                    {
                        "EXCEPTION": "Some error",
                    }
                ]
            }
        }

        with patch("requests.post", return_value=mock_response):
            with pytest.raises(SQLExecutionError) as exc_info:
                await executor.execute_select_query(
                    "SELECT * FROM test_collection", "test_collection"
                )
            assert exc_info.value.response_time is None

    @pytest.mark.asyncio
    async def test_execute_select_query_network_error(self, executor):
        """Test handling of network/connection errors."""
        with patch("requests.post", side_effect=requests.RequestException("Network error")):
            with pytest.raises(SQLExecutionError) as exc_info:
                await executor.execute_select_query(
                    "SELECT * FROM test_collection", "test_collection"
                )
            assert "SQL query failed" in str(exc_info.value)
            assert "Network error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_execute_select_query_json_decode_error(self, executor):
        """Test handling of invalid JSON response."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)

        with patch("requests.post", return_value=mock_response):
            with pytest.raises(SQLExecutionError) as exc_info:
                await executor.execute_select_query(
                    "SELECT * FROM test_collection", "test_collection"
                )
            assert "SQL query failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_execute_select_query_reraise_specific_exceptions(self, executor):
        """Test that specific exceptions are re-raised correctly."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "result-set": {
                "docs": [
                    {
                        "EXCEPTION": "parse failed: error",
                    }
                ]
            }
        }

        with patch("requests.post", return_value=mock_response):
            # Should raise SQLParseError, not wrapped in another exception
            with pytest.raises(SQLParseError):
                await executor.execute_select_query(
                    "SELECT * FROM test_collection", "test_collection"
                )


class TestExecuteVectorSelectQuery:
    """Test execute_vector_select_query method."""

    @pytest.mark.asyncio
    async def test_execute_vector_select_query_success(self, executor, mock_vector_results):
        """Test successful vector SQL query execution."""
        mock_vector_results.results = [
            MagicMock(docid="1", score=0.9),
            MagicMock(docid="2", score=0.8),
        ]

        mock_response_data = {
            "result-set": {
                "docs": [
                    {"id": "1", "title": "Doc 1"},
                    {"id": "2", "title": "Doc 2"},
                ]
            }
        }

        mock_response = create_mock_aiohttp_response(
            status=200,
            headers={"Content-Type": "application/json"},
            text_data=json.dumps(mock_response_data)
        )
        mock_session = create_mock_aiohttp_session(mock_response)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await executor.execute_vector_select_query(
                query="SELECT * FROM test_collection",
                vector=[0.1, 0.2, 0.3],
                field="vector_field",
                collection="test_collection",
                vector_results=mock_vector_results,
            )

            assert "result-set" in result
            assert len(result["result-set"]["docs"]) == 2

    @pytest.mark.asyncio
    async def test_execute_vector_select_query_with_where_clause(self, executor, mock_vector_results):
        """Test vector query with existing WHERE clause."""
        mock_vector_results.results = [MagicMock(docid="1")]

        mock_response = create_mock_aiohttp_response(
            status=200,
            headers={"Content-Type": "application/json"},
            text_data=json.dumps({"result-set": {"docs": []}})
        )
        mock_session = create_mock_aiohttp_session(mock_response)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            await executor.execute_vector_select_query(
                query="SELECT * FROM test_collection WHERE status = 'active'",
                vector=[0.1, 0.2],
                field="vector_field",
                collection="test_collection",
                vector_results=mock_vector_results,
            )

            call_args = mock_session.post.call_args
            stmt = call_args[1]["data"]["stmt"]
            assert "WHERE status = 'active'" in stmt
            assert "AND id IN (1)" in stmt

    @pytest.mark.asyncio
    async def test_execute_vector_select_query_with_limit(self, executor, mock_vector_results):
        """Test vector query with existing LIMIT clause."""
        mock_vector_results.results = [MagicMock(docid="1")]

        mock_response = create_mock_aiohttp_response(
            status=200,
            headers={"Content-Type": "application/json"},
            text_data=json.dumps({"result-set": {"docs": []}})
        )
        mock_session = create_mock_aiohttp_session(mock_response)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            await executor.execute_vector_select_query(
                query="SELECT * FROM test_collection LIMIT 5",
                vector=[0.1],
                field="vector_field",
                collection="test_collection",
                vector_results=mock_vector_results,
            )

            call_args = mock_session.post.call_args
            stmt = call_args[1]["data"]["stmt"]
            assert "LIMIT 5" in stmt

    @pytest.mark.asyncio
    async def test_execute_vector_select_query_no_results(self, executor, mock_vector_results):
        """Test vector query with no vector results."""
        mock_vector_results.results = []

        mock_response = create_mock_aiohttp_response(
            status=200,
            headers={"Content-Type": "application/json"},
            text_data=json.dumps({"result-set": {"docs": []}})
        )
        mock_session = create_mock_aiohttp_session(mock_response)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await executor.execute_vector_select_query(
                query="SELECT * FROM test_collection",
                vector=[0.1],
                field="vector_field",
                collection="test_collection",
                vector_results=mock_vector_results,
            )

            call_args = mock_session.post.call_args
            stmt = call_args[1]["data"]["stmt"]
            assert "WHERE 1=0" in stmt

    @pytest.mark.asyncio
    async def test_execute_vector_select_query_adds_default_limit(self, executor, mock_vector_results):
        """Test that default LIMIT 10 is added if not present."""
        mock_vector_results.results = [MagicMock(docid="1")]

        mock_response = create_mock_aiohttp_response(
            status=200,
            headers={"Content-Type": "application/json"},
            text_data=json.dumps({"result-set": {"docs": []}})
        )
        mock_session = create_mock_aiohttp_session(mock_response)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            await executor.execute_vector_select_query(
                query="SELECT * FROM test_collection",
                vector=[0.1],
                field="vector_field",
                collection="test_collection",
                vector_results=mock_vector_results,
            )

            call_args = mock_session.post.call_args
            stmt = call_args[1]["data"]["stmt"]
            assert "LIMIT 10" in stmt

    @pytest.mark.asyncio
    async def test_execute_vector_select_query_http_error(self, executor, mock_vector_results):
        """Test handling of HTTP error in vector query."""
        mock_vector_results.results = [MagicMock(docid="1")]

        mock_response = create_mock_aiohttp_response(
            status=500,
            headers={},
            text_data="Internal Server Error"
        )
        mock_session = create_mock_aiohttp_session(mock_response)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            with pytest.raises(QueryError) as exc_info:
                await executor.execute_vector_select_query(
                    query="SELECT * FROM test_collection",
                    vector=[0.1],
                    field="vector_field",
                    collection="test_collection",
                    vector_results=mock_vector_results,
                )
            assert "SQL query failed" in str(exc_info.value)
            assert "Internal Server Error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_execute_vector_select_query_text_plain_response(self, executor, mock_vector_results):
        """Test handling of text/plain response that contains JSON."""
        mock_vector_results.results = [MagicMock(docid="1")]

        mock_response_data = {"result-set": {"docs": []}}
        mock_response = create_mock_aiohttp_response(
            status=200,
            headers={"Content-Type": "text/plain"},
            text_data=json.dumps(mock_response_data)
        )
        mock_session = create_mock_aiohttp_session(mock_response)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await executor.execute_vector_select_query(
                query="SELECT * FROM test_collection",
                vector=[0.1],
                field="vector_field",
                collection="test_collection",
                vector_results=mock_vector_results,
            )
            assert "result-set" in result

    @pytest.mark.asyncio
    async def test_execute_vector_select_query_non_json_text_response(self, executor, mock_vector_results):
        """Test handling of text/plain response that is not JSON."""
        mock_vector_results.results = [MagicMock(docid="1")]

        mock_response = create_mock_aiohttp_response(
            status=200,
            headers={"Content-Type": "text/plain"},
            text_data="Not JSON at all"
        )
        mock_session = create_mock_aiohttp_session(mock_response)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await executor.execute_vector_select_query(
                query="SELECT * FROM test_collection",
                vector=[0.1],
                field="vector_field",
                collection="test_collection",
                vector_results=mock_vector_results,
            )
            assert result["result-set"]["numFound"] == 0
            assert result["result-set"]["docs"] == []

    @pytest.mark.asyncio
    async def test_execute_vector_select_query_parse_error(self, executor, mock_vector_results):
        """Test handling of response parse error."""
        mock_vector_results.results = [MagicMock(docid="1")]

        mock_response = create_mock_aiohttp_response(
            status=200,
            headers={"Content-Type": "application/json"},
            text_data='{"invalid": '
        )
        mock_session = create_mock_aiohttp_session(mock_response)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            with pytest.raises(QueryError) as exc_info:
                await executor.execute_vector_select_query(
                    query="SELECT * FROM test_collection",
                    vector=[0.1],
                    field="vector_field",
                    collection="test_collection",
                    vector_results=mock_vector_results,
                )
            assert "Failed to parse response" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_execute_vector_select_query_network_error(self, executor, mock_vector_results):
        """Test handling of network errors."""
        mock_vector_results.results = [MagicMock(docid="1")]

        mock_session = AsyncMock()
        mock_session.post = Mock(side_effect=aiohttp.ClientError("Connection failed"))
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            with pytest.raises(QueryError) as exc_info:
                await executor.execute_vector_select_query(
                    query="SELECT * FROM test_collection",
                    vector=[0.1],
                    field="vector_field",
                    collection="test_collection",
                    vector_results=mock_vector_results,
                )
            assert "Error executing vector query" in str(exc_info.value)
            assert "Connection failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_execute_vector_select_query_multiple_doc_ids(self, executor, mock_vector_results):
        """Test vector query with multiple document IDs."""
        mock_vector_results.results = [
            MagicMock(docid="1"),
            MagicMock(docid="2"),
            MagicMock(docid="3"),
        ]

        mock_response = create_mock_aiohttp_response(
            status=200,
            headers={"Content-Type": "application/json"},
            text_data=json.dumps({"result-set": {"docs": []}})
        )
        mock_session = create_mock_aiohttp_session(mock_response)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            await executor.execute_vector_select_query(
                query="SELECT * FROM test_collection",
                vector=[0.1],
                field="vector_field",
                collection="test_collection",
                vector_results=mock_vector_results,
            )

            call_args = mock_session.post.call_args
            stmt = call_args[1]["data"]["stmt"]
            assert "WHERE id IN (1,2,3)" in stmt

    @pytest.mark.asyncio
    async def test_execute_vector_select_query_case_insensitive_where(self, executor, mock_vector_results):
        """Test that WHERE clause detection is case insensitive."""
        mock_vector_results.results = [MagicMock(docid="1")]

        mock_response = create_mock_aiohttp_response(
            status=200,
            headers={"Content-Type": "application/json"},
            text_data=json.dumps({"result-set": {"docs": []}})
        )
        mock_session = create_mock_aiohttp_session(mock_response)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            await executor.execute_vector_select_query(
                query="SELECT * FROM test_collection where status = 'active'",
                vector=[0.1],
                field="vector_field",
                collection="test_collection",
                vector_results=mock_vector_results,
            )

            call_args = mock_session.post.call_args
            stmt = call_args[1]["data"]["stmt"]
            assert "AND id IN (1)" in stmt

    @pytest.mark.asyncio
    async def test_execute_vector_select_query_case_insensitive_limit(self, executor, mock_vector_results):
        """Test that LIMIT clause detection is case insensitive."""
        mock_vector_results.results = [MagicMock(docid="1")]

        mock_response = create_mock_aiohttp_response(
            status=200,
            headers={"Content-Type": "application/json"},
            text_data=json.dumps({"result-set": {"docs": []}})
        )
        mock_session = create_mock_aiohttp_session(mock_response)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            await executor.execute_vector_select_query(
                query="SELECT * FROM test_collection limit 20",
                vector=[0.1],
                field="vector_field",
                collection="test_collection",
                vector_results=mock_vector_results,
            )

            call_args = mock_session.post.call_args
            stmt = call_args[1]["data"]["stmt"]
            assert "LIMIT 20" in stmt
            assert "LIMIT 10" not in stmt

    @pytest.mark.asyncio
    async def test_execute_vector_select_query_reraise_query_error(self, executor, mock_vector_results):
        """Test that QueryError is re-raised correctly."""
        mock_vector_results.results = [MagicMock(docid="1")]

        mock_response = create_mock_aiohttp_response(
            status=400,
            headers={},
            text_data="Bad Request"
        )
        mock_session = create_mock_aiohttp_session(mock_response)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            with pytest.raises(QueryError):
                await executor.execute_vector_select_query(
                    query="SELECT * FROM test_collection",
                    vector=[0.1],
                    field="vector_field",
                    collection="test_collection",
                    vector_results=mock_vector_results,
                )
