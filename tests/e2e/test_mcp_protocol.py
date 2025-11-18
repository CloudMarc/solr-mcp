"""
End-to-end tests for MCP protocol compliance.

These tests verify that the solr-mcp server correctly implements
the Model Context Protocol by testing the actual server process.
"""

import asyncio
import json
import subprocess
import sys

import pytest
import pytest_asyncio


@pytest_asyncio.fixture
async def mcp_server():
    """
    Start the MCP server as a subprocess for testing.

    The server communicates over stdin/stdout using JSON-RPC.
    """
    # Set environment variables for testing
    import os
    env = os.environ.copy()
    env["SOLR_BASE_URL"] = "http://localhost:8983/solr"
    env["DEFAULT_COLLECTION"] = "unified"

    # Start the server process in stdio mode (for MCP protocol over stdin/stdout)
    proc = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        "solr_mcp.server",
        "--transport",
        "stdio",
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )

    # Give server time to initialize and check if it crashed
    await asyncio.sleep(1)

    # Check if process is still running
    if proc.returncode is not None:
        # Process crashed, get stderr
        stderr_data = await proc.stderr.read()
        raise RuntimeError(f"Server crashed during startup: {stderr_data.decode()}")

    yield proc

    # Clean up
    if proc.returncode is None:
        proc.terminate()
        try:
            await asyncio.wait_for(proc.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()


async def send_mcp_request(proc, method, params=None, request_id=1):
    """
    Send an MCP JSON-RPC request to the server.

    Args:
        proc: The server subprocess
        method: The MCP method to call
        params: Optional parameters for the method
        request_id: Request ID (default 1)

    Returns:
        The parsed JSON response
    """
    request = {"jsonrpc": "2.0", "id": request_id, "method": method}

    if params is not None:
        request["params"] = params

    request_json = json.dumps(request) + "\n"
    proc.stdin.write(request_json.encode())
    await proc.stdin.drain()

    # Read response
    response_line = await asyncio.wait_for(proc.stdout.readline(), timeout=5.0)
    return json.loads(response_line)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_mcp_initialize(mcp_server):
    """Test that server responds to initialize request."""
    response = await send_mcp_request(
        mcp_server,
        "initialize",
        {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test-client", "version": "1.0.0"},
        },
    )

    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 1
    assert "result" in response
    assert "protocolVersion" in response["result"]
    assert "capabilities" in response["result"]
    assert "serverInfo" in response["result"]


@pytest.mark.asyncio
@pytest.mark.integration
async def test_mcp_list_tools(mcp_server):
    """Test that server responds to tools/list request."""
    # First initialize
    await send_mcp_request(
        mcp_server,
        "initialize",
        {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test-client", "version": "1.0.0"},
        },
    )

    # Then list tools
    response = await send_mcp_request(mcp_server, "tools/list", {}, request_id=2)

    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 2
    assert "result" in response
    assert "tools" in response["result"]

    tools = response["result"]["tools"]
    assert len(tools) > 0

    tool_names = [t["name"] for t in tools]

    # Verify some expected tools are present
    expected_tools = [
        "execute_query",
        "execute_list_collections",
        "execute_list_fields",
        "execute_add_documents",
        "execute_delete_documents",
        "execute_schema_list_fields",
        "execute_schema_add_field",
        "execute_terms",
        "execute_select_query",
    ]

    for tool in expected_tools:
        assert tool in tool_names, f"Expected tool '{tool}' not found in {tool_names}"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_mcp_tool_schemas(mcp_server):
    """Test that all tools have proper schemas."""
    # Initialize
    await send_mcp_request(
        mcp_server,
        "initialize",
        {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test-client", "version": "1.0.0"},
        },
    )

    # List tools
    response = await send_mcp_request(mcp_server, "tools/list", {}, request_id=2)
    tools = response["result"]["tools"]

    # Check each tool has required fields
    for tool in tools:
        assert "name" in tool
        assert "description" in tool
        assert "inputSchema" in tool

        # Verify input schema is valid JSON Schema
        schema = tool["inputSchema"]
        assert "type" in schema
        assert schema["type"] == "object"
        assert "properties" in schema


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.skip(reason="Requires running Solr instance")
async def test_mcp_call_tool_list_collections(mcp_server):
    """Test calling solr_list_collections tool through MCP."""
    # Initialize
    await send_mcp_request(
        mcp_server,
        "initialize",
        {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test-client", "version": "1.0.0"},
        },
    )

    # Call tool
    response = await send_mcp_request(
        mcp_server,
        "tools/call",
        {"name": "solr_list_collections", "arguments": {}},
        request_id=2,
    )

    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 2

    # Should either succeed or fail gracefully
    if "result" in response:
        # Success case
        assert "content" in response["result"]
    else:
        # Error case (e.g., Solr not running)
        assert "error" in response
        assert "message" in response["error"]


@pytest.mark.asyncio
@pytest.mark.integration
async def test_mcp_error_handling(mcp_server):
    """Test that server handles invalid requests properly."""
    # Initialize
    await send_mcp_request(
        mcp_server,
        "initialize",
        {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test-client", "version": "1.0.0"},
        },
    )

    # Call non-existent tool
    response = await send_mcp_request(
        mcp_server,
        "tools/call",
        {"name": "nonexistent_tool", "arguments": {}},
        request_id=2,
    )

    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 2
    # MCP protocol returns errors in result with isError flag
    if "error" in response:
        assert "message" in response["error"]
    else:
        assert "result" in response
        assert response["result"].get("isError") is True
        assert "content" in response["result"]


@pytest.mark.asyncio
@pytest.mark.integration
async def test_mcp_invalid_json_rpc(mcp_server):
    """Test that server handles invalid JSON-RPC requests."""
    # Send malformed request (missing required fields)
    request = {"invalid": "request"}
    request_json = json.dumps(request) + "\n"
    mcp_server.stdin.write(request_json.encode())
    await mcp_server.stdin.drain()

    # Server should send an error response or notification
    response_line = await asyncio.wait_for(mcp_server.stdout.readline(), timeout=5.0)
    response = json.loads(response_line)

    # MCP can respond with either an error or an error notification
    if "error" in response:
        # JSON-RPC error codes: -32600 = Invalid Request
        assert response["error"]["code"] == -32600
    else:
        # Or as an error notification
        assert "method" in response
        assert response["method"] == "notifications/message"
        assert response.get("params", {}).get("level") == "error"


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.skip(reason="Concurrent stdout reading not supported in test environment")
async def test_mcp_concurrent_requests(mcp_server):
    """Test that server can handle multiple requests."""
    # Initialize
    await send_mcp_request(
        mcp_server,
        "initialize",
        {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test-client", "version": "1.0.0"},
        },
    )

    # Send multiple list_tools requests with different IDs
    responses = await asyncio.gather(
        send_mcp_request(mcp_server, "tools/list", {}, request_id=2),
        send_mcp_request(mcp_server, "tools/list", {}, request_id=3),
        send_mcp_request(mcp_server, "tools/list", {}, request_id=4),
    )

    # All should succeed
    for i, response in enumerate(responses, start=2):
        assert response["id"] == i
        assert "result" in response
        assert "tools" in response["result"]


@pytest.mark.asyncio
@pytest.mark.integration
async def test_mcp_server_info(mcp_server):
    """Test that server provides correct server info."""
    response = await send_mcp_request(
        mcp_server,
        "initialize",
        {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test-client", "version": "1.0.0"},
        },
    )

    server_info = response["result"]["serverInfo"]
    assert "name" in server_info
    assert server_info["name"] == "Solr MCP Server"
    assert "version" in server_info
