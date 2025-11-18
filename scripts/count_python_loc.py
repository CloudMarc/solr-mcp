#!/usr/bin/env python3
"""
Count Python lines of code using the Solr-indexed codebase, excluding tests.
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import httpx


async def count_python_loc():
    """Count Python lines of code, excluding tests."""
    print("\n=== Counting Python Lines of Code (excluding tests) ===\n")

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Query for Python files that are NOT in the tests category
        response = await client.get(
            "http://localhost:8983/solr/codebase/select",
            params={
                "q": "tags_ss:py AND category_ss:python AND -category_ss:tests",
                "rows": "1000",  # Get all non-test Python files
                "fl": "id,source,content",
                "wt": "json",
            }
        )
        result = response.json()

        total_files = result['response']['numFound']
        docs = result['response']['docs']

        print(f"Non-test Python files found: {total_files}")
        print(f"Retrieved documents: {len(docs)}\n")

        total_lines = 0
        total_non_blank = 0
        total_code_lines = 0  # Lines that aren't blank or pure comments

        file_stats = []

        for doc in docs:
            source = doc.get('source', 'unknown')
            content = doc.get('content', [''])[0] if isinstance(doc.get('content'), list) else doc.get('content', '')

            if not content:
                continue

            lines = content.split('\n')
            file_lines = len(lines)

            # Count non-blank lines
            non_blank = sum(1 for line in lines if line.strip())

            # Count code lines (excluding blank lines and comment-only lines)
            code_lines = 0
            for line in lines:
                stripped = line.strip()
                if stripped and not stripped.startswith('#'):
                    code_lines += 1

            total_lines += file_lines
            total_non_blank += non_blank
            total_code_lines += code_lines

            file_stats.append({
                'source': source,
                'lines': file_lines,
                'non_blank': non_blank,
                'code': code_lines
            })

        # Sort by code lines
        file_stats.sort(key=lambda x: x['code'], reverse=True)

        print("=" * 80)
        print(f"TOTAL LINES OF CODE (excluding tests):")
        print(f"  Total lines (including blanks):  {total_lines:,}")
        print(f"  Non-blank lines:                  {total_non_blank:,}")
        print(f"  Code lines (excl. comments):      {total_code_lines:,}")
        print("=" * 80)

        print(f"\nTop 10 largest files by code lines:\n")
        for i, stat in enumerate(file_stats[:10], 1):
            print(f"{i:2}. {stat['source']:60} {stat['code']:5} lines")

        # Also show category breakdown
        print("\n" + "=" * 80)
        print("Category Breakdown:")
        print("=" * 80)

        # Query for different categories
        categories = ['source', 'tools', 'vector', 'scripts', 'documentation', 'configuration']
        for category in categories:
            cat_response = await client.get(
                "http://localhost:8983/solr/codebase/select",
                params={
                    "q": f"tags_ss:py AND category_ss:{category} AND -category_ss:tests",
                    "rows": "0",
                    "wt": "json",
                }
            )
            cat_result = cat_response.json()
            count = cat_result['response']['numFound']
            if count > 0:
                print(f"  {category:20} {count:3} files")


async def main():
    await count_python_loc()


if __name__ == "__main__":
    asyncio.run(main())
