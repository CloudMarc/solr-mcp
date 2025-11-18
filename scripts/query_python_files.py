#!/usr/bin/env python3
"""
Query the codebase collection for Python files using the Solr client.
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from solr_mcp.solr.client import SolrClient
from solr_mcp.solr.config import SolrConfig


async def count_python_files():
    """Count Python files in the codebase collection."""
    config = SolrConfig(
        solr_base_url="http://localhost:8983/solr",
        zookeeper_hosts=["localhost:2181"]
    )
    client = SolrClient(config)

    # Query for Python files using facets
    print("\n=== Counting Python files in codebase collection ===\n")

    # Use direct HTTP query to get facet counts
    import httpx
    async with httpx.AsyncClient() as http_client:
        # Query for files with .py extension tag
        response = await http_client.get(
            "http://localhost:8983/solr/codebase/select",
            params={
                "q": "tags_ss:py",
                "rows": "0",
                "wt": "json",
            }
        )
        result = response.json()
        py_count = result['response']['numFound']
        print(f"Python files (with .py extension): {py_count}")

        # Also query by category
        response2 = await http_client.get(
            "http://localhost:8983/solr/codebase/select",
            params={
                "q": "category_ss:python",
                "rows": "0",
                "wt": "json",
            }
        )
        result2 = response2.json()
        py_category_count = result2['response']['numFound']
        print(f"Python files (by category): {py_category_count}")

        # Get some sample Python files
        response3 = await http_client.get(
            "http://localhost:8983/solr/codebase/select",
            params={
                "q": "tags_ss:py",
                "rows": "5",
                "fl": "id,title,source,category_ss",
                "wt": "json",
            }
        )
        result3 = response3.json()
        print(f"\nSample Python files:")
        for doc in result3['response']['docs']:
            print(f"  - {doc['source']}")


async def main():
    await count_python_files()


if __name__ == "__main__":
    asyncio.run(main())
