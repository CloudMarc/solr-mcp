"""Tests for SolrClient indexing functionality."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from solr_mcp.solr.client import SolrClient
from solr_mcp.solr.config import SolrConfig
from solr_mcp.solr.exceptions import IndexingError, SolrError


@pytest.fixture
def mock_config():
    """Create a mock SolrConfig."""
    return SolrConfig(
        solr_base_url="http://localhost:8983/solr",
        zookeeper_hosts=["localhost:2181"],
        connection_timeout=10,
    )


@pytest.fixture
def mock_collection_provider():
    """Create a mock collection provider."""
    provider = AsyncMock()
    provider.list_collections = AsyncMock(return_value=["test_collection"])
    return provider


@pytest.fixture
def mock_pysolr_client():
    """Create a mock pysolr.Solr client."""
    import json

    client = MagicMock()
    # pysolr methods return JSON strings
    client.add = MagicMock(
        return_value=json.dumps({"responseHeader": {"status": 0, "QTime": 10}})
    )
    client.delete = MagicMock(
        return_value=json.dumps({"responseHeader": {"status": 0, "QTime": 5}})
    )
    client.commit = MagicMock()
    return client


@pytest.fixture
def solr_client(mock_config, mock_collection_provider, mock_pysolr_client):
    """Create a SolrClient with mocked dependencies."""
    client = SolrClient(
        config=mock_config,
        collection_provider=mock_collection_provider,
    )
    client._solr_client = mock_pysolr_client
    return client


class TestAddDocuments:
    """Tests for add_documents method."""

    @pytest.mark.asyncio
    async def test_add_documents_success(self, solr_client, mock_pysolr_client):
        """Test successfully adding documents."""
        documents = [
            {"id": "doc1", "title": "First Document"},
            {"id": "doc2", "title": "Second Document"},
        ]

        result = await solr_client.add_documents(
            collection="test_collection",
            documents=documents,
        )

        # Verify pysolr.add was called correctly
        mock_pysolr_client.add.assert_called_once_with(
            documents,
            commit=True,
            commitWithin=None,
            overwrite=True,
        )

        # Verify response (raw Solr format)
        assert "responseHeader" in result
        assert result["responseHeader"]["status"] == 0

    @pytest.mark.asyncio
    async def test_add_documents_no_commit(self, solr_client, mock_pysolr_client):
        """Test adding documents without immediate commit."""
        documents = [{"id": "doc1", "title": "Test"}]

        result = await solr_client.add_documents(
            collection="test_collection",
            documents=documents,
            commit=False,
        )

        mock_pysolr_client.add.assert_called_once_with(
            documents,
            commit=False,
            commitWithin=None,
            overwrite=True,
        )

        # Verify raw Solr response
        assert "responseHeader" in result
        assert result["responseHeader"]["status"] == 0

    @pytest.mark.asyncio
    async def test_add_documents_commit_within(self, solr_client, mock_pysolr_client):
        """Test adding documents with commitWithin."""
        documents = [{"id": "doc1", "title": "Test"}]

        result = await solr_client.add_documents(
            collection="test_collection",
            documents=documents,
            commit=False,
            commit_within=5000,
        )

        mock_pysolr_client.add.assert_called_once_with(
            documents,
            commit=False,
            commitWithin=5000,
            overwrite=True,
        )

        # Verify raw Solr response
        assert "responseHeader" in result
        assert result["responseHeader"]["status"] == 0

    @pytest.mark.asyncio
    async def test_add_documents_no_overwrite(self, solr_client, mock_pysolr_client):
        """Test adding documents without overwrite."""
        documents = [{"id": "doc1", "title": "Test"}]

        await solr_client.add_documents(
            collection="test_collection",
            documents=documents,
            overwrite=False,
        )

        mock_pysolr_client.add.assert_called_once_with(
            documents,
            commit=True,
            commitWithin=None,
            overwrite=False,
        )

    @pytest.mark.asyncio
    async def test_add_documents_empty_list(self, solr_client):
        """Test adding empty list of documents raises error."""
        with pytest.raises(IndexingError, match="No documents provided"):
            await solr_client.add_documents(
                collection="test_collection",
                documents=[],
            )

    @pytest.mark.asyncio
    async def test_add_documents_collection_not_found(
        self, solr_client, mock_collection_provider
    ):
        """Test adding documents to non-existent collection raises error."""
        mock_collection_provider.list_collections.return_value = ["other_collection"]

        documents = [{"id": "doc1", "title": "Test"}]

        with pytest.raises(
            SolrError, match="Collection 'test_collection' does not exist"
        ):
            await solr_client.add_documents(
                collection="test_collection",
                documents=documents,
            )

    @pytest.mark.asyncio
    async def test_add_documents_pysolr_error(self, solr_client, mock_pysolr_client):
        """Test handling pysolr errors."""
        mock_pysolr_client.add.side_effect = Exception("Solr server error")

        documents = [{"id": "doc1", "title": "Test"}]

        with pytest.raises(IndexingError, match="Failed to add documents"):
            await solr_client.add_documents(
                collection="test_collection",
                documents=documents,
            )


class TestDeleteDocuments:
    """Tests for delete_documents method."""

    @pytest.mark.asyncio
    async def test_delete_by_ids(self, solr_client):
        """Test deleting documents by IDs."""
        ids = ["doc1", "doc2", "doc3"]

        with patch("requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"responseHeader": {"status": 0}}
            mock_post.return_value = mock_response

            result = await solr_client.delete_documents(
                collection="test_collection",
                ids=ids,
            )

            # Verify requests.post was called correctly
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert "test_collection/update" in call_args[0][0]
            assert call_args[1]["json"] == {"delete": ids}

            assert "responseHeader" in result
            assert result["responseHeader"]["status"] == 0

    @pytest.mark.asyncio
    async def test_delete_by_query(self, solr_client):
        """Test deleting documents by query."""
        query = "status:archived"

        with patch("requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"responseHeader": {"status": 0}}
            mock_post.return_value = mock_response

            result = await solr_client.delete_documents(
                collection="test_collection",
                query=query,
            )

            # Verify requests.post was called correctly
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert call_args[1]["json"] == {"delete": {"query": query}}

            assert "responseHeader" in result
            assert result["responseHeader"]["status"] == 0

    @pytest.mark.asyncio
    async def test_delete_no_commit(self, solr_client):
        """Test deleting without immediate commit."""
        with patch("requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"responseHeader": {"status": 0}}
            mock_post.return_value = mock_response

            result = await solr_client.delete_documents(
                collection="test_collection",
                ids=["doc1"],
                commit=False,
            )

            # Verify requests.post was called correctly
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            # When commit=False, we don't add commit to params
            assert (
                "commit" not in call_args[1]["params"]
                or call_args[1]["params"]["commit"] == "false"
            )

            # Verify raw Solr response
            assert "responseHeader" in result
            assert result["responseHeader"]["status"] == 0

    @pytest.mark.asyncio
    async def test_delete_both_ids_and_query_error(self, solr_client):
        """Test error when both ids and query are provided."""
        with pytest.raises(
            IndexingError, match="Cannot specify both 'ids' and 'query'"
        ):
            await solr_client.delete_documents(
                collection="test_collection",
                ids=["doc1"],
                query="*:*",
            )

    @pytest.mark.asyncio
    async def test_delete_neither_ids_nor_query_error(self, solr_client):
        """Test error when neither ids nor query are provided."""
        with pytest.raises(IndexingError, match="Must specify either 'ids' or 'query'"):
            await solr_client.delete_documents(
                collection="test_collection",
            )

    @pytest.mark.asyncio
    async def test_delete_collection_not_found(
        self, solr_client, mock_collection_provider
    ):
        """Test deleting from non-existent collection raises error."""
        mock_collection_provider.list_collections.return_value = ["other_collection"]

        with pytest.raises(
            SolrError, match="Collection 'test_collection' does not exist"
        ):
            await solr_client.delete_documents(
                collection="test_collection",
                ids=["doc1"],
            )

    @pytest.mark.asyncio
    async def test_delete_pysolr_error(self, solr_client):
        """Test handling requests errors."""
        with patch("requests.post") as mock_post:
            mock_post.side_effect = Exception("Network error")

            with pytest.raises(IndexingError, match="Failed to delete documents"):
                await solr_client.delete_documents(
                    collection="test_collection",
                    ids=["doc1"],
                )


class TestCommit:
    """Tests for commit method."""

    @pytest.mark.asyncio
    async def test_commit_success(self, solr_client):
        """Test successfully committing changes."""
        # Mock requests.post since commit() uses requests directly
        with patch("requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"responseHeader": {"status": 0}}
            mock_post.return_value = mock_response

            result = await solr_client.commit(collection="test_collection")

            # Verify requests.post was called correctly
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert "test_collection/update" in call_args[0][0]
            assert call_args[1]["params"]["commit"] == "true"

            assert "responseHeader" in result
            assert result["responseHeader"]["status"] == 0

    @pytest.mark.asyncio
    async def test_commit_collection_not_found(
        self, solr_client, mock_collection_provider
    ):
        """Test committing to non-existent collection raises error."""
        mock_collection_provider.list_collections.return_value = ["other_collection"]

        with pytest.raises(
            SolrError, match="Collection 'test_collection' does not exist"
        ):
            await solr_client.commit(collection="test_collection")

    @pytest.mark.asyncio
    async def test_commit_request_error(self, solr_client):
        """Test handling request errors."""
        with patch("requests.post") as mock_post:
            mock_post.side_effect = Exception("Connection error")

            with pytest.raises(SolrError, match="Failed to commit"):
                await solr_client.commit(collection="test_collection")
