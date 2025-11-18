#!/usr/bin/env python3
"""
Clever ways to use solr-mcp with the indexed codebase collection.
Demonstrates advanced search, analytics, and discovery capabilities.
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import httpx
import json


async def semantic_code_search():
    """Use vector embeddings for semantic code search."""
    print("\n" + "=" * 80)
    print("1. SEMANTIC CODE SEARCH - Find code by meaning, not just keywords")
    print("=" * 80)

    async with httpx.AsyncClient(timeout=30.0) as client:
        # First, get embedding for our search query
        query_text = "handling errors and exceptions from network requests"

        embed_response = await client.post(
            "http://localhost:11434/api/embeddings",
            json={"model": "nomic-embed-text", "prompt": query_text}
        )
        query_embedding = embed_response.json()["embedding"]

        # Now use KNN search to find similar code
        # Use POST for vector search with large embedding
        search_response = await client.post(
            "http://localhost:8983/solr/codebase/select",
            params={
                "q": "{!knn f=embedding topK=5}[" + ",".join(map(str, query_embedding)) + "]",
                "fl": "id,source,title,category_ss,score",
                "rows": "5",
                "wt": "json"
            }
        )

        results = search_response.json()
        print(f"\nQuery: '{query_text}'")
        print(f"Found {results['response']['numFound']} semantically similar files:\n")

        for i, doc in enumerate(results['response']['docs'], 1):
            print(f"{i}. {doc['source']:60} (score: {doc.get('score', 0):.4f})")
            print(f"   Categories: {', '.join(doc.get('category_ss', []))}")


async def code_complexity_analysis():
    """Analyze code complexity using stats component."""
    print("\n" + "=" * 80)
    print("2. CODE COMPLEXITY ANALYSIS - Stats on file sizes and structure")
    print("=" * 80)

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Use stats component to analyze content length
        response = await client.get(
            "http://localhost:8983/solr/codebase/select",
            params={
                "q": "category_ss:source AND tags_ss:py",
                "rows": "0",
                "stats": "true",
                "stats.field": "content",
                "wt": "json"
            }
        )

        # Note: Solr's stats component works on numeric fields
        # For text length analysis, we need to fetch docs and analyze
        doc_response = await client.get(
            "http://localhost:8983/solr/codebase/select",
            params={
                "q": "category_ss:source AND tags_ss:py",
                "rows": "1000",
                "fl": "source,content",
                "wt": "json"
            }
        )

        docs = doc_response.json()['response']['docs']

        file_sizes = []
        for doc in docs:
            content = doc.get('content', [''])[0] if isinstance(doc.get('content'), list) else doc.get('content', '')
            lines = len(content.split('\n'))
            chars = len(content)
            file_sizes.append({
                'source': doc.get('source', 'unknown'),
                'lines': lines,
                'chars': chars,
                'avg_line_length': chars / lines if lines > 0 else 0
            })

        file_sizes.sort(key=lambda x: x['lines'], reverse=True)

        total_lines = sum(f['lines'] for f in file_sizes)
        total_chars = sum(f['chars'] for f in file_sizes)
        avg_lines = total_lines / len(file_sizes) if file_sizes else 0
        avg_chars = total_chars / len(file_sizes) if file_sizes else 0

        print(f"\nSource Code Statistics:")
        print(f"  Total files analyzed: {len(file_sizes)}")
        print(f"  Total lines: {total_lines:,}")
        print(f"  Total characters: {total_chars:,}")
        print(f"  Average lines per file: {avg_lines:.1f}")
        print(f"  Average characters per file: {avg_chars:.1f}")

        print(f"\nLargest files:")
        for f in file_sizes[:5]:
            print(f"  {f['source']:50} {f['lines']:5} lines, {f['chars']:7} chars")


async def dependency_graph():
    """Build a simple dependency graph using import statements."""
    print("\n" + "=" * 80)
    print("3. DEPENDENCY ANALYSIS - Find import relationships")
    print("=" * 80)

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Find files that import from solr_mcp.solr
        response = await client.get(
            "http://localhost:8983/solr/codebase/select",
            params={
                "q": 'content:"from solr_mcp.solr" OR content:"import solr_mcp.solr"',
                "rows": "100",
                "fl": "source,content",
                "wt": "json"
            }
        )

        docs = response.json()['response']['docs']

        print(f"\nFiles importing from solr_mcp.solr module: {len(docs)}")

        # Analyze what they're importing
        imports = {}
        for doc in docs:
            source = doc.get('source', 'unknown')
            content = doc.get('content', [''])[0] if isinstance(doc.get('content'), list) else doc.get('content', '')

            for line in content.split('\n'):
                if 'from solr_mcp.solr' in line and 'import' in line:
                    import_stmt = line.strip()
                    if import_stmt not in imports:
                        imports[import_stmt] = []
                    imports[import_stmt].append(source)

        print(f"\nMost common imports:")
        sorted_imports = sorted(imports.items(), key=lambda x: len(x[1]), reverse=True)
        for import_stmt, files in sorted_imports[:10]:
            print(f"  {len(files):2}x {import_stmt[:70]}")


async def documentation_coverage():
    """Analyze documentation coverage."""
    print("\n" + "=" * 80)
    print("4. DOCUMENTATION COVERAGE - Find undocumented code")
    print("=" * 80)

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Find Python files with docstrings
        with_docs = await client.get(
            "http://localhost:8983/solr/codebase/select",
            params={
                "q": 'tags_ss:py AND category_ss:source AND (content:def OR content:class)',
                "rows": "0",
                "wt": "json"
            }
        )

        # All source files
        all_source = await client.get(
            "http://localhost:8983/solr/codebase/select",
            params={
                "q": "tags_ss:py AND category_ss:source",
                "rows": "0",
                "wt": "json"
            }
        )

        documented = with_docs.json()['response']['numFound']
        total = all_source.json()['response']['numFound']
        coverage = (documented / total * 100) if total > 0 else 0

        print(f"\nDocumentation Coverage:")
        print(f"  Files with docstrings: {documented}/{total} ({coverage:.1f}%)")

        # Find files without common documentation patterns
        without_docs = await client.get(
            "http://localhost:8983/solr/codebase/select",
            params={
                "q": 'tags_ss:py AND category_ss:source AND -content:Args AND -content:Returns',
                "rows": "10",
                "fl": "source",
                "wt": "json"
            }
        )

        undocumented = without_docs.json()['response']['docs']
        if undocumented:
            print(f"\nFiles potentially missing docstrings:")
            for doc in undocumented[:10]:
                print(f"  - {doc['source']}")


async def error_handling_patterns():
    """Find error handling patterns in the codebase."""
    print("\n" + "=" * 80)
    print("5. ERROR HANDLING PATTERNS - Find exception handling code")
    print("=" * 80)

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Use faceting to find different exception types
        response = await client.get(
            "http://localhost:8983/solr/codebase/select",
            params={
                "q": "tags_ss:py AND (content:except OR content:raise OR content:try)",
                "rows": "0",
                "facet": "true",
                "facet.field": "category_ss",
                "wt": "json"
            }
        )

        result = response.json()
        total_with_exceptions = result['response']['numFound']

        print(f"\nFiles with exception handling: {total_with_exceptions}")

        # Find specific exception types
        exception_types = [
            "ValueError", "TypeError", "KeyError", "IndexError",
            "ConnectionError", "TimeoutError", "HTTPError",
            "SolrError", "VectorProviderError"
        ]

        print(f"\nException type usage:")
        for exc_type in exception_types:
            exc_response = await client.get(
                "http://localhost:8983/solr/codebase/select",
                params={
                    "q": f'tags_ss:py AND content:"{exc_type}"',
                    "rows": "0",
                    "wt": "json"
                }
            )
            count = exc_response.json()['response']['numFound']
            if count > 0:
                print(f"  {exc_type:20} {count:3} files")


async def code_evolution_timeline():
    """Show when files were last indexed (proxy for modification)."""
    print("\n" + "=" * 80)
    print("6. RECENT ACTIVITY - Recently indexed/modified files")
    print("=" * 80)

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            "http://localhost:8983/solr/codebase/select",
            params={
                "q": "tags_ss:py AND category_ss:source",
                "rows": "10",
                "sort": "date_indexed_dt desc",
                "fl": "source,date_indexed_dt,category_ss",
                "wt": "json"
            }
        )

        docs = response.json()['response']['docs']

        print(f"\nMost recently indexed source files:")
        for i, doc in enumerate(docs, 1):
            date = doc.get('date_indexed_dt', 'unknown')
            categories = ', '.join(doc.get('category_ss', []))
            print(f"{i:2}. {doc['source']:50} [{categories}]")


async def search_by_author_or_metadata():
    """Demonstrate searching by metadata fields."""
    print("\n" + "=" * 80)
    print("7. METADATA SEARCH - Search by file characteristics")
    print("=" * 80)

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Search for tool implementations
        response = await client.get(
            "http://localhost:8983/solr/codebase/select",
            params={
                "q": "category_ss:tools AND tags_ss:py",
                "rows": "20",
                "fl": "source,title",
                "wt": "json"
            }
        )

        docs = response.json()['response']['docs']

        print(f"\nTool implementations ({len(docs)} files):")
        for doc in docs:
            print(f"  - {doc.get('title', ['unknown'])[0] if isinstance(doc.get('title'), list) else doc.get('title', 'unknown')}")


async def hybrid_search_example():
    """Combine keyword search with vector similarity."""
    print("\n" + "=" * 80)
    print("8. HYBRID SEARCH - Combine keyword + semantic search")
    print("=" * 80)

    async with httpx.AsyncClient(timeout=30.0) as client:
        # First get embedding for semantic part
        query_text = "database query execution"

        embed_response = await client.post(
            "http://localhost:11434/api/embeddings",
            json={"model": "nomic-embed-text", "prompt": query_text}
        )
        query_embedding = embed_response.json()["embedding"]

        # Combine keyword search with vector search
        # This finds files that mention "solr" AND are semantically similar to "database query execution"
        vector_str = "[" + ",".join(map(str, query_embedding)) + "]"

        response = await client.post(
            "http://localhost:8983/solr/codebase/select",
            params={
                "q": f'content:solr AND ({{!knn f=embedding topK=10}}{vector_str})',
                "fl": "source,title,category_ss,score",
                "rows": "5",
                "wt": "json"
            }
        )

        results = response.json()
        print(f"\nHybrid search: keyword='solr' + semantic='{query_text}'")
        print(f"Found {results['response']['numFound']} matching files:\n")

        for i, doc in enumerate(results['response']['docs'], 1):
            print(f"{i}. {doc['source']:60}")
            print(f"   Score: {doc.get('score', 0):.4f}, Categories: {', '.join(doc.get('category_ss', []))}")


async def main():
    """Run all examples."""
    print("\n" + "=" * 80)
    print("CLEVER CODEBASE QUERIES WITH SOLR-MCP")
    print("=" * 80)
    print("\nDemonstrating advanced search, analytics, and discovery capabilities")
    print("on the indexed codebase collection...")

    try:
        # Skip semantic search for now (KNN syntax issues)
        # await semantic_code_search()
        await code_complexity_analysis()
        await dependency_graph()
        await documentation_coverage()
        await error_handling_patterns()
        await code_evolution_timeline()
        await search_by_author_or_metadata()
        # await hybrid_search_example()

        print("\n" + "=" * 80)
        print("MORE IDEAS:")
        print("=" * 80)
        print("""
- Find duplicate/similar code using vector similarity
- Build call graphs by analyzing function definitions and calls
- Find code smells (very long functions, high cyclomatic complexity)
- Create a "tech debt" score based on TODO/FIXME comments
- Find orphaned files (not imported by anything)
- Analyze test coverage by comparing test vs source file counts
- Generate documentation suggestions for undocumented functions
- Find outdated patterns or deprecated API usage
- Create a code knowledge graph linking related modules
- Build a search engine for code examples (like "how to handle HTTP errors")
        """)

    except Exception as e:
        print(f"\nError during queries: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
