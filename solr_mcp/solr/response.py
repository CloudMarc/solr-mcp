"""Response formatters for Solr results."""

import logging
from typing import Any

import pysolr
from loguru import logger

from solr_mcp.solr.utils.formatting import format_search_results, format_sql_response


logger = logging.getLogger(__name__)


class ResponseFormatter:
    """Formats Solr responses for client consumption."""

    @staticmethod
    def format_search_results(
        results: pysolr.Results, start: int = 0
    ) -> dict[str, Any]:
        """Format Solr search results for client consumption.

        Args:
            results: Solr search results
            start: Starting index of results

        Returns:
            Formatted search results
        """
        return format_search_results(results, start)

    @staticmethod
    def format_sql_response(response: dict[str, Any]) -> dict[str, Any]:
        """Format Solr SQL response for client consumption.

        Args:
            response: Solr SQL response

        Returns:
            Formatted SQL response
        """
        return format_sql_response(response)

    @staticmethod
    def format_vector_search_results(
        results: dict[str, Any], top_k: int
    ) -> dict[str, Any]:
        """Format vector search results.

        Args:
            results: Vector search results
            top_k: Number of top results

        Returns:
            Formatted vector search results
        """
        from solr_mcp.solr.vector import VectorSearchResults

        vector_results = VectorSearchResults.from_solr_response(
            response=results, top_k=top_k
        )
        return vector_results.to_dict()
