"""Tests for indexing tools."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from solr_mcp.tools.solr_add_documents import execute_add_documents
from solr_mcp.tools.solr_commit import execute_commit
from solr_mcp.tools.solr_delete_documents import execute_delete_documents


@pytest.fixture
def mock_mcp():
    """Create a mock MCP server instance."""
    mcp = MagicMock()
    mcp.solr_client = MagicMock()
    return mcp


class TestAddDocumentsTool:
    """Tests for execute_add_documents tool."""

    @pytest.mark.asyncio
    async def test_add_documents_basic(self, mock_mcp):
        """Test basic document addition."""
        documents = [
            {"id": "doc1", "title": "Test Document"},
        ]

        expected_result = {
            "status": "success",
            "collection": "test_collection",
            "num_documents": 1,
            "committed": True,
            "commit_within": None,
        }

        mock_mcp.solr_client.add_documents = AsyncMock(return_value=expected_result)

        result = await execute_add_documents(
            mock_mcp,
            collection="test_collection",
            documents=documents,
        )

        mock_mcp.solr_client.add_documents.assert_called_once_with(
            collection="test_collection",
            documents=documents,
            commit=True,
            commit_within=None,
            overwrite=True,
        )

        assert result == expected_result

    @pytest.mark.asyncio
    async def test_add_documents_with_options(self, mock_mcp):
        """Test document addition with custom options."""
        documents = [{"id": "doc1"}]

        expected_result = {
            "status": "success",
            "collection": "test_collection",
            "num_documents": 1,
            "committed": False,
            "commit_within": 5000,
        }

        mock_mcp.solr_client.add_documents = AsyncMock(return_value=expected_result)

        result = await execute_add_documents(
            mock_mcp,
            collection="test_collection",
            documents=documents,
            commit=False,
            commit_within=5000,
            overwrite=False,
        )

        mock_mcp.solr_client.add_documents.assert_called_once_with(
            collection="test_collection",
            documents=documents,
            commit=False,
            commit_within=5000,
            overwrite=False,
        )

        assert result == expected_result

    @pytest.mark.asyncio
    async def test_add_documents_multiple(self, mock_mcp):
        """Test adding multiple documents."""
        documents = [
            {"id": "doc1", "title": "First"},
            {"id": "doc2", "title": "Second"},
            {"id": "doc3", "title": "Third"},
        ]

        expected_result = {
            "status": "success",
            "collection": "test_collection",
            "num_documents": 3,
            "committed": True,
            "commit_within": None,
        }

        mock_mcp.solr_client.add_documents = AsyncMock(return_value=expected_result)

        result = await execute_add_documents(
            mock_mcp,
            collection="test_collection",
            documents=documents,
        )

        assert result["num_documents"] == 3


class TestDeleteDocumentsTool:
    """Tests for execute_delete_documents tool."""

    @pytest.mark.asyncio
    async def test_delete_by_ids(self, mock_mcp):
        """Test deleting documents by IDs."""
        expected_result = {
            "status": "success",
            "collection": "test_collection",
            "num_affected": 2,
            "committed": True,
            "delete_by": "id",
        }

        mock_mcp.solr_client.delete_documents = AsyncMock(return_value=expected_result)

        result = await execute_delete_documents(
            mock_mcp,
            collection="test_collection",
            ids=["doc1", "doc2"],
        )

        mock_mcp.solr_client.delete_documents.assert_called_once_with(
            collection="test_collection",
            ids=["doc1", "doc2"],
            query=None,
            commit=True,
        )

        assert result == expected_result

    @pytest.mark.asyncio
    async def test_delete_by_query(self, mock_mcp):
        """Test deleting documents by query."""
        expected_result = {
            "status": "success",
            "collection": "test_collection",
            "num_affected": "unknown (query-based)",
            "committed": True,
            "delete_by": "query",
        }

        mock_mcp.solr_client.delete_documents = AsyncMock(return_value=expected_result)

        result = await execute_delete_documents(
            mock_mcp,
            collection="test_collection",
            query="status:archived",
        )

        mock_mcp.solr_client.delete_documents.assert_called_once_with(
            collection="test_collection",
            ids=None,
            query="status:archived",
            commit=True,
        )

        assert result == expected_result

    @pytest.mark.asyncio
    async def test_delete_no_commit(self, mock_mcp):
        """Test deleting without immediate commit."""
        expected_result = {
            "status": "success",
            "collection": "test_collection",
            "num_affected": 1,
            "committed": False,
            "delete_by": "id",
        }

        mock_mcp.solr_client.delete_documents = AsyncMock(return_value=expected_result)

        result = await execute_delete_documents(
            mock_mcp,
            collection="test_collection",
            ids=["doc1"],
            commit=False,
        )

        mock_mcp.solr_client.delete_documents.assert_called_once_with(
            collection="test_collection",
            ids=["doc1"],
            query=None,
            commit=False,
        )

        assert result["committed"] is False


class TestCommitTool:
    """Tests for execute_commit tool."""

    @pytest.mark.asyncio
    async def test_commit_success(self, mock_mcp):
        """Test successful commit."""
        expected_result = {
            "status": "success",
            "collection": "test_collection",
            "committed": True,
            "commit_type": "hard",
        }

        mock_mcp.solr_client.commit = AsyncMock(return_value=expected_result)

        result = await execute_commit(
            mock_mcp,
            collection="test_collection",
        )

        mock_mcp.solr_client.commit.assert_called_once_with(
            collection="test_collection",
            soft=False,
            wait_searcher=True,
            expunge_deletes=False,
        )

        assert result == expected_result
        assert result["committed"] is True
