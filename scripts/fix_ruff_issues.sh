#!/bin/bash
set -e

echo "🔧 Fixing Ruff Linting Issues"
echo "=============================="

cd "$(dirname "$0")/.."

echo ""
echo "Phase 1: Auto-fixable issues"
echo "----------------------------"

# Fix unused imports
echo "✓ Removing unused imports..."
uv run ruff check --fix --select F401 .

# Fix code simplifications (safe fixes only first)
echo "✓ Applying safe simplifications..."
uv run ruff check --fix --select SIM .

echo ""
echo "Phase 2: Apply unsafe fixes (with confirmation)"
echo "-----------------------------------------------"
echo "This will apply code simplifications like:"
echo "  - Converting if-else to ternary operators"
echo "  - Combining nested if statements"
echo "  - Using contextlib.suppress() for try-except-pass"
echo ""
read -p "Apply unsafe fixes? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "✓ Applying unsafe fixes..."
    uv run ruff check --fix --unsafe-fixes .
else
    echo "⊘ Skipped unsafe fixes"
fi

echo ""
echo "Phase 3: Check remaining issues"
echo "-------------------------------"
uv run ruff check . | head -50

echo ""
echo "🎯 Summary"
echo "=========="
ERRORS=$(uv run ruff check . 2>&1 | grep "Found [0-9]* error" || echo "Found 0 errors")
echo "$ERRORS"

echo ""
echo "📝 Next steps:"
echo "  1. Review changes: git diff"
echo "  2. For remaining B904 errors (exception chaining), we need manual fixes"
echo "  3. For N803/N805 errors (naming), we should add ignore comments"
echo "  4. Run: make test-all"
