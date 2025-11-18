#!/usr/bin/env python3
"""Fix all B904 errors by adding 'from e' to exception chains."""

import re
from pathlib import Path


def fix_file(file_path: Path) -> int:
    """Fix B904 errors in a single file. Returns number of fixes."""
    content = file_path.read_text()
    lines = content.split('\n')

    fixed_count = 0
    i = 0
    while i < len(lines):
        line = lines[i]

        # Check if this is a raise statement that ends with )
        if re.match(r'^\s+raise\s+\w+.*\)\s*$', line) and ' from ' not in line:
            # Check if we're in an except block by looking backwards
            in_except = False
            for j in range(i - 1, max(0, i - 20), -1):
                prev_line = lines[j]
                if re.match(r'^\s*except\s+.*\s+as\s+\w+:', prev_line):
                    in_except = True
                    break
                # Stop if we hit a non-indented line or different block
                if prev_line and not prev_line[0].isspace():
                    break
                if re.match(r'^\s*(def|class|if|for|while|with|try).*:', prev_line):
                    break

            if in_except:
                # Add 'from e' before the final )
                lines[i] = line.rstrip()[:-1] + ') from e'
                fixed_count += 1

        # Handle multi-line raise statements
        elif re.match(r'^\s+raise\s+\w+.*[^)]$', line) and ' from ' not in line:
            # Find the closing parenthesis
            closing_line = i
            paren_count = line.count('(') - line.count(')')

            while paren_count > 0 and closing_line < len(lines) - 1:
                closing_line += 1
                paren_count += lines[closing_line].count('(') - lines[closing_line].count(')')

            # Check if we're in an except block
            in_except = False
            for j in range(i - 1, max(0, i - 20), -1):
                prev_line = lines[j]
                if re.match(r'^\s*except\s+.*\s+as\s+\w+:', prev_line):
                    in_except = True
                    break
                if prev_line and not prev_line[0].isspace():
                    break
                if re.match(r'^\s*(def|class|if|for|while|with|try).*:', prev_line):
                    break

            if in_except and closing_line < len(lines):
                # Add 'from e' to the closing line
                close_line = lines[closing_line].rstrip()
                if close_line.endswith(')'):
                    lines[closing_line] = close_line + ' from e'
                    fixed_count += 1

        i += 1

    if fixed_count > 0:
        file_path.write_text('\n'.join(lines))
        print(f"✓ {file_path}: fixed {fixed_count} errors")

    return fixed_count


def main():
    """Fix all B904 errors in the project."""
    root = Path('/Users/marcbyrd/Documents/Github/solr-mcp')

    files_to_fix = [
        root / 'solr_mcp/solr/client.py',
        root / 'solr_mcp/solr/collections.py',
        root / 'solr_mcp/solr/config.py',
        root / 'solr_mcp/solr/query/builder.py',
        root / 'solr_mcp/solr/query/executor.py',
    ]

    total_fixed = 0
    for file_path in files_to_fix:
        if file_path.exists():
            total_fixed += fix_file(file_path)

    print(f"\n✨ Fixed {total_fixed} B904 errors")


if __name__ == '__main__':
    main()
