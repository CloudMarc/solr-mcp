#!/bin/bash

echo "🤖 Setting up solr-mcp for Claude Desktop"
echo "=========================================="

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Get the absolute path to this repo
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"

# Claude Desktop config location (macOS)
CLAUDE_CONFIG_DIR="$HOME/Library/Application Support/Claude"
CLAUDE_CONFIG_FILE="$CLAUDE_CONFIG_DIR/claude_desktop_config.json"

echo -e "\n${YELLOW}Step 1: Checking Prerequisites${NC}"

# Check if Claude Desktop is installed
if [ ! -d "/Applications/Claude.app" ]; then
    echo -e "${RED}✗ Claude Desktop not found${NC}"
    echo -e "${YELLOW}Please install from: https://claude.ai/download${NC}"
    echo -e "Or run: ${BLUE}brew install --cask claude${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Claude Desktop is installed${NC}"

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo -e "${RED}✗ uv not found${NC}"
    echo -e "${YELLOW}Please install uv first${NC}"
    exit 1
fi
echo -e "${GREEN}✓ uv is installed${NC}"

# Check if Docker is running
if ! docker ps &> /dev/null; then
    echo -e "${RED}✗ Docker is not running${NC}"
    echo -e "${YELLOW}Please start Docker Desktop${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Docker is running${NC}"

echo -e "\n${YELLOW}Step 2: Starting Solr Cluster${NC}"
cd "$REPO_DIR"
docker compose up -d
sleep 10

# Check Solr health
if curl -s http://localhost:8983/solr/admin/info/system > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Solr cluster is running${NC}"
else
    echo -e "${RED}✗ Solr cluster failed to start${NC}"
    echo -e "${YELLOW}Run: docker compose logs${NC}"
    exit 1
fi

# Create test collection if it doesn't exist
echo -e "\n${YELLOW}Step 3: Creating test collection${NC}"
curl -s "http://localhost:8983/solr/admin/collections?action=CREATE&name=test_collection&numShards=2&replicationFactor=2" > /dev/null 2>&1 || true
echo -e "${GREEN}✓ Test collection ready${NC}"

echo -e "\n${YELLOW}Step 4: Configuring Claude Desktop${NC}"

# Create config directory if it doesn't exist
mkdir -p "$CLAUDE_CONFIG_DIR"

# Backup existing config
if [ -f "$CLAUDE_CONFIG_FILE" ]; then
    cp "$CLAUDE_CONFIG_FILE" "$CLAUDE_CONFIG_FILE.backup.$(date +%Y%m%d_%H%M%S)"
    echo -e "${GREEN}✓ Backed up existing config${NC}"
fi

# Create or update config
cat > "$CLAUDE_CONFIG_FILE" << EOF
{
  "mcpServers": {
    "solr": {
      "command": "uv",
      "args": [
        "--directory",
        "$REPO_DIR",
        "run",
        "solr-mcp"
      ],
      "env": {
        "SOLR_URL": "http://localhost:8983/solr",
        "DEFAULT_COLLECTION": "test_collection"
      }
    }
  }
}
EOF

echo -e "${GREEN}✓ Claude Desktop config updated${NC}"
echo -e "${BLUE}Config location: $CLAUDE_CONFIG_FILE${NC}"

echo -e "\n${YELLOW}Step 5: Testing MCP Server${NC}"

# Test that server starts
timeout 5s uv run solr-mcp > /tmp/solr-mcp-test.log 2>&1 &
SERVER_PID=$!
sleep 2

if ps -p $SERVER_PID > /dev/null 2>&1; then
    echo -e "${GREEN}✓ MCP server starts correctly${NC}"
    kill $SERVER_PID 2>/dev/null || true
else
    echo -e "${RED}✗ MCP server failed to start${NC}"
    echo -e "${RED}Logs:${NC}"
    cat /tmp/solr-mcp-test.log
    exit 1
fi

echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ Setup Complete!${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

echo -e "\n${YELLOW}Next Steps:${NC}"
echo -e "  1. ${RED}Fully quit Claude Desktop${NC} (Cmd+Q, not just close window)"
echo -e "  2. ${GREEN}Restart Claude Desktop${NC}"
echo -e "  3. ${BLUE}Look for the 🔌 icon${NC} in Claude Desktop"
echo -e "  4. ${YELLOW}Start chatting!${NC}"

echo -e "\n${YELLOW}Test Prompts to Try:${NC}"
echo -e '  • "Can you list the Solr collections?"'
echo -e '  • "What fields are in the test_collection?"'
echo -e '  • "Index this document: {id: \"test1\", title: \"Hello World\"}"'
echo -e '  • "Query for documents with title containing Hello"'

echo -e "\n${YELLOW}Troubleshooting:${NC}"
echo -e "  • View config: ${BLUE}cat '$CLAUDE_CONFIG_FILE'${NC}"
echo -e "  • View logs: ${BLUE}tail -f ~/Library/Logs/Claude/mcp*.log${NC}"
echo -e "  • Test server: ${BLUE}uv run solr-mcp${NC}"
echo -e "  • Check Solr: ${BLUE}curl http://localhost:8983/solr/admin/info/system${NC}"

echo -e "\n${GREEN}Happy testing! 🚀${NC}"
