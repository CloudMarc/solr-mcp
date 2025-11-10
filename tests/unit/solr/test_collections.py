"""Unit tests for collection providers."""

import pytest
from unittest.mock import MagicMock, Mock, patch
from kazoo.exceptions import ConnectionLoss, NoNodeError

from solr_mcp.solr.collections import HttpCollectionProvider, ZooKeeperCollectionProvider
from solr_mcp.solr.exceptions import ConnectionError, SolrError


class TestHttpCollectionProvider:
    """Tests for HttpCollectionProvider."""

    def test_init(self):
        """Test initialization."""
        provider = HttpCollectionProvider("http://localhost:8983/solr")
        assert provider.base_url == "http://localhost:8983/solr"

    def test_init_strips_trailing_slash(self):
        """Test that trailing slash is removed from base_url."""
        provider = HttpCollectionProvider("http://localhost:8983/solr/")
        assert provider.base_url == "http://localhost:8983/solr"

    @pytest.mark.asyncio
    @patch("solr_mcp.solr.collections.requests.get")
    async def test_list_collections_success(self, mock_get):
        """Test successful collection listing."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"collections": ["collection1", "collection2"]}
        mock_get.return_value = mock_response

        provider = HttpCollectionProvider("http://localhost:8983/solr")
        collections = await provider.list_collections()

        assert collections == ["collection1", "collection2"]
        mock_get.assert_called_once_with(
            "http://localhost:8983/solr/admin/collections?action=LIST"
        )

    @pytest.mark.asyncio
    @patch("solr_mcp.solr.collections.requests.get")
    async def test_list_collections_empty(self, mock_get):
        """Test listing collections when none exist."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"collections": []}
        mock_get.return_value = mock_response

        provider = HttpCollectionProvider("http://localhost:8983/solr")
        collections = await provider.list_collections()

        assert collections == []

    @pytest.mark.asyncio
    @patch("solr_mcp.solr.collections.requests.get")
    async def test_list_collections_http_error(self, mock_get):
        """Test handling HTTP errors."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_get.return_value = mock_response

        provider = HttpCollectionProvider("http://localhost:8983/solr")
        
        with pytest.raises(SolrError, match="Failed to list collections"):
            await provider.list_collections()

    @pytest.mark.asyncio
    @patch("solr_mcp.solr.collections.requests.get")
    async def test_list_collections_network_error(self, mock_get):
        """Test handling network errors."""
        mock_get.side_effect = Exception("Network error")

        provider = HttpCollectionProvider("http://localhost:8983/solr")
        
        with pytest.raises(SolrError, match="Failed to list collections"):
            await provider.list_collections()

    @pytest.mark.asyncio
    @patch("solr_mcp.solr.collections.requests.get")
    async def test_collection_exists_true(self, mock_get):
        """Test checking if collection exists (true case)."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"collections": ["collection1", "collection2"]}
        mock_get.return_value = mock_response

        provider = HttpCollectionProvider("http://localhost:8983/solr")
        exists = await provider.collection_exists("collection1")

        assert exists is True

    @pytest.mark.asyncio
    @patch("solr_mcp.solr.collections.requests.get")
    async def test_collection_exists_false(self, mock_get):
        """Test checking if collection exists (false case)."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"collections": ["collection1", "collection2"]}
        mock_get.return_value = mock_response

        provider = HttpCollectionProvider("http://localhost:8983/solr")
        exists = await provider.collection_exists("nonexistent")

        assert exists is False

    @pytest.mark.asyncio
    @patch("solr_mcp.solr.collections.requests.get")
    async def test_collection_exists_error(self, mock_get):
        """Test error handling in collection_exists."""
        mock_get.side_effect = Exception("Network error")

        provider = HttpCollectionProvider("http://localhost:8983/solr")
        
        with pytest.raises(SolrError, match="Failed to check if collection exists"):
            await provider.collection_exists("collection1")


class TestZooKeeperCollectionProvider:
    """Tests for ZooKeeperCollectionProvider."""

    @patch("solr_mcp.solr.collections.KazooClient")
    def test_init_success(self, mock_kazoo_class):
        """Test successful initialization."""
        mock_zk = MagicMock()
        mock_zk.exists.return_value = True
        mock_kazoo_class.return_value = mock_zk

        provider = ZooKeeperCollectionProvider(["localhost:2181"])

        assert provider.hosts == ["localhost:2181"]
        assert provider.zk is not None
        mock_kazoo_class.assert_called_once_with(hosts="localhost:2181")
        mock_zk.start.assert_called_once()
        mock_zk.exists.assert_called_once_with("/collections")

    @patch("solr_mcp.solr.collections.KazooClient")
    def test_init_no_collections_path(self, mock_kazoo_class):
        """Test initialization when /collections path doesn't exist."""
        mock_zk = MagicMock()
        mock_zk.exists.return_value = False
        mock_kazoo_class.return_value = mock_zk

        with pytest.raises(ConnectionError, match="/collections path does not exist"):
            ZooKeeperCollectionProvider(["localhost:2181"])

    @patch("solr_mcp.solr.collections.KazooClient")
    def test_init_connection_loss(self, mock_kazoo_class):
        """Test initialization when connection is lost."""
        mock_zk = MagicMock()
        mock_zk.start.side_effect = ConnectionLoss("Connection lost")
        mock_kazoo_class.return_value = mock_zk

        with pytest.raises(ConnectionError, match="Failed to connect to ZooKeeper"):
            ZooKeeperCollectionProvider(["localhost:2181"])

    @patch("solr_mcp.solr.collections.KazooClient")
    def test_init_generic_error(self, mock_kazoo_class):
        """Test initialization with generic error."""
        mock_zk = MagicMock()
        mock_zk.start.side_effect = Exception("Generic error")
        mock_kazoo_class.return_value = mock_zk

        with pytest.raises(ConnectionError, match="Error connecting to ZooKeeper"):
            ZooKeeperCollectionProvider(["localhost:2181"])

    @patch("solr_mcp.solr.collections.KazooClient")
    def test_init_multiple_hosts(self, mock_kazoo_class):
        """Test initialization with multiple ZooKeeper hosts."""
        mock_zk = MagicMock()
        mock_zk.exists.return_value = True
        mock_kazoo_class.return_value = mock_zk

        provider = ZooKeeperCollectionProvider(["host1:2181", "host2:2181", "host3:2181"])

        assert provider.hosts == ["host1:2181", "host2:2181", "host3:2181"]
        mock_kazoo_class.assert_called_once_with(hosts="host1:2181,host2:2181,host3:2181")

    @patch("solr_mcp.solr.collections.KazooClient")
    def test_cleanup(self, mock_kazoo_class):
        """Test cleanup method."""
        mock_zk = MagicMock()
        mock_zk.exists.return_value = True
        mock_kazoo_class.return_value = mock_zk

        provider = ZooKeeperCollectionProvider(["localhost:2181"])
        provider.cleanup()

        mock_zk.stop.assert_called_once()
        mock_zk.close.assert_called_once()
        assert provider.zk is None

    @patch("solr_mcp.solr.collections.KazooClient")
    def test_cleanup_with_error(self, mock_kazoo_class):
        """Test cleanup handles errors gracefully."""
        mock_zk = MagicMock()
        mock_zk.exists.return_value = True
        mock_zk.stop.side_effect = Exception("Stop error")
        mock_kazoo_class.return_value = mock_zk

        provider = ZooKeeperCollectionProvider(["localhost:2181"])
        provider.cleanup()  # Should not raise

        assert provider.zk is None

    @pytest.mark.asyncio
    @patch("solr_mcp.solr.collections.KazooClient")
    @patch("solr_mcp.solr.collections.anyio.to_thread.run_sync")
    async def test_list_collections_success(self, mock_run_sync, mock_kazoo_class):
        """Test successful collection listing."""
        mock_zk = MagicMock()
        mock_zk.exists.return_value = True
        mock_kazoo_class.return_value = mock_zk
        mock_run_sync.return_value = ["collection1", "collection2"]

        provider = ZooKeeperCollectionProvider(["localhost:2181"])
        collections = await provider.list_collections()

        assert collections == ["collection1", "collection2"]
        mock_run_sync.assert_called_once_with(mock_zk.get_children, "/collections")

    @pytest.mark.asyncio
    @patch("solr_mcp.solr.collections.KazooClient")
    @patch("solr_mcp.solr.collections.anyio.to_thread.run_sync")
    async def test_list_collections_no_node(self, mock_run_sync, mock_kazoo_class):
        """Test listing collections when node doesn't exist."""
        mock_zk = MagicMock()
        mock_zk.exists.return_value = True
        mock_kazoo_class.return_value = mock_zk
        mock_run_sync.side_effect = NoNodeError()

        provider = ZooKeeperCollectionProvider(["localhost:2181"])
        collections = await provider.list_collections()

        assert collections == []

    @pytest.mark.asyncio
    @patch("solr_mcp.solr.collections.KazooClient")
    async def test_list_collections_not_connected(self, mock_kazoo_class):
        """Test listing collections when not connected."""
        mock_zk = MagicMock()
        mock_zk.exists.return_value = True
        mock_kazoo_class.return_value = mock_zk

        provider = ZooKeeperCollectionProvider(["localhost:2181"])
        provider.zk = None  # Simulate disconnection

        with pytest.raises(ConnectionError, match="Not connected to ZooKeeper"):
            await provider.list_collections()

    @pytest.mark.asyncio
    @patch("solr_mcp.solr.collections.KazooClient")
    @patch("solr_mcp.solr.collections.anyio.to_thread.run_sync")
    async def test_list_collections_connection_loss(self, mock_run_sync, mock_kazoo_class):
        """Test handling connection loss during listing."""
        mock_zk = MagicMock()
        mock_zk.exists.return_value = True
        mock_kazoo_class.return_value = mock_zk
        mock_run_sync.side_effect = ConnectionLoss("Lost connection")

        provider = ZooKeeperCollectionProvider(["localhost:2181"])

        with pytest.raises(ConnectionError, match="Lost connection to ZooKeeper"):
            await provider.list_collections()

    @pytest.mark.asyncio
    @patch("solr_mcp.solr.collections.KazooClient")
    @patch("solr_mcp.solr.collections.anyio.to_thread.run_sync")
    async def test_list_collections_generic_error(self, mock_run_sync, mock_kazoo_class):
        """Test handling generic errors during listing."""
        mock_zk = MagicMock()
        mock_zk.exists.return_value = True
        mock_kazoo_class.return_value = mock_zk
        mock_run_sync.side_effect = Exception("Generic error")

        provider = ZooKeeperCollectionProvider(["localhost:2181"])

        with pytest.raises(ConnectionError, match="Error listing collections"):
            await provider.list_collections()

    @pytest.mark.asyncio
    @patch("solr_mcp.solr.collections.KazooClient")
    @patch("solr_mcp.solr.collections.anyio.to_thread.run_sync")
    async def test_collection_exists_true(self, mock_run_sync, mock_kazoo_class):
        """Test checking if collection exists (true case)."""
        mock_zk = MagicMock()
        mock_zk.exists.return_value = True
        mock_kazoo_class.return_value = mock_zk
        mock_run_sync.return_value = MagicMock()  # Non-None value means exists

        provider = ZooKeeperCollectionProvider(["localhost:2181"])
        exists = await provider.collection_exists("collection1")

        assert exists is True
        mock_run_sync.assert_called_once_with(mock_zk.exists, "/collections/collection1")

    @pytest.mark.asyncio
    @patch("solr_mcp.solr.collections.KazooClient")
    @patch("solr_mcp.solr.collections.anyio.to_thread.run_sync")
    async def test_collection_exists_false(self, mock_run_sync, mock_kazoo_class):
        """Test checking if collection exists (false case)."""
        mock_zk = MagicMock()
        mock_zk.exists.return_value = True
        mock_kazoo_class.return_value = mock_zk
        mock_run_sync.return_value = None  # None means doesn't exist

        provider = ZooKeeperCollectionProvider(["localhost:2181"])
        exists = await provider.collection_exists("nonexistent")

        assert exists is False

    @pytest.mark.asyncio
    @patch("solr_mcp.solr.collections.KazooClient")
    async def test_collection_exists_not_connected(self, mock_kazoo_class):
        """Test checking collection existence when not connected."""
        mock_zk = MagicMock()
        mock_zk.exists.return_value = True
        mock_kazoo_class.return_value = mock_zk

        provider = ZooKeeperCollectionProvider(["localhost:2181"])
        provider.zk = None  # Simulate disconnection

        with pytest.raises(ConnectionError, match="Not connected to ZooKeeper"):
            await provider.collection_exists("collection1")

    @pytest.mark.asyncio
    @patch("solr_mcp.solr.collections.KazooClient")
    @patch("solr_mcp.solr.collections.anyio.to_thread.run_sync")
    async def test_collection_exists_connection_loss(self, mock_run_sync, mock_kazoo_class):
        """Test handling connection loss when checking existence."""
        mock_zk = MagicMock()
        mock_zk.exists.return_value = True
        mock_kazoo_class.return_value = mock_zk
        mock_run_sync.side_effect = ConnectionLoss("Lost connection")

        provider = ZooKeeperCollectionProvider(["localhost:2181"])

        with pytest.raises(ConnectionError, match="Lost connection to ZooKeeper"):
            await provider.collection_exists("collection1")

    @pytest.mark.asyncio
    @patch("solr_mcp.solr.collections.KazooClient")
    @patch("solr_mcp.solr.collections.anyio.to_thread.run_sync")
    async def test_collection_exists_generic_error(self, mock_run_sync, mock_kazoo_class):
        """Test handling generic errors when checking existence."""
        mock_zk = MagicMock()
        mock_zk.exists.return_value = True
        mock_kazoo_class.return_value = mock_zk
        mock_run_sync.side_effect = Exception("Generic error")

        provider = ZooKeeperCollectionProvider(["localhost:2181"])

        with pytest.raises(ConnectionError, match="Error checking collection existence"):
            await provider.collection_exists("collection1")
