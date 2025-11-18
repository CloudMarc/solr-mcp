#!/bin/bash
# Setup script for integration tests
# This script ensures Solr is properly configured for all integration tests

set -e  # Exit on error

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

SOLR_URL="http://localhost:8983/solr"
COLLECTION="unified"
ZK_HOST="localhost:2181"

echo -e "${GREEN}=== Setting up Solr for Integration Tests ===${NC}"

# Function to check if Solr is running
check_solr() {
    echo -e "${CYAN}Checking if Solr is running...${NC}"
    if curl -s "${SOLR_URL}/admin/info/system" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Solr is running${NC}"
        return 0
    else
        echo -e "${RED}✗ Solr is not running${NC}"
        return 1
    fi
}

# Function to wait for Solr to be ready
wait_for_solr() {
    echo -e "${CYAN}Waiting for Solr to be ready...${NC}"
    local max_attempts=30
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        if curl -s "${SOLR_URL}/admin/info/system" > /dev/null 2>&1; then
            echo -e "${GREEN}✓ Solr is ready${NC}"
            return 0
        fi
        echo -e "${YELLOW}Attempt $attempt/$max_attempts - waiting for Solr...${NC}"
        sleep 2
        attempt=$((attempt + 1))
    done

    echo -e "${RED}✗ Solr did not become ready in time${NC}"
    return 1
}

# Function to delete collection if it exists
delete_collection() {
    echo -e "${CYAN}Checking if collection '${COLLECTION}' exists...${NC}"

    if curl -s "${SOLR_URL}/admin/collections?action=LIST" | grep -q "\"${COLLECTION}\""; then
        echo -e "${YELLOW}Collection '${COLLECTION}' exists, deleting...${NC}"
        curl -s "${SOLR_URL}/admin/collections?action=DELETE&name=${COLLECTION}" > /dev/null
        echo -e "${GREEN}✓ Collection deleted${NC}"
        sleep 2
    else
        echo -e "${CYAN}Collection '${COLLECTION}' does not exist${NC}"
    fi
}

# UpdateLog is already enabled in the _default configset, so we don't need to configure it

# Function to create collection
create_collection() {
    echo -e "${CYAN}Creating collection '${COLLECTION}'...${NC}"

    curl -s "${SOLR_URL}/admin/collections?action=CREATE&name=${COLLECTION}&numShards=1&replicationFactor=1" > /dev/null

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Collection created${NC}"
        sleep 3
    else
        echo -e "${RED}✗ Failed to create collection${NC}"
        return 1
    fi
}

# Function to add schema fields
configure_schema() {
    echo -e "${CYAN}Configuring schema...${NC}"

    # Add text field (general text with standard analyzer)
    curl -X POST "${SOLR_URL}/${COLLECTION}/schema" \
        -H "Content-Type: application/json" \
        -d '{
            "add-field": {
                "name": "text",
                "type": "text_general",
                "stored": true,
                "indexed": true
            }
        }' > /dev/null 2>&1

    # Add title field
    curl -X POST "${SOLR_URL}/${COLLECTION}/schema" \
        -H "Content-Type: application/json" \
        -d '{
            "add-field": {
                "name": "title",
                "type": "text_general",
                "stored": true,
                "indexed": true
            }
        }' > /dev/null 2>&1

    # Add section_number field with docValues for stats (use 'plong' for integers with docValues)
    curl -X POST "${SOLR_URL}/${COLLECTION}/schema" \
        -H "Content-Type: application/json" \
        -d '{
            "add-field": {
                "name": "section_number",
                "type": "plong",
                "stored": true,
                "indexed": true,
                "docValues": true
            }
        }' 2>&1 | grep -v "already exists" || true

    # Add test_score field (renamed from score to avoid ambiguity)
    curl -X POST "${SOLR_URL}/${COLLECTION}/schema" \
        -H "Content-Type: application/json" \
        -d '{
            "add-field": {
                "name": "test_score",
                "type": "plong",
                "stored": true,
                "indexed": true,
                "docValues": true
            }
        }' 2>&1 | grep -v "already exists" || true

    # Add field type for dense vectors (768 dimensions for nomic-embed-text)
    curl -X POST "${SOLR_URL}/${COLLECTION}/schema" \
        -H "Content-Type: application/json" \
        -d '{
            "add-field-type": {
                "name": "knn_vector_768",
                "class": "solr.DenseVectorField",
                "vectorDimension": 768,
                "similarityFunction": "cosine"
            }
        }' 2>&1 | grep -v "already exists" || true

    # Add embedding field for semantic search (named 'embedding' to match tests)
    curl -X POST "${SOLR_URL}/${COLLECTION}/schema" \
        -H "Content-Type: application/json" \
        -d '{
            "add-field": {
                "name": "embedding",
                "type": "knn_vector_768",
                "stored": true,
                "indexed": true
            }
        }' 2>&1 | grep -v "already exists" || true

    echo -e "${GREEN}✓ Schema configured${NC}"
}

# Function to update test data files to use test_score instead of score
update_test_data() {
    echo -e "${CYAN}Updating test data to use 'test_score' field...${NC}"

    # Update bitcoin_sections.json if it exists
    if [ -f "$PROJECT_ROOT/data/processed/bitcoin_sections.json" ]; then
        # Use Python to safely update the JSON
        python3 << 'EOF'
import json
import sys

try:
    with open('/Users/marcbyrd/Documents/Github/solr-mcp/data/processed/bitcoin_sections.json', 'r') as f:
        data = json.load(f)

    # Rename 'score' to 'test_score' if present
    modified = False
    for doc in data:
        if 'score' in doc:
            doc['test_score'] = doc.pop('score')
            modified = True

    if modified:
        with open('/Users/marcbyrd/Documents/Github/solr-mcp/data/processed/bitcoin_sections.json', 'w') as f:
            json.dump(data, f, indent=2)
        print("Updated bitcoin_sections.json")
    else:
        print("No 'score' field found in bitcoin_sections.json")
except Exception as e:
    print(f"Error updating bitcoin_sections.json: {e}", file=sys.stderr)
EOF
    fi
}

# Function to index test data
index_test_data() {
    echo -e "${CYAN}Indexing test data...${NC}"

    if [ -f "$PROJECT_ROOT/data/processed/bitcoin_sections.json" ]; then
        cd "$PROJECT_ROOT"
        uv run python scripts/unified_index.py data/processed/bitcoin_sections.json --collection unified
        echo -e "${GREEN}✓ Test data indexed${NC}"
    else
        echo -e "${YELLOW}⚠ Bitcoin sections data not found, skipping indexing${NC}"
    fi
}

# Main execution
main() {
    cd "$PROJECT_ROOT"

    # Step 1: Check if Solr is running, if not start it
    if ! check_solr; then
        echo -e "${YELLOW}Starting Solr with Docker Compose...${NC}"
        docker-compose up -d
        wait_for_solr || exit 1
    fi

    # Step 2: Delete existing collection
    delete_collection

    # Step 3: Create collection with default config (includes updateLog)
    create_collection || exit 1

    # Step 4: Configure schema
    configure_schema

    # Step 5: Update test data files
    update_test_data

    # Step 6: Index test data
    index_test_data

    echo -e "${GREEN}=== Integration Test Setup Complete ===${NC}"
    echo -e "${CYAN}Solr URL: ${SOLR_URL}${NC}"
    echo -e "${CYAN}Collection: ${COLLECTION}${NC}"
    echo -e "${GREEN}Ready to run: make test-integration${NC}"
}

main "$@"
