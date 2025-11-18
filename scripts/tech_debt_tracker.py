#!/usr/bin/env python3
"""
Tech Debt Tracker - Find TODO, FIXME, HACK, and other code debt markers.
"""

import asyncio
import httpx


async def track_tech_debt():
    """Track technical debt markers in the codebase."""
    print("\n" + "=" * 80)
    print("TECHNICAL DEBT TRACKER")
    print("=" * 80)

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Search for various debt markers
        markers = {
            "TODO": "Things that need to be done",
            "FIXME": "Things that need to be fixed",
            "HACK": "Hacky solutions that should be improved",
            "XXX": "Warning or important notes",
            "NOTE": "General notes",
            "BUG": "Known bugs"
        }

        print("\n📊 Technical Debt Summary:\n")

        total_debt_items = 0
        debt_details = []

        for marker, description in markers.items():
            response = await client.get(
                "http://localhost:8983/solr/codebase/select",
                params={
                    "q": f'tags_ss:py AND content:"{marker}"',
                    "rows": "100",
                    "fl": "source,content",
                    "wt": "json"
                }
            )

            result = response.json()
            count = result['response']['numFound']
            total_debt_items += count

            if count > 0:
                print(f"  {marker:8} {count:3} occurrences - {description}")

                # Extract actual TODO/FIXME lines
                docs = result['response']['docs']
                for doc in docs:
                    source = doc.get('source', 'unknown')
                    content = doc.get('content', [''])[0] if isinstance(doc.get('content'), list) else doc.get('content', '')

                    for i, line in enumerate(content.split('\n'), 1):
                        if marker in line:
                            debt_details.append({
                                'marker': marker,
                                'file': source,
                                'line': i,
                                'text': line.strip()
                            })

        print(f"\n  TOTAL:   {total_debt_items:3} technical debt markers found")

        # Show detailed breakdown
        if debt_details:
            print(f"\n📋 Detailed Tech Debt Items (showing first 20):\n")
            for i, item in enumerate(debt_details[:20], 1):
                print(f"{i:2}. [{item['marker']}] {item['file']}:{item['line']}")
                print(f"    {item['text'][:100]}")
                print()

        # Find files with the most debt
        print("\n📈 Files with Most Technical Debt:\n")

        file_debt_count = {}
        for item in debt_details:
            file_debt_count[item['file']] = file_debt_count.get(item['file'], 0) + 1

        sorted_files = sorted(file_debt_count.items(), key=lambda x: x[1], reverse=True)

        for i, (filename, count) in enumerate(sorted_files[:10], 1):
            print(f"{i:2}. {filename:60} {count:3} items")


async def find_long_functions():
    """Find potentially complex functions (very long)."""
    print("\n" + "=" * 80)
    print("LONG FUNCTION DETECTOR - Functions that might be too complex")
    print("=" * 80)

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Get all Python source files
        response = await client.get(
            "http://localhost:8983/solr/codebase/select",
            params={
                "q": "tags_ss:py AND category_ss:source",
                "rows": "100",
                "fl": "source,content",
                "wt": "json"
            }
        )

        docs = response.json()['response']['docs']

        long_functions = []

        for doc in docs:
            source = doc.get('source', 'unknown')
            content = doc.get('content', [''])[0] if isinstance(doc.get('content'), list) else doc.get('content', '')

            lines = content.split('\n')
            in_function = False
            func_start = 0
            func_name = ""
            indent_level = 0

            for i, line in enumerate(lines, 1):
                stripped = line.lstrip()

                # Detect function start
                if stripped.startswith('def ') or stripped.startswith('async def '):
                    if in_function:
                        # End previous function
                        func_length = i - func_start - 1
                        if func_length > 50:  # Flag functions > 50 lines
                            long_functions.append({
                                'file': source,
                                'function': func_name,
                                'start': func_start,
                                'length': func_length
                            })

                    in_function = True
                    func_start = i
                    func_name = stripped.split('(')[0].replace('def ', '').replace('async ', '').strip()
                    indent_level = len(line) - len(stripped)

                # Detect function end (dedent or another def at same level)
                elif in_function and stripped and not stripped.startswith('#'):
                    current_indent = len(line) - len(stripped)
                    if current_indent <= indent_level and stripped.startswith(('def ', 'class ', 'async def ')):
                        func_length = i - func_start - 1
                        if func_length > 50:
                            long_functions.append({
                                'file': source,
                                'function': func_name,
                                'start': func_start,
                                'length': func_length
                            })
                        in_function = False

        # Sort by length
        long_functions.sort(key=lambda x: x['length'], reverse=True)

        print(f"\nFound {len(long_functions)} functions longer than 50 lines:\n")

        for i, func in enumerate(long_functions[:15], 1):
            print(f"{i:2}. {func['function']:30} in {func['file']:40} ({func['length']} lines)")


async def find_missing_tests():
    """Find source files that might not have corresponding test files."""
    print("\n" + "=" * 80)
    print("MISSING TESTS DETECTOR")
    print("=" * 80)

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Get all source files
        source_response = await client.get(
            "http://localhost:8983/solr/codebase/select",
            params={
                "q": "tags_ss:py AND category_ss:source AND -source:*test* AND -source:*__init__*",
                "rows": "100",
                "fl": "source",
                "wt": "json"
            }
        )

        source_files = [doc['source'] for doc in source_response.json()['response']['docs']]

        # Get all test files
        test_response = await client.get(
            "http://localhost:8983/solr/codebase/select",
            params={
                "q": "tags_ss:py AND category_ss:tests",
                "rows": "100",
                "fl": "source",
                "wt": "json"
            }
        )

        test_files = [doc['source'] for doc in test_response.json()['response']['docs']]

        print(f"\nSource files: {len(source_files)}")
        print(f"Test files: {len(test_files)}")

        # Simple heuristic: look for matching test files
        potentially_untested = []

        for source_file in source_files:
            # Extract module name
            module_name = source_file.split('/')[-1].replace('.py', '')

            # Look for test file
            has_test = any(f'test_{module_name}' in test_file for test_file in test_files)

            if not has_test:
                potentially_untested.append(source_file)

        print(f"\nFiles potentially missing dedicated tests: {len(potentially_untested)}\n")

        for i, filename in enumerate(potentially_untested[:20], 1):
            print(f"{i:2}. {filename}")


async def main():
    """Run all tech debt analyses."""
    await track_tech_debt()
    await find_long_functions()
    await find_missing_tests()

    print("\n" + "=" * 80)
    print("✅ Analysis Complete!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
