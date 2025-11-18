"""Integration tests for Query Features.

Tests highlighting, stats component, terms component, and other query features.
"""

import logging
import os
import sys

import pytest
import pytest_asyncio


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from solr_mcp.solr.client import SolrClient
from solr_mcp.solr.config import SolrConfig


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

TEST_COLLECTION = os.getenv("TEST_COLLECTION", "unified")
SOLR_BASE_URL = os.getenv("SOLR_BASE_URL", "http://localhost:8983/solr")


@pytest_asyncio.fixture
async def solr_client():
    """Create SolrClient for testing."""
    config = SolrConfig(
        solr_base_url=SOLR_BASE_URL,
        zookeeper_hosts=["localhost:2181"],
        default_collection=TEST_COLLECTION,
    )
    client = SolrClient(config=config)
    try:
        yield client
    finally:
        if hasattr(client, "close"):
            await client.close()


@pytest.mark.asyncio
async def test_query_with_highlighting(solr_client):
    """Test query with highlighting enabled."""
    result = await solr_client.execute_query(
        collection=TEST_COLLECTION,
        q="bitcoin",
        highlight_fields=["text", "title"],
        highlight_snippets=2,
        highlight_fragsize=100,
        rows=5,
    )

    logger.info(f"Query with highlighting result: {result}")

    assert "response" in result, "Should have response"
    assert "highlighting" in result, "Should have highlighting"

    # Check highlighting structure
    highlighting = result["highlighting"]
    assert isinstance(highlighting, dict), "Highlighting should be a dict"

    # If we have results, check that highlighting exists for at least one
    if result["response"]["numFound"] > 0:
        docs = result["response"]["docs"]
        for doc in docs:
            doc_id = doc["id"]
            if doc_id in highlighting:
                logger.info(f"Highlighting for {doc_id}: {highlighting[doc_id]}")
                # Highlighting should have at least one field
                assert len(highlighting[doc_id]) > 0, "Should have highlighting data"
                break


@pytest.mark.asyncio
async def test_query_with_stats(solr_client):
    """Test query with stats component."""
    # First add some documents with numeric fields for stats
    # The existing bitcoin docs should have some fields we can use

    result = await solr_client.execute_query(
        collection=TEST_COLLECTION,
        q="*:*",
        stats_fields=["section_number"],  # Bitcoin docs have section numbers
        rows=0,  # We don't need docs, just stats
    )

    logger.info(f"Query with stats result: {result}")

    assert "stats" in result, "Should have stats"
    assert "stats_fields" in result["stats"], "Should have stats_fields"

    # Check stats structure
    stats_fields = result["stats"]["stats_fields"]
    if "section_number" in stats_fields:
        section_stats = stats_fields["section_number"]
        logger.info(f"Section number stats: {section_stats}")

        # Stats should include min, max, count, etc.
        assert "min" in section_stats, "Should have min value"
        assert "max" in section_stats, "Should have max value"
        assert "count" in section_stats, "Should have count"


@pytest.mark.asyncio
async def test_query_with_highlighting_and_stats(solr_client):
    """Test query combining highlighting and stats."""
    result = await solr_client.execute_query(
        collection=TEST_COLLECTION,
        q="blockchain",
        highlight_fields=["text"],
        stats_fields=["section_number"],
        rows=3,
    )

    logger.info(f"Combined query result keys: {result.keys()}")

    assert "response" in result, "Should have response"
    assert "highlighting" in result, "Should have highlighting"
    assert "stats" in result, "Should have stats"

    # Verify we can use both features together
    assert result["response"]["numFound"] >= 0, "Should have valid numFound"


@pytest.mark.asyncio
async def test_terms_component_prefix(solr_client):
    """Test terms component with prefix filtering."""
    result = await solr_client.get_terms(
        collection=TEST_COLLECTION,
        field="text",
        prefix="bit",  # Should match "bitcoin", "bit", etc.
        limit=10,
    )

    logger.info(f"Terms with prefix result: {result}")

    assert "terms" in result, "Should have terms"
    assert "text" in result["terms"], "Should have terms for 'text' field"

    # Terms should be a list of [term, count, term, count, ...]
    terms_list = result["terms"]["text"]
    assert isinstance(terms_list, list), "Terms should be a list"

    # Check that terms start with prefix
    if len(terms_list) > 0:
        # Terms are in pairs: [term1, count1, term2, count2, ...]
        for i in range(0, len(terms_list), 2):
            term = terms_list[i]
            logger.info(f"Term: {term}")
            assert term.startswith("bit"), f"Term '{term}' should start with 'bit'"


@pytest.mark.asyncio
async def test_terms_component_no_prefix(solr_client):
    """Test terms component without prefix (top terms)."""
    result = await solr_client.get_terms(
        collection=TEST_COLLECTION, field="text", limit=20
    )

    logger.info(f"Terms without prefix result: {result}")

    assert "terms" in result, "Should have terms"
    assert "text" in result["terms"], "Should have terms for 'text' field"

    terms_list = result["terms"]["text"]
    # Should get top 20 terms by frequency
    assert len(terms_list) <= 40, "Should have at most 20 terms (40 with counts)"


@pytest.mark.asyncio
async def test_terms_component_regex(solr_client):
    """Test terms component with regex filtering."""
    result = await solr_client.get_terms(
        collection=TEST_COLLECTION,
        field="text",
        regex=".*coin.*",  # Should match terms containing "coin"
        limit=10,
    )

    logger.info(f"Terms with regex result: {result}")

    assert "terms" in result, "Should have terms"
    assert "text" in result["terms"], "Should have terms for 'text' field"

    terms_list = result["terms"]["text"]
    # Check that terms match regex
    if len(terms_list) > 0:
        for i in range(0, len(terms_list), 2):
            term = terms_list[i]
            logger.info(f"Regex matched term: {term}")
            assert "coin" in term.lower(), f"Term '{term}' should contain 'coin'"


@pytest.mark.asyncio
async def test_terms_component_min_count(solr_client):
    """Test terms component with minimum count filter."""
    result = await solr_client.get_terms(
        collection=TEST_COLLECTION,
        field="text",
        min_count=2,  # Only terms appearing at least twice
        limit=10,
    )

    logger.info(f"Terms with min_count result: {result}")

    assert "terms" in result, "Should have terms"
    assert "text" in result["terms"], "Should have terms for 'text' field"

    terms_list = result["terms"]["text"]
    # Check that all terms have count >= 2
    if len(terms_list) > 0:
        for i in range(1, len(terms_list), 2):
            count = terms_list[i]
            logger.info(f"Term count: {count}")
            assert count >= 2, f"Count {count} should be >= 2"


@pytest.mark.asyncio
async def test_standard_query_filters(solr_client):
    """Test standard Solr query with filters."""
    result = await solr_client.execute_query(
        collection=TEST_COLLECTION,
        q="bitcoin",
        fq=["section_number:[0 TO 5]"],  # Filter to first 5 sections
        rows=10,
    )

    logger.info(f"Query with filter result: {result}")

    assert "response" in result, "Should have response"
    docs = result["response"]["docs"]

    # Verify filter was applied
    for doc in docs:
        if "section_number" in doc:
            section = doc["section_number"]
            assert 0 <= section <= 5, f"Section {section} should be in range [0, 5]"


@pytest.mark.asyncio
async def test_query_field_list(solr_client):
    """Test query with specific field list."""
    result = await solr_client.execute_query(
        collection=TEST_COLLECTION, q="*:*", fl="id,title", rows=5
    )

    logger.info(f"Query with field list result: {result}")

    assert "response" in result, "Should have response"
    docs = result["response"]["docs"]

    if len(docs) > 0:
        # Check that only requested fields are returned (plus score)
        doc = docs[0]
        logger.info(f"Document fields: {doc.keys()}")
        # Should have id and title, maybe score
        assert "id" in doc, "Should have id field"
        # title might not be in all docs, but should be in schema


@pytest.mark.asyncio
async def test_query_sorting(solr_client):
    """Test query with sorting."""
    result = await solr_client.execute_query(
        collection=TEST_COLLECTION,
        q="*:*",
        sort="section_number asc",
        fl="id,section_number",
        rows=5,
    )

    logger.info(f"Query with sorting result: {result}")

    assert "response" in result, "Should have response"
    docs = result["response"]["docs"]

    # Verify sorting
    if len(docs) > 1:
        prev_section = -1
        for doc in docs:
            if "section_number" in doc:
                current_section = doc["section_number"]
                assert current_section >= prev_section, (
                    "Documents should be sorted ascending by section_number"
                )
                prev_section = current_section


@pytest.mark.asyncio
async def test_query_pagination(solr_client):
    """Test query pagination with start and rows."""
    # First query
    result1 = await solr_client.execute_query(
        collection=TEST_COLLECTION, q="*:*", start=0, rows=3, fl="id"
    )

    # Second query (next page)
    result2 = await solr_client.execute_query(
        collection=TEST_COLLECTION, q="*:*", start=3, rows=3, fl="id"
    )

    logger.info(f"First page: {result1}")
    logger.info(f"Second page: {result2}")

    docs1 = result1["response"]["docs"]
    docs2 = result2["response"]["docs"]

    # Pages should have different documents
    ids1 = {doc["id"] for doc in docs1}
    ids2 = {doc["id"] for doc in docs2}

    assert len(ids1.intersection(ids2)) == 0, "Pages should not overlap"


@pytest.mark.asyncio
async def test_facet_query(solr_client):
    """Test faceting on a field."""
    result = await solr_client.execute_query(
        collection=TEST_COLLECTION,
        q="*:*",
        facet=True,
        facet_field=["section_number"],
        rows=0,
    )

    logger.info(f"Facet query result: {result}")

    assert "facet_counts" in result, "Should have facet_counts"
    assert "facet_fields" in result["facet_counts"], "Should have facet_fields"

    facet_fields = result["facet_counts"]["facet_fields"]
    if "section_number" in facet_fields:
        section_facets = facet_fields["section_number"]
        logger.info(f"Section facets: {section_facets}")
        # Facets are in pairs: [value1, count1, value2, count2, ...]
        assert isinstance(section_facets, list), "Facets should be a list"
