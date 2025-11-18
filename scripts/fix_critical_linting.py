#!/usr/bin/env python3
"""
Fix critical linting errors:
- B904: Add 'from e' to exception chains
- E722: Replace bare except with specific exceptions
"""

import re
from pathlib import Path


def fix_b904_errors(content: str) -> str:
    """Fix B904 - add 'from e' to exception chains."""
    # Pattern: raise SomeException(...) after an except block
    # We need to find except blocks and add 'from e' to raises

    lines = content.split('\n')
    fixed_lines = []
    in_except = False
    except_var = None

    for _i, line in enumerate(lines):
        # Check if we're entering an except block
        except_match = re.match(r'^(\s*)except\s+(\w+(?:\.\w+)*(?:\s*\|\s*\w+(?:\.\w+)*)*)\s+as\s+(\w+):', line)
        if except_match:
            in_except = True
            except_var = except_match.group(3)
            fixed_lines.append(line)
            continue

        # Check if we're exiting the except block (dedent)
        if in_except and line and not line[0].isspace() and line.strip():
            in_except = False
            except_var = None

        # Fix raise statements in except blocks
        if in_except and except_var:
            raise_match = re.match(r'^(\s+)raise\s+(\w+(?:\.\w+)*)\((.*)\)\s*$', line)
            if raise_match and 'from' not in line:
                indent = raise_match.group(1)
                exception = raise_match.group(2)
                args = raise_match.group(3)
                fixed_lines.append(f'{indent}raise {exception}({args}) from {except_var}')
                continue

        fixed_lines.append(line)

    return '\n'.join(fixed_lines)


def fix_e722_errors(content: str) -> str:
    """Fix E722 - replace bare except with Exception."""
    # Replace 'except:' with 'except Exception:'
    return re.sub(r'(\s+)except:\s*$', r'\1except Exception:', content, flags=re.MULTILINE)


def process_file(file_path: Path) -> bool:
    """Process a single file and return True if changes were made."""
    try:
        content = file_path.read_text()
        original = content

        # Apply fixes
        content = fix_b904_errors(content)
        content = fix_e722_errors(content)

        if content != original:
            file_path.write_text(content)
            print(f"✓ Fixed: {file_path}")
            return True
        return False
    except Exception as e:
        print(f"✗ Error processing {file_path}: {e}")
        return False


def main():
    """Fix all Python files in src/ and tests/."""
    root = Path(__file__).parent.parent

    python_files = list(root.glob('src/**/*.py')) + list(root.glob('tests/**/*.py'))

    fixed_count = 0
    for file_path in python_files:
        if process_file(file_path):
            fixed_count += 1

    print(f"\n✨ Fixed {fixed_count} files")


if __name__ == '__main__':
    main()
