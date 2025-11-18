"""Unit tests for solr/vector/manager.py"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from solr_mcp.solr.exceptions import SchemaError, SolrError
from solr_mcp.solr.vector.manager import VectorManager


class TestVectorManager:
    """Tests for VectorManager"""

    def test_init_default_client(self):
        """Test initialization with default client"""
        mock_solr_client = MagicMock()

        with patch("solr_mcp.solr.vector.manager.OllamaVectorProvider") as MockProvider:
            mock_provider = MagicMock()
            MockProvider.return_value = mock_provider

            manager = VectorManager(mock_solr_client)

            assert manager.solr_client == mock_solr_client
            assert manager.default_top_k == 10
            MockProvider.assert_called_once_with()

    def test_init_custom_client(self):
        """Test initialization with custom client"""
        mock_solr_client = MagicMock()
        mock_vector_client = MagicMock()

        manager = VectorManager(
            mock_solr_client, client=mock_vector_client, default_top_k=20
        )

        assert manager.solr_client == mock_solr_client
        assert manager.client == mock_vector_client
        assert manager.default_top_k == 20

    @pytest.mark.asyncio
    async def test_get_vector_no_client(self):
        """Test get_vector raises error when no client is set"""
        mock_solr_client = MagicMock()
        manager = VectorManager(mock_solr_client)
        manager.client = None

        with pytest.raises(SolrError, match="Vector operations unavailable"):
            await manager.get_vector("test text")

    @pytest.mark.asyncio
    async def test_get_vector_default_client(self):
        """Test get_vector with default client"""
        mock_solr_client = MagicMock()
        mock_vector_client = MagicMock()
        mock_vector_client.get_vector = AsyncMock(return_value=[0.1, 0.2, 0.3])

        manager = VectorManager(mock_solr_client, client=mock_vector_client)

        result = await manager.get_vector("test text")

        assert result == [0.1, 0.2, 0.3]
        mock_vector_client.get_vector.assert_called_once_with("test text", None)

    @pytest.mark.asyncio
    async def test_get_vector_with_custom_config(self):
        """Test get_vector with custom model and base_url"""
        mock_solr_client = MagicMock()
        mock_vector_client = MagicMock()
        mock_vector_client.model = "default-model"
        mock_vector_client.base_url = "http://default:11434"
        mock_vector_client.timeout = 30
        mock_vector_client.retries = 3

        manager = VectorManager(mock_solr_client, client=mock_vector_client)

        # Patch at the source module where it's imported from
        with patch("solr_mcp.vector_provider.OllamaVectorProvider") as MockProvider:
            temp_client = MagicMock()
            temp_client.get_vector = AsyncMock(return_value=[0.4, 0.5, 0.6])
            MockProvider.return_value = temp_client

            result = await manager.get_vector(
                "test text",
                vector_provider_config={
                    "model": "custom-model",
                    "base_url": "http://custom:11434",
                },
            )

            assert result == [0.4, 0.5, 0.6]
            MockProvider.assert_called_once_with(
                model="custom-model",
                base_url="http://custom:11434",
                timeout=30,
                retries=3,
            )
            temp_client.get_vector.assert_called_once_with("test text")

    @pytest.mark.asyncio
    async def test_get_vector_with_model_only(self):
        """Test get_vector with just model override creates temp client"""
        mock_solr_client = MagicMock()
        mock_vector_client = MagicMock()
        mock_vector_client.model = "default-model"
        mock_vector_client.base_url = "http://default:11434"
        mock_vector_client.timeout = 30
        mock_vector_client.retries = 3

        manager = VectorManager(mock_solr_client, client=mock_vector_client)

        with patch("solr_mcp.vector_provider.OllamaVectorProvider") as MockProvider:
            temp_client = AsyncMock()
            temp_client.get_vector = AsyncMock(return_value=[0.7, 0.8, 0.9])
            MockProvider.return_value = temp_client

            result = await manager.get_vector(
                "test text", vector_provider_config={"model": "custom-model"}
            )

            assert result == [0.7, 0.8, 0.9]
            # Should create temp client with custom model but default other settings
            MockProvider.assert_called_once_with(
                model="custom-model",
                base_url="http://default:11434",
                timeout=30,
                retries=3,
            )

    @pytest.mark.asyncio
    async def test_get_vector_error(self):
        """Test get_vector handles errors"""
        mock_solr_client = MagicMock()
        mock_vector_client = MagicMock()
        mock_vector_client.get_vector = AsyncMock(
            side_effect=Exception("Connection failed")
        )

        manager = VectorManager(mock_solr_client, client=mock_vector_client)

        with pytest.raises(SolrError, match="Error getting vector"):
            await manager.get_vector("test text")

    def test_format_knn_query_with_top_k(self):
        """Test formatting KNN query with top_k"""
        mock_solr_client = MagicMock()
        manager = VectorManager(mock_solr_client)

        vector = [0.1, 0.2, 0.3]
        result = manager.format_knn_query(vector, "vector_field", top_k=5)

        assert result == "{!knn f=vector_field topK=5}[0.1,0.2,0.3]"

    def test_format_knn_query_without_top_k(self):
        """Test formatting KNN query without top_k"""
        mock_solr_client = MagicMock()
        manager = VectorManager(mock_solr_client)

        vector = [0.4, 0.5]
        result = manager.format_knn_query(vector, "my_vector")

        assert result == "{!knn f=my_vector}[0.4,0.5]"

    @pytest.mark.asyncio
    async def test_find_vector_field_success(self):
        """Test finding vector field successfully"""
        mock_solr_client = MagicMock()
        mock_solr_client.field_manager = MagicMock()
        mock_solr_client.field_manager.find_vector_field = AsyncMock(
            return_value="vector_field"
        )

        manager = VectorManager(mock_solr_client)

        result = await manager.find_vector_field("test_collection")

        assert result == "vector_field"
        mock_solr_client.field_manager.find_vector_field.assert_called_once_with(
            "test_collection"
        )

    @pytest.mark.asyncio
    async def test_find_vector_field_error(self):
        """Test find_vector_field handles errors"""
        mock_solr_client = MagicMock()
        mock_solr_client.field_manager = MagicMock()
        mock_solr_client.field_manager.find_vector_field = AsyncMock(
            side_effect=Exception("Field not found")
        )

        manager = VectorManager(mock_solr_client)

        with pytest.raises(SolrError, match="Failed to find vector field"):
            await manager.find_vector_field("test_collection")

    @pytest.mark.asyncio
    async def test_validate_vector_field_with_field(self):
        """Test validating vector field when field is provided"""
        mock_solr_client = MagicMock()
        mock_solr_client.field_manager = MagicMock()
        field_info = {"type": "knn_vector", "dimension": 384}
        mock_solr_client.field_manager.validate_vector_field_dimension = AsyncMock(
            return_value=field_info
        )

        manager = VectorManager(mock_solr_client)

        result_field, result_info = await manager.validate_vector_field(
            "test_collection", "vector_field", "all-minilm"
        )

        assert result_field == "vector_field"
        assert result_info == field_info

    @pytest.mark.asyncio
    async def test_validate_vector_field_auto_detect(self):
        """Test validating vector field with auto-detection"""
        mock_solr_client = MagicMock()
        mock_solr_client.field_manager = MagicMock()
        mock_solr_client.field_manager.find_vector_field = AsyncMock(
            return_value="auto_field"
        )
        field_info = {"type": "knn_vector", "dimension": 384}
        mock_solr_client.field_manager.validate_vector_field_dimension = AsyncMock(
            return_value=field_info
        )

        manager = VectorManager(mock_solr_client)

        result_field, result_info = await manager.validate_vector_field(
            "test_collection", None
        )

        assert result_field == "auto_field"
        assert result_info == field_info
        mock_solr_client.field_manager.find_vector_field.assert_called_once_with(
            "test_collection"
        )

    @pytest.mark.asyncio
    async def test_validate_vector_field_schema_error(self):
        """Test validate_vector_field handles SchemaError"""
        mock_solr_client = MagicMock()
        mock_solr_client.field_manager = MagicMock()
        mock_solr_client.field_manager.validate_vector_field_dimension = AsyncMock(
            side_effect=SchemaError("Invalid schema")
        )

        manager = VectorManager(mock_solr_client)

        with pytest.raises(SolrError, match="Invalid schema"):
            await manager.validate_vector_field("test_collection", "vector_field")

    @pytest.mark.asyncio
    async def test_validate_vector_field_generic_error(self):
        """Test validate_vector_field handles generic errors"""
        mock_solr_client = MagicMock()
        mock_solr_client.field_manager = MagicMock()
        mock_solr_client.field_manager.validate_vector_field_dimension = AsyncMock(
            side_effect=Exception("Connection error")
        )

        manager = VectorManager(mock_solr_client)

        with pytest.raises(SolrError, match="Failed to validate vector field"):
            await manager.validate_vector_field("test_collection", "vector_field")

    @pytest.mark.asyncio
    async def test_execute_vector_search_success(self):
        """Test successful vector search execution"""
        mock_solr_client = MagicMock()
        manager = VectorManager(mock_solr_client)

        mock_pysolr_client = MagicMock()
        mock_results = MagicMock()
        mock_results.hits = 5
        mock_results.qtime = 10
        mock_results.__iter__ = lambda self: iter([{"id": "1"}, {"id": "2"}])
        mock_pysolr_client.search.return_value = mock_results

        vector = [0.1, 0.2, 0.3]
        result = await manager.execute_vector_search(
            mock_pysolr_client, vector, "vector_field", top_k=10
        )

        assert result["response"]["numFound"] == 5
        assert len(result["response"]["docs"]) == 2
        mock_pysolr_client.search.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_vector_search_with_filter(self):
        """Test vector search with filter query"""
        mock_solr_client = MagicMock()
        manager = VectorManager(mock_solr_client)

        mock_pysolr_client = MagicMock()
        mock_pysolr_client.search.return_value = {
            "response": {"numFound": 0, "docs": []}
        }

        vector = [0.1, 0.2, 0.3]
        await manager.execute_vector_search(
            mock_pysolr_client, vector, "vector_field", filter_query="category:books"
        )

        call_args = mock_pysolr_client.search.call_args
        assert call_args[1]["fq"] == "category:books"

    @pytest.mark.asyncio
    async def test_execute_vector_search_error(self):
        """Test execute_vector_search handles errors"""
        mock_solr_client = MagicMock()
        manager = VectorManager(mock_solr_client)

        mock_pysolr_client = MagicMock()
        mock_pysolr_client.search.side_effect = Exception("Search failed")

        vector = [0.1, 0.2, 0.3]

        with pytest.raises(SolrError, match="Vector search failed"):
            await manager.execute_vector_search(
                mock_pysolr_client, vector, "vector_field"
            )

    def test_extract_doc_ids(self):
        """Test extracting document IDs from results"""
        mock_solr_client = MagicMock()
        manager = VectorManager(mock_solr_client)

        results = {
            "response": {
                "numFound": 3,
                "docs": [{"id": "doc1"}, {"id": "doc2"}, {"id": "doc3"}],
            }
        }

        doc_ids = manager.extract_doc_ids(results)

        assert doc_ids == ["doc1", "doc2", "doc3"]

    def test_extract_doc_ids_empty(self):
        """Test extracting doc IDs from empty results"""
        mock_solr_client = MagicMock()
        manager = VectorManager(mock_solr_client)

        results = {"response": {"numFound": 0, "docs": []}}

        doc_ids = manager.extract_doc_ids(results)

        assert doc_ids == []

    def test_extract_doc_ids_missing_id(self):
        """Test extracting doc IDs when some docs don't have id"""
        mock_solr_client = MagicMock()
        manager = VectorManager(mock_solr_client)

        results = {
            "response": {"docs": [{"id": "doc1"}, {"name": "no_id"}, {"id": "doc2"}]}
        }

        doc_ids = manager.extract_doc_ids(results)

        assert doc_ids == ["doc1", "doc2"]
