#!/usr/bin/env python3
"""Comprehensive manual integration test for all solr-mcp features.

This script tests all the features in the PR to ensure everything works end-to-end.
"""

import asyncio
import logging
import sys
from pathlib import Path


# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from solr_mcp.solr.client import SolrClient
from solr_mcp.solr.config import SolrConfig


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class Colors:
    """ANSI color codes for terminal output."""

    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BLUE = "\033[94m"
    END = "\033[0m"
    BOLD = "\033[1m"


def print_test(name: str):
    """Print test name."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 70}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}TEST: {name}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 70}{Colors.END}")


def print_success(message: str):
    """Print success message."""
    print(f"{Colors.GREEN}✓ {message}{Colors.END}")


def print_error(message: str):
    """Print error message."""
    print(f"{Colors.RED}✗ {message}{Colors.END}")


def print_info(message: str):
    """Print info message."""
    print(f"{Colors.YELLOW}ℹ {message}{Colors.END}")


async def test_list_collections(client: SolrClient):
    """Test listing collections."""
    print_test("List Collections")
    try:
        collections = await client.list_collections()
        print_info(f"Found {len(collections)} collections: {collections}")
        print_success("List collections works!")
        return True
    except Exception as e:
        print_error(f"Failed: {e}")
        return False


async def test_list_fields(client: SolrClient, collection: str):
    """Test listing fields."""
    print_test(f"List Fields ({collection})")
    try:
        result = await client.list_fields(collection)
        fields = result.get("fields", [])
        print_info(f"Found {len(fields)} fields")
        for field in fields[:5]:  # Show first 5
            print_info(f"  - {field.get('name')}: {field.get('type')}")
        print_success("List fields works!")
        return True
    except Exception as e:
        print_error(f"Failed: {e}")
        return False


async def test_schema_operations(client: SolrClient, collection: str):
    """Test schema management operations."""
    print_test("Schema Management Operations")
    test_field = "test_comprehensive_field"
    success = True

    try:
        # Cleanup first
        try:
            await client.delete_schema_field(collection, test_field)
            print_info("Cleaned up existing test field")
        except Exception:
            pass

        # Test 1: Add field
        print_info("Adding test field...")
        add_result = await client.add_schema_field(
            collection=collection,
            field_name=test_field,
            field_type="text_general",
            stored=True,
            indexed=True,
        )
        if add_result.get("responseHeader", {}).get("status") == 0:
            print_success("✓ Added field successfully")
        else:
            print_error("✗ Failed to add field")
            success = False

        # Test 2: Get field
        print_info("Getting field details...")
        get_result = await client.get_schema_field(collection, test_field)
        if get_result.get("field", {}).get("name") == test_field:
            print_success("✓ Retrieved field successfully")
        else:
            print_error("✗ Failed to retrieve field")
            success = False

        # Test 3: List fields (should include our field)
        print_info("Listing all fields...")
        list_result = await client.get_schema_fields(collection)
        field_names = [f.get("name") for f in list_result.get("fields", [])]
        if test_field in field_names:
            print_success("✓ Field appears in schema list")
        else:
            print_error("✗ Field not in schema list")
            success = False

        # Test 4: Delete field
        print_info("Deleting test field...")
        delete_result = await client.delete_schema_field(collection, test_field)
        if delete_result.get("responseHeader", {}).get("status") == 0:
            print_success("✓ Deleted field successfully")
        else:
            print_error("✗ Failed to delete field")
            success = False

        return success

    except Exception as e:
        print_error(f"Schema operations failed: {e}")
        return False


async def test_indexing_operations(client: SolrClient, collection: str):
    """Test indexing operations."""
    print_test("Indexing Operations")
    test_doc_id = "test_comprehensive_doc"
    success = True

    try:
        # Cleanup
        try:
            await client.delete_documents(collection, ids=[test_doc_id])
            await client.commit(collection)
        except Exception:
            pass

        # Test 1: Add document
        print_info("Adding document...")
        doc = {
            "id": test_doc_id,
            "title": "Test Document",
            "text": "This is a comprehensive test document",
            "score": 100,
        }
        add_result = await client.add_documents(collection, [doc])
        if add_result.get("responseHeader", {}).get("status") == 0:
            print_success("✓ Added document successfully")
        else:
            print_error("✗ Failed to add document")
            success = False

        # Test 2: Real-time get (uncommitted)
        print_info("Testing real-time get (uncommitted)...")
        rtg_result = await client.realtime_get(collection, ids=[test_doc_id])
        if "doc" in rtg_result or (
            "response" in rtg_result and rtg_result["response"]["docs"]
        ):
            print_success("✓ Real-time get works (uncommitted)")
        else:
            print_error("✗ Real-time get failed")
            success = False

        # Test 3: Soft commit
        print_info("Performing soft commit...")
        soft_commit_result = await client.commit(collection, soft_commit=True)
        if soft_commit_result.get("responseHeader", {}).get("status") == 0:
            print_success("✓ Soft commit successful")
        else:
            print_error("✗ Soft commit failed")
            success = False

        # Wait a moment for visibility
        await asyncio.sleep(0.5)

        # Test 4: Search for document
        print_info("Searching for document...")
        query = f"SELECT * FROM {collection} WHERE id = '{test_doc_id}'"
        search_result = await client.execute_select_query(query)
        docs = search_result.get("result-set", {}).get("docs", [])
        if len(docs) > 0 and docs[0]["id"] == test_doc_id:
            print_success("✓ Document is searchable after soft commit")
        else:
            print_error("✗ Document not searchable")
            success = False

        # Test 5: Atomic update
        print_info("Testing atomic update...")
        atomic_result = await client.atomic_update(
            collection, test_doc_id, {"title": {"set": "Updated Title"}}
        )
        if atomic_result.get("responseHeader", {}).get("status") == 0:
            print_success("✓ Atomic update successful")
        else:
            print_error("✗ Atomic update failed")
            success = False

        # Test 6: Hard commit
        print_info("Performing hard commit...")
        hard_commit_result = await client.commit(collection, soft_commit=False)
        if hard_commit_result.get("responseHeader", {}).get("status") == 0:
            print_success("✓ Hard commit successful")
        else:
            print_error("✗ Hard commit failed")
            success = False

        # Test 7: Verify update
        await asyncio.sleep(0.5)
        search_result = await client.execute_select_query(query)
        docs = search_result.get("result-set", {}).get("docs", [])
        if len(docs) > 0 and docs[0].get("title") == "Updated Title":
            print_success("✓ Atomic update verified")
        else:
            print_error("✗ Atomic update not reflected")
            success = False

        # Test 8: Delete document
        print_info("Deleting document...")
        delete_result = await client.delete_documents(collection, ids=[test_doc_id])
        await client.commit(collection)
        if delete_result.get("responseHeader", {}).get("status") == 0:
            print_success("✓ Document deleted successfully")
        else:
            print_error("✗ Failed to delete document")
            success = False

        return success

    except Exception as e:
        print_error(f"Indexing operations failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_query_features(client: SolrClient, collection: str):
    """Test query features."""
    print_test("Query Features")
    success = True

    try:
        # Test 1: Basic query
        print_info("Testing basic query...")
        result = await client.query(collection, q="bitcoin", rows=3)
        if result.get("response", {}).get("numFound", 0) >= 0:
            print_success(
                f"✓ Basic query works ({result['response']['numFound']} results)"
            )
        else:
            print_error("✗ Basic query failed")
            success = False

        # Test 2: Query with highlighting
        print_info("Testing query with highlighting...")
        result = await client.query(
            collection,
            q="bitcoin",
            highlight=True,
            hl_fl="text,title",
            hl_snippets=2,
            rows=3,
        )
        if "highlighting" in result:
            print_success("✓ Highlighting works")
            # Show sample
            for doc_id, hl_data in list(result["highlighting"].items())[:1]:
                print_info(f"  Sample highlight for {doc_id}: {list(hl_data.keys())}")
        else:
            print_error("✗ Highlighting not returned")
            success = False

        # Test 3: Query with stats
        print_info("Testing query with stats...")
        result = await client.query(
            collection,
            q="*:*",
            stats=True,
            stats_field=["section_number"],
            rows=0,
        )
        if "stats" in result and "stats_fields" in result["stats"]:
            print_success("✓ Stats component works")
            if "section_number" in result["stats"]["stats_fields"]:
                stats = result["stats"]["stats_fields"]["section_number"]
                print_info(
                    f"  Section stats: min={stats.get('min')}, max={stats.get('max')}, count={stats.get('count')}"
                )
        else:
            print_error("✗ Stats component not returned")
            success = False

        # Test 4: Terms component
        print_info("Testing terms component...")
        result = await client.terms(collection, field="text", prefix="bit", limit=5)
        if "terms" in result and "text" in result["terms"]:
            print_success("✓ Terms component works")
            terms_list = result["terms"]["text"]
            print_info(f"  Found {len(terms_list) // 2} terms starting with 'bit'")
        else:
            print_error("✗ Terms component not returned")
            success = False

        return success

    except Exception as e:
        print_error(f"Query features failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_vector_search(client: SolrClient, collection: str):
    """Test vector search capabilities."""
    print_test("Vector Search")
    success = True

    try:
        # Test semantic search (text -> vector -> search)
        print_info("Testing semantic search...")
        result = await client.execute_semantic_select_query(
            query=f"SELECT * FROM {collection} LIMIT 5",
            text="bitcoin blockchain technology",
            field="embedding",
        )
        if "result-set" in result:
            num_found = result["result-set"].get("numFound", 0)
            print_success(f"✓ Semantic search works ({num_found} results)")
        else:
            print_error("✗ Semantic search failed")
            success = False

        return success

    except Exception as e:
        print_error(f"Vector search failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def main():
    """Run all tests."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 70}{Colors.END}")
    print(
        f"{Colors.BOLD}{Colors.BLUE}Comprehensive solr-mcp Integration Test{Colors.END}"
    )
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 70}{Colors.END}\n")

    # Setup client
    config = SolrConfig(
        solr_base_url="http://localhost:8983/solr",
        zookeeper_hosts=["localhost:2181"],
        default_collection="unified",
    )
    client = SolrClient(config=config)

    collection = "unified"
    results = {}

    # Run all tests
    results["List Collections"] = await test_list_collections(client)
    results["List Fields"] = await test_list_fields(client, collection)
    results["Schema Operations"] = await test_schema_operations(client, collection)
    results["Indexing Operations"] = await test_indexing_operations(client, collection)
    results["Query Features"] = await test_query_features(client, collection)
    results["Vector Search"] = await test_vector_search(client, collection)

    # Print summary
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 70}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}TEST SUMMARY{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 70}{Colors.END}\n")

    passed = sum(1 for r in results.values() if r)
    total = len(results)

    for test_name, result in results.items():
        status = (
            f"{Colors.GREEN}✓ PASS{Colors.END}"
            if result
            else f"{Colors.RED}✗ FAIL{Colors.END}"
        )
        print(f"{status} - {test_name}")

    print(f"\n{Colors.BOLD}Results: {passed}/{total} tests passed{Colors.END}")

    if passed == total:
        print(f"\n{Colors.GREEN}{Colors.BOLD}🎉 ALL TESTS PASSED! 🎉{Colors.END}\n")
        return 0
    else:
        print(f"\n{Colors.YELLOW}{Colors.BOLD}⚠️  Some tests failed ⚠️{Colors.END}\n")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
