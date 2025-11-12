"""Unit tests for SolrMCPServer."""

import sys
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from solr_mcp.server import SolrMCPServer, create_starlette_app, main


class TestSolrMCPServer:
    """Tests for SolrMCPServer class."""

    @patch("solr_mcp.server.SolrClient")
    @patch("solr_mcp.server.FastMCP")
    def test_init_defaults(self, mock_fastmcp, mock_solr_client):
        """Test initialization with default values."""
        with patch.dict("os.environ", {}, clear=True):
            server = SolrMCPServer()

            assert server.port == 8081
            assert server.stdio is False
            assert server.config.solr_base_url == "http://localhost:8983/solr"
            assert server.config.connection_timeout == 10

    @patch("solr_mcp.server.SolrClient")
    @patch("solr_mcp.server.FastMCP")
    def test_init_custom_params(self, mock_fastmcp, mock_solr_client):
        """Test initialization with custom parameters."""
        server = SolrMCPServer(
            mcp_port=9000,
            solr_base_url="http://custom:8983/solr",
            zookeeper_hosts=["zk1:2181", "zk2:2181"],
            connection_timeout=30,
            stdio=True,
        )

        assert server.port == 9000
        assert server.stdio is True
        assert server.config.solr_base_url == "http://custom:8983/solr"
        assert server.config.zookeeper_hosts == ["zk1:2181", "zk2:2181"]
        assert server.config.connection_timeout == 30

    @patch("solr_mcp.server.SolrClient")
    @patch("solr_mcp.server.FastMCP")
    def test_init_with_custom_values_overrides_defaults(
        self, mock_fastmcp, mock_solr_client
    ):
        """Test initialization with custom values (which override environment defaults)."""
        # Since os.getenv is evaluated at function definition time, we can't mock it
        # Instead, test that explicit values work
        server = SolrMCPServer(
            mcp_port=9999,
            solr_base_url="http://custom:8983/solr",
            zookeeper_hosts=["custom1:2181", "custom2:2181"],
            connection_timeout=60,
        )

        assert server.port == 9999
        assert server.config.solr_base_url == "http://custom:8983/solr"
        assert server.config.zookeeper_hosts == ["custom1:2181", "custom2:2181"]
        assert server.config.connection_timeout == 60

    @patch("solr_mcp.server.SolrClient")
    @patch("solr_mcp.server.FastMCP")
    @patch("sys.exit")
    def test_setup_server_connection_error(
        self, mock_exit, mock_fastmcp, mock_solr_client
    ):
        """Test that connection errors cause sys.exit."""
        mock_solr_client.side_effect = Exception("Connection failed")

        SolrMCPServer()

        mock_exit.assert_called_once_with(1)

    @patch("solr_mcp.server.SolrClient")
    @patch("solr_mcp.server.FastMCP")
    def test_connect_to_solr(self, mock_fastmcp, mock_solr_client):
        """Test Solr client connection."""
        server = SolrMCPServer()

        mock_solr_client.assert_called_once()
        assert server.solr_client is not None

    @patch("solr_mcp.server.SolrClient")
    @patch("solr_mcp.server.FastMCP")
    def test_setup_tools_called(self, mock_fastmcp, mock_solr_client):
        """Test that tools are registered."""
        mock_mcp_instance = MagicMock()
        mock_fastmcp.return_value = mock_mcp_instance

        server = SolrMCPServer()

        # Tool decorator should be called
        assert mock_mcp_instance.tool.called

    @patch("solr_mcp.server.SolrClient")
    @patch("solr_mcp.server.FastMCP")
    def test_transform_tool_params_with_mcp_string(
        self, mock_fastmcp, mock_solr_client
    ):
        """Test parameter transformation when mcp is a string."""
        server = SolrMCPServer()

        params = {"mcp": "server_name", "other_param": "value"}
        result = server._transform_tool_params("test_tool", params)

        assert result["mcp"] is server
        assert result["other_param"] == "value"

    @patch("solr_mcp.server.SolrClient")
    @patch("solr_mcp.server.FastMCP")
    def test_transform_tool_params_with_mcp_object(
        self, mock_fastmcp, mock_solr_client
    ):
        """Test parameter transformation when mcp is already an object."""
        server = SolrMCPServer()
        mock_server = MagicMock()

        params = {"mcp": mock_server, "other_param": "value"}
        result = server._transform_tool_params("test_tool", params)

        assert result["mcp"] is mock_server
        assert result["other_param"] == "value"

    @patch("solr_mcp.server.SolrClient")
    @patch("solr_mcp.server.FastMCP")
    def test_transform_tool_params_without_mcp(self, mock_fastmcp, mock_solr_client):
        """Test parameter transformation without mcp parameter."""
        server = SolrMCPServer()

        params = {"other_param": "value"}
        result = server._transform_tool_params("test_tool", params)

        assert "mcp" not in result
        assert result["other_param"] == "value"

    @pytest.mark.asyncio
    @patch("solr_mcp.server.SolrClient")
    @patch("solr_mcp.server.FastMCP")
    async def test_wrap_tool(self, mock_fastmcp, mock_solr_client):
        """Test tool wrapper functionality."""
        server = SolrMCPServer()

        # Create a mock tool
        async def mock_tool(arg1, mcp=None):
            return f"result: {arg1}, mcp: {mcp}"

        mock_tool.__name__ = "test_tool"
        mock_tool.__doc__ = "Test tool description"

        wrapped = server._wrap_tool(mock_tool)

        # Test that wrapper has correct metadata
        assert wrapped._is_tool is True
        assert wrapped._tool_name == "test_tool"
        assert wrapped._tool_description == "Test tool description"

        # Test that wrapper transforms params
        result = await wrapped(arg1="test", mcp="server_name")
        assert "mcp:" in result

    @patch("solr_mcp.server.SolrClient")
    @patch("solr_mcp.server.FastMCP")
    def test_run_stdio(self, mock_fastmcp, mock_solr_client):
        """Test running server in stdio mode."""
        mock_mcp_instance = MagicMock()
        mock_fastmcp.return_value = mock_mcp_instance

        server = SolrMCPServer(stdio=True)
        server.run()

        mock_mcp_instance.run.assert_called_once_with("stdio")

    @patch("solr_mcp.server.SolrClient")
    @patch("solr_mcp.server.FastMCP")
    def test_run_sse(self, mock_fastmcp, mock_solr_client):
        """Test running server in SSE mode."""
        mock_mcp_instance = MagicMock()
        mock_fastmcp.return_value = mock_mcp_instance

        server = SolrMCPServer(stdio=False)
        server.run()

        mock_mcp_instance.run.assert_called_once_with("sse")

    @pytest.mark.asyncio
    @patch("solr_mcp.server.SolrClient")
    @patch("solr_mcp.server.FastMCP")
    async def test_close_with_close_method(self, mock_fastmcp, mock_solr_client):
        """Test cleanup when client has close method."""
        mock_solr_instance = AsyncMock()
        mock_solr_instance.close = AsyncMock()
        mock_solr_client.return_value = mock_solr_instance

        mock_mcp_instance = MagicMock()
        mock_mcp_instance.close = AsyncMock()
        mock_mcp_instance.tool = MagicMock(return_value=MagicMock(return_value=None))
        mock_fastmcp.return_value = mock_mcp_instance

        server = SolrMCPServer()
        await server.close()

        mock_solr_instance.close.assert_called_once()
        mock_mcp_instance.close.assert_called_once()

    @pytest.mark.asyncio
    @patch("solr_mcp.server.SolrClient")
    @patch("solr_mcp.server.FastMCP")
    async def test_close_without_close_method(self, mock_fastmcp, mock_solr_client):
        """Test cleanup when client doesn't have close method."""
        mock_solr_instance = MagicMock()
        # Ensure the mock doesn't have a close attribute
        del mock_solr_instance.close
        mock_solr_client.return_value = mock_solr_instance

        mock_mcp_instance = MagicMock()
        mock_mcp_instance.close = AsyncMock()  # MCP should still have async close
        mock_mcp_instance.tool = MagicMock(return_value=MagicMock(return_value=None))
        mock_fastmcp.return_value = mock_mcp_instance

        server = SolrMCPServer()
        await server.close()  # Should not raise

        # MCP close should still be called
        mock_mcp_instance.close.assert_called_once()


class TestCreateStarletteApp:
    """Tests for create_starlette_app function."""

    @patch("solr_mcp.server.SseServerTransport")
    @patch("solr_mcp.server.Starlette")
    def test_create_starlette_app(self, mock_starlette, mock_sse_transport):
        """Test Starlette app creation."""
        mock_server = MagicMock()

        app = create_starlette_app(mock_server, debug=True)

        mock_sse_transport.assert_called_once_with("/messages/")
        mock_starlette.assert_called_once()

        # Check that routes were created
        call_kwargs = mock_starlette.call_args[1]
        assert call_kwargs["debug"] is True
        assert "routes" in call_kwargs
        assert len(call_kwargs["routes"]) == 2  # Route for SSE and Mount for messages

    @patch("solr_mcp.server.SseServerTransport")
    @patch("solr_mcp.server.Starlette")
    def test_create_starlette_app_default_debug(
        self, mock_starlette, mock_sse_transport
    ):
        """Test Starlette app creation with default debug."""
        mock_server = MagicMock()

        app = create_starlette_app(mock_server)

        call_kwargs = mock_starlette.call_args[1]
        assert call_kwargs["debug"] is False


class TestMain:
    """Tests for main() function."""

    @patch("solr_mcp.server.SolrMCPServer")
    @patch("sys.argv", ["solr-mcp"])
    def test_main_defaults(self, mock_server_class):
        """Test main with default arguments."""
        mock_server_instance = MagicMock()
        mock_server_instance.mcp = MagicMock()
        mock_server_instance.mcp._mcp_server = MagicMock()
        mock_server_class.return_value = mock_server_instance

        with patch.dict("os.environ", {}, clear=True):
            with patch("uvicorn.run") as mock_uvicorn:
                main()

                # Check server was created with defaults
                mock_server_class.assert_called_once()
                call_kwargs = mock_server_class.call_args[1]
                assert call_kwargs["mcp_port"] == 8081
                assert call_kwargs["solr_base_url"] == "http://localhost:8983/solr"
                assert call_kwargs["stdio"] is False

    @patch("solr_mcp.server.SolrMCPServer")
    @patch(
        "sys.argv",
        [
            "solr-mcp",
            "--mcp-port",
            "9000",
            "--solr-base-url",
            "http://custom:8983/solr",
            "--zookeeper-hosts",
            "zk1:2181,zk2:2181",
            "--connection-timeout",
            "30",
            "--transport",
            "stdio",
        ],
    )
    def test_main_custom_args(self, mock_server_class):
        """Test main with custom arguments."""
        mock_server_instance = MagicMock()
        mock_server_class.return_value = mock_server_instance

        main()

        mock_server_class.assert_called_once()
        call_kwargs = mock_server_class.call_args[1]
        assert call_kwargs["mcp_port"] == 9000
        assert call_kwargs["solr_base_url"] == "http://custom:8983/solr"
        assert call_kwargs["zookeeper_hosts"] == ["zk1:2181", "zk2:2181"]
        assert call_kwargs["connection_timeout"] == 30
        assert call_kwargs["stdio"] is True

        # In stdio mode, server.run() should be called
        mock_server_instance.run.assert_called_once()

    @patch("solr_mcp.server.SolrMCPServer")
    @patch(
        "sys.argv",
        ["solr-mcp", "--transport", "sse", "--host", "localhost", "--port", "9090"],
    )
    def test_main_sse_mode(self, mock_server_class):
        """Test main with SSE transport mode."""
        mock_server_instance = MagicMock()
        mock_server_instance.mcp = MagicMock()
        mock_server_instance.mcp._mcp_server = MagicMock()
        mock_server_class.return_value = mock_server_instance

        with patch("solr_mcp.server.create_starlette_app") as mock_create_app:
            with patch("uvicorn.run") as mock_uvicorn:
                main()

                # Server should be created
                mock_server_class.assert_called_once()

                # Starlette app should be created
                mock_create_app.assert_called_once()

                # Uvicorn should run the app
                mock_uvicorn.assert_called_once()
                call_args = mock_uvicorn.call_args[1]
                assert call_args["host"] == "localhost"
                assert call_args["port"] == 9090

    @patch("solr_mcp.server.SolrMCPServer")
    @patch("sys.argv", ["solr-mcp", "--log-level", "DEBUG"])
    def test_main_log_level(self, mock_server_class):
        """Test main with custom log level."""
        mock_server_instance = MagicMock()
        mock_server_instance.mcp = MagicMock()
        mock_server_instance.mcp._mcp_server = MagicMock()
        mock_server_class.return_value = mock_server_instance

        with patch("solr_mcp.server.logging.basicConfig") as mock_logging:
            with patch("uvicorn.run"):
                main()

                # Check logging was configured
                mock_logging.assert_called_once()
                import logging

                assert mock_logging.call_args[1]["level"] == logging.DEBUG

    @patch("solr_mcp.server.SolrMCPServer")
    @patch("sys.argv", ["solr-mcp", "--log-level", "ERROR"])
    def test_main_log_level_error(self, mock_server_class):
        """Test main with ERROR log level."""
        mock_server_instance = MagicMock()
        mock_server_instance.mcp = MagicMock()
        mock_server_instance.mcp._mcp_server = MagicMock()
        mock_server_class.return_value = mock_server_instance

        with patch("solr_mcp.server.logging.basicConfig") as mock_logging:
            with patch("uvicorn.run"):
                main()

                import logging

                assert mock_logging.call_args[1]["level"] == logging.ERROR
