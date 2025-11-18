#!/bin/bash
set -e

echo "🚀 Starting Comprehensive Integration Tests"
echo "============================================="

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Track failures
FAILURES=0

# Helper function to run a step
run_step() {
    local step_num=$1
    local step_name=$2
    local step_command=$3
    
    echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${YELLOW}Step $step_num: $step_name${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    
    if eval "$step_command"; then
        echo -e "${GREEN}✓ $step_name passed${NC}"
        return 0
    else
        echo -e "${RED}✗ $step_name failed${NC}"
        FAILURES=$((FAILURES + 1))
        return 1
    fi
}

# Change to repo directory
cd "$(dirname "$0")/.."

# 1. Clean up existing Docker containers
run_step 1 "Cleaning up existing Docker containers" \
    "docker compose down -v 2>/dev/null || true"

# 2. Start Docker Cluster
run_step 2 "Starting Solr Docker Cluster" \
    "docker compose up -d && sleep 15"

# 3. Check Solr health
echo -e "\n${YELLOW}Checking Solr health...${NC}"
MAX_RETRIES=30
RETRY_COUNT=0
while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -s http://localhost:8983/solr/admin/info/system > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Solr cluster is healthy${NC}"
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo -e "${YELLOW}Waiting for Solr... ($RETRY_COUNT/$MAX_RETRIES)${NC}"
    sleep 2
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo -e "${RED}✗ Solr cluster failed to start${NC}"
    docker compose logs
    exit 1
fi

# 4. Create test collection
run_step 4 "Creating test collection" \
    "curl -s 'http://localhost:8983/solr/admin/collections?action=CREATE&name=test_collection&numShards=2&replicationFactor=2' > /dev/null"

# Give collection time to initialize
sleep 5

# 5. Run unit tests
run_step 5 "Running Unit Tests" \
    "uv run pytest tests/unit/ -v --tb=short -x"

# 6. Run integration tests
run_step 6 "Running Integration Tests" \
    "uv run pytest tests/integration/ -v --tb=short -x -m integration"

# 7. Test MCP server startup
echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}Step 7: Testing MCP Server Startup${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# Start server in background
uv run solr-mcp > /tmp/solr-mcp-test.log 2>&1 &
SERVER_PID=$!
sleep 3

if ps -p $SERVER_PID > /dev/null 2>&1; then
    echo -e "${GREEN}✓ MCP server starts successfully${NC}"
    kill $SERVER_PID 2>/dev/null || true
else
    echo -e "${RED}✗ MCP server failed to start${NC}"
    echo -e "${RED}Server logs:${NC}"
    cat /tmp/solr-mcp-test.log
    FAILURES=$((FAILURES + 1))
fi

# 8. Code quality checks - Type checking
run_step 8 "Running Type Checking (mypy)" \
    "uv run mypy solr_mcp"

# 9. Code quality checks - Linting
run_step 9 "Running Linting (ruff)" \
    "uv run ruff check solr_mcp"

# 10. Generate coverage report
echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}Step 10: Generating Coverage Report${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

uv run pytest tests/unit/ tests/integration/ \
    --cov=solr_mcp \
    --cov-report=term-missing \
    --cov-report=html \
    --cov-fail-under=60 || {
    echo -e "${YELLOW}⚠ Coverage below 60% (this is a warning, not a failure)${NC}"
}

# Summary
echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
if [ $FAILURES -eq 0 ]; then
    echo -e "${GREEN}✅ All Integration Tests Passed!${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    
    echo -e "\n${GREEN}Test Summary:${NC}"
    echo "  ✓ Docker cluster started"
    echo "  ✓ Unit tests passed"
    echo "  ✓ Integration tests passed"
    echo "  ✓ MCP server starts correctly"
    echo "  ✓ Type checking passed"
    echo "  ✓ Linting passed"
    echo "  ✓ Coverage report generated"
    
    echo -e "\n${YELLOW}Next Steps:${NC}"
    echo "  1. Review coverage: ${BLUE}open htmlcov/index.html${NC}"
    echo "  2. Test with MCP Inspector:"
    echo "     ${BLUE}npx @modelcontextprotocol/inspector uv run solr-mcp${NC}"
    echo "  3. Test with Claude Desktop (see COMPREHENSIVE_INTEGRATION_TESTING.md)"
    echo "  4. Submit your PR! 🚀"
else
    echo -e "${RED}❌ $FAILURES Test(s) Failed${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "\n${YELLOW}Please fix the failures above before proceeding.${NC}"
fi

# Cleanup option
echo -e "\n${YELLOW}Cleanup Options:${NC}"
echo "  1. Keep containers running (for manual testing)"
echo "  2. Stop containers but keep data"
echo "  3. Stop containers and remove all data"
read -p "Choose (1/2/3): " -n 1 -r CLEANUP_CHOICE
echo

case $CLEANUP_CHOICE in
    2)
        docker compose stop
        echo -e "${GREEN}✓ Containers stopped${NC}"
        ;;
    3)
        docker compose down -v
        echo -e "${GREEN}✓ Full cleanup complete${NC}"
        ;;
    *)
        echo -e "${GREEN}✓ Containers still running for manual testing${NC}"
        echo -e "${YELLOW}To stop later, run: docker compose down -v${NC}"
        ;;
esac

# Exit with failure count
exit $FAILURES
