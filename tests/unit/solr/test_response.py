"""Tests for solr_mcp.solr.response module."""

import json
from unittest.mock import MagicMock, patch

import pysolr
import pytest

from solr_mcp.solr.response import ResponseFormatter


class TestResponseFormatter:
    """Tests for ResponseFormatter class."""

    def test_format_search_results_basic(self):
        """Test formatting basic search results."""
        # Create mock results
        mock_results = MagicMock(spec=pysolr.Results)
        mock_results.hits = 10
        mock_results.docs = [{"id": "1", "title": "Test"}]

        result = ResponseFormatter.format_search_results(mock_results, start=0)

        # The result should be a JSON string
        assert isinstance(result, str)
        parsed = json.loads(result)
        assert parsed["result-set"]["numFound"] == 10
        assert parsed["result-set"]["start"] == 0
        assert len(parsed["result-set"]["docs"]) == 1

    def test_format_search_results_with_custom_start(self):
        """Test formatting search results with custom start offset."""
        mock_results = MagicMock(spec=pysolr.Results)
        mock_results.hits = 100
        mock_results.docs = [{"id": "21", "title": "Test"}]

        result = ResponseFormatter.format_search_results(mock_results, start=20)

        parsed = json.loads(result)
        assert parsed["result-set"]["start"] == 20

    def test_format_sql_response_basic(self):
        """Test formatting basic SQL response."""
        raw_response = {
            "result-set": {
                "docs": [{"id": "1", "name": "Alice"}, {"id": "2", "name": "Bob"}]
            }
        }

        result = ResponseFormatter.format_sql_response(raw_response)

        assert result["result-set"]["numFound"] == 2
        assert result["result-set"]["start"] == 0
        assert len(result["result-set"]["docs"]) == 2

    def test_format_sql_response_empty(self):
        """Test formatting empty SQL response."""
        raw_response = {"result-set": {"docs": []}}

        result = ResponseFormatter.format_sql_response(raw_response)

        assert result["result-set"]["numFound"] == 0
        assert result["result-set"]["docs"] == []

    def test_format_vector_search_results_basic(self):
        """Test formatting basic vector search results."""
        raw_results = {
            "responseHeader": {"QTime": 10},
            "response": {
                "numFound": 2,
                "docs": [
                    {
                        "_docid_": "1",
                        "score": 0.95,
                        "_vector_distance_": 0.05,
                        "title": "Test 1",
                    },
                    {
                        "_docid_": "2",
                        "score": 0.85,
                        "_vector_distance_": 0.15,
                        "title": "Test 2",
                    },
                ],
            },
        }

        result = ResponseFormatter.format_vector_search_results(raw_results, top_k=10)

        assert "results" in result
        assert "metadata" in result
        assert len(result["results"]) == 2
        assert result["metadata"]["total_found"] == 2
        assert result["metadata"]["top_k"] == 10
        assert result["metadata"]["query_time_ms"] == 10

    def test_format_vector_search_results_empty(self):
        """Test formatting empty vector search results."""
        raw_results = {
            "responseHeader": {"QTime": 5},
            "response": {"numFound": 0, "docs": []},
        }

        result = ResponseFormatter.format_vector_search_results(raw_results, top_k=10)

        assert len(result["results"]) == 0
        assert result["metadata"]["total_found"] == 0

    def test_format_vector_search_results_with_top_k(self):
        """Test formatting vector search results with custom top_k."""
        raw_results = {
            "responseHeader": {"QTime": 15},
            "response": {
                "numFound": 5,
                "docs": [{"_docid_": str(i), "score": 1.0 - i * 0.1} for i in range(5)],
            },
        }

        result = ResponseFormatter.format_vector_search_results(raw_results, top_k=5)

        assert result["metadata"]["top_k"] == 5
        assert len(result["results"]) == 5

    def test_format_vector_search_results_alternate_docid_fields(self):
        """Test formatting vector search results with alternate docid field names."""
        raw_results = {
            "responseHeader": {},
            "response": {
                "numFound": 2,
                "docs": [
                    {"[docid]": "doc1", "score": 0.9},  # Alternate field [docid]
                    {"docid": "doc2", "score": 0.8},  # Alternate field docid
                ],
            },
        }

        result = ResponseFormatter.format_vector_search_results(raw_results, top_k=10)

        assert result["results"][0]["docid"] == "doc1"
        assert result["results"][1]["docid"] == "doc2"

    def test_format_vector_search_results_missing_docid(self):
        """Test formatting vector search results with missing docid (defaults to '0')."""
        raw_results = {
            "responseHeader": {},
            "response": {"numFound": 1, "docs": [{"score": 0.9, "title": "No docid"}]},
        }

        result = ResponseFormatter.format_vector_search_results(raw_results, top_k=10)

        # Should default to "0" when no docid field is found
        assert result["results"][0]["docid"] == "0"

    def test_format_vector_search_results_with_metadata(self):
        """Test that vector search results include metadata fields."""
        raw_results = {
            "responseHeader": {"QTime": 20},
            "response": {
                "numFound": 1,
                "docs": [
                    {
                        "_docid_": "1",
                        "score": 0.95,
                        "_vector_distance_": 0.05,
                        "title": "Test",
                        "author": "Alice",
                        "year": 2023,
                    }
                ],
            },
        }

        result = ResponseFormatter.format_vector_search_results(raw_results, top_k=10)

        # Metadata should include fields not in the special list
        metadata = result["results"][0]["metadata"]
        assert "title" in metadata
        assert "author" in metadata
        assert "year" in metadata
        assert "_docid_" not in metadata
        assert "score" not in metadata
        assert "_vector_distance_" not in metadata
