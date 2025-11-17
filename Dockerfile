FROM python:3.10-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Copy essential files first
COPY pyproject.toml README.md ./
COPY solr_mcp ./solr_mcp

# Install dependencies (uv automatically creates .venv)
RUN uv sync --no-dev

# Copy the rest of the application
COPY . .

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    SOLR_MCP_ZK_HOSTS=zookeeper:2181 \
    SOLR_MCP_SOLR_URL=http://solr1:8983/solr \
    SOLR_MCP_DEFAULT_COLLECTION=unified \
    OLLAMA_BASE_URL=http://ollama:11434 \
    PATH="/app/.venv/bin:$PATH"

# Expose the port the app runs on
EXPOSE 8000

# Command to run the application
CMD ["python", "-m", "solr_mcp.server"]
