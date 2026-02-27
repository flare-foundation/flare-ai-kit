"""Tests for MCP Manager."""

from unittest.mock import MagicMock, patch

import pytest

from flare_ai_kit.mcp.manager import MCPManager
from flare_ai_kit.mcp.settings import MCPServerConfig, MCPSettings


class TestMCPManager:
    """Tests for MCPManager class."""

    def test_init_with_empty_settings(self):
        """Test initialization with empty settings."""
        settings = MCPSettings(servers={})
        manager = MCPManager(settings)

        assert not manager.has_servers
        assert manager.server_names == []
        assert manager.get_errors() == {}

    def test_init_with_servers(self):
        """Test initialization with configured servers."""
        settings = MCPSettings(
            servers={
                "server1": MCPServerConfig(command="echo", args=[]),
                "server2": MCPServerConfig(command="cat", args=[]),
            }
        )
        manager = MCPManager(settings)

        assert manager.has_servers
        assert set(manager.server_names) == {"server1", "server2"}

    @patch("google.adk.tools.mcp_tool.mcp_toolset.McpToolset")
    def test_get_toolsets_sync_creates_toolsets(self, mock_toolset_class):
        """Test that toolsets are created for each server."""
        mock_toolset_class.return_value = MagicMock()

        settings = MCPSettings(
            servers={
                "server1": MCPServerConfig(command="npx", args=["-y", "server1"]),
                "server2": MCPServerConfig(command="npx", args=["-y", "server2"]),
            }
        )
        manager = MCPManager(settings)

        toolsets = manager.get_toolsets_sync()

        assert mock_toolset_class.call_count == 2
        assert len(toolsets) == 2

    @patch("google.adk.tools.mcp_tool.mcp_toolset.McpToolset")
    def test_get_toolsets_sync_caches_result(self, mock_toolset_class):
        """Test that toolsets are only created once."""
        mock_toolset_class.return_value = MagicMock()

        settings = MCPSettings(
            servers={"server1": MCPServerConfig(command="echo", args=[])}
        )
        manager = MCPManager(settings)

        toolsets1 = manager.get_toolsets_sync()
        toolsets2 = manager.get_toolsets_sync()

        assert mock_toolset_class.call_count == 1
        assert toolsets1 == toolsets2

    @patch("google.adk.tools.mcp_tool.mcp_toolset.McpToolset")
    def test_get_toolsets_handles_errors(self, mock_toolset_class):
        """Test graceful error handling during toolset creation."""
        mock_toolset_class.side_effect = [
            Exception("Connection failed"),
            MagicMock(),
        ]

        settings = MCPSettings(
            servers={
                "failing": MCPServerConfig(command="fail", args=[]),
                "working": MCPServerConfig(command="work", args=[]),
            }
        )
        manager = MCPManager(settings)

        toolsets = manager.get_toolsets_sync()

        assert len(toolsets) == 1
        errors = manager.get_errors()
        assert "failing" in errors
        assert "working" not in errors

    @patch("google.adk.tools.mcp_tool.mcp_toolset.McpToolset")
    def test_get_toolset_by_name(self, mock_toolset_class):
        """Test getting specific toolset by name."""
        mock_instance = MagicMock()
        mock_toolset_class.return_value = mock_instance

        settings = MCPSettings(
            servers={"my-server": MCPServerConfig(command="echo", args=[])}
        )
        manager = MCPManager(settings)

        toolset = manager.get_toolset("my-server")

        assert toolset is mock_instance

    @patch("google.adk.tools.mcp_tool.mcp_toolset.McpToolset")
    def test_get_toolset_not_found(self, mock_toolset_class):
        """Test getting non-existent toolset returns None."""
        mock_toolset_class.return_value = MagicMock()

        settings = MCPSettings(
            servers={"my-server": MCPServerConfig(command="echo", args=[])}
        )
        manager = MCPManager(settings)

        toolset = manager.get_toolset("nonexistent")

        assert toolset is None

    @patch("google.adk.tools.mcp_tool.mcp_toolset.McpToolset")
    def test_disabled_servers_not_created(self, mock_toolset_class):
        """Test that disabled servers don't create toolsets."""
        mock_toolset_class.return_value = MagicMock()

        settings = MCPSettings(
            servers={
                "enabled": MCPServerConfig(command="echo", args=[], enabled=True),
                "disabled": MCPServerConfig(command="echo", args=[], enabled=False),
            }
        )
        manager = MCPManager(settings)

        toolsets = manager.get_toolsets_sync()

        assert mock_toolset_class.call_count == 1
        assert len(toolsets) == 1

    @pytest.mark.asyncio
    async def test_get_toolsets_async(self):
        """Test async toolsets method."""
        settings = MCPSettings(servers={})
        manager = MCPManager(settings)

        toolsets = await manager.get_toolsets()

        assert toolsets == []

    @pytest.mark.asyncio
    async def test_close(self):
        """Test close cleans up all toolsets."""
        mock_toolset = MagicMock()
        mock_toolset.close = MagicMock(return_value=None)

        settings = MCPSettings(servers={})
        manager = MCPManager(settings)
        manager._toolsets = {"test": mock_toolset}
        manager._initialized = True

        await manager.close()

        mock_toolset.close.assert_called_once()
        assert len(manager._toolsets) == 0
        assert manager._initialized is False

    @pytest.mark.asyncio
    async def test_close_handles_errors(self):
        """Test close continues on errors."""
        mock_toolset1 = MagicMock()
        mock_toolset1.close = MagicMock(side_effect=Exception("Error"))

        mock_toolset2 = MagicMock()
        mock_toolset2.close = MagicMock(return_value=None)

        settings = MCPSettings(servers={})
        manager = MCPManager(settings)
        manager._toolsets = {"failing": mock_toolset1, "working": mock_toolset2}
        manager._initialized = True

        await manager.close()

        mock_toolset1.close.assert_called_once()
        mock_toolset2.close.assert_called_once()
        assert len(manager._toolsets) == 0

    @patch("google.adk.tools.mcp_tool.mcp_toolset.McpToolset")
    def test_create_toolset_stdio_missing_command(self, mock_toolset_class):
        """Test that _create_toolset raises ValueError when stdio config has no command."""
        # Create a mock config that bypasses Pydantic validation
        mock_config = MagicMock()
        mock_config.is_stdio = True
        mock_config.command = None  # Missing command

        settings = MCPSettings(servers={})
        manager = MCPManager(settings)

        with pytest.raises(ValueError, match="stdio config requires 'command'"):
            manager._create_toolset("test-server", mock_config)

    @patch("google.adk.tools.mcp_tool.mcp_toolset.McpToolset")
    def test_create_toolset_sse_missing_url(self, mock_toolset_class):
        """Test that _create_toolset raises ValueError when SSE config has no url."""
        mock_config = MagicMock()
        mock_config.is_stdio = False
        mock_config.transport = "sse"
        mock_config.url = None  # Missing URL

        settings = MCPSettings(servers={})
        manager = MCPManager(settings)

        with pytest.raises(ValueError, match="SSE config requires 'url'"):
            manager._create_toolset("test-server", mock_config)

    @patch("google.adk.tools.mcp_tool.mcp_toolset.McpToolset")
    def test_create_toolset_http_missing_url(self, mock_toolset_class):
        """Test that _create_toolset raises ValueError when HTTP config has no url."""
        mock_config = MagicMock()
        mock_config.is_stdio = False
        mock_config.transport = "http"
        mock_config.url = None  # Missing URL

        settings = MCPSettings(servers={})
        manager = MCPManager(settings)

        with pytest.raises(ValueError, match="HTTP config requires 'url'"):
            manager._create_toolset("test-server", mock_config)

    def test_import_error_propagates(self):
        """Test that ImportError is re-raised, not silently caught."""
        import sys

        settings = MCPSettings(
            servers={"server1": MCPServerConfig(command="echo", args=[])}
        )
        manager = MCPManager(settings)

        original_mcp = sys.modules.get("mcp")
        sys.modules["mcp"] = None  # type: ignore[assignment]

        try:
            with pytest.raises(ImportError, match="MCP dependencies not installed"):
                manager.get_toolsets_sync()
        finally:
            if original_mcp is not None:
                sys.modules["mcp"] = original_mcp
            elif "mcp" in sys.modules:
                del sys.modules["mcp"]

    @pytest.mark.asyncio
    async def test_close_awaits_async_close(self):
        """Test that close() properly awaits an async toolset.close() method."""
        close_awaited = False

        async def async_close():
            nonlocal close_awaited
            close_awaited = True

        mock_toolset = MagicMock()
        mock_toolset.close = MagicMock(return_value=async_close())

        settings = MCPSettings(servers={})
        manager = MCPManager(settings)
        manager._toolsets = {"async-server": mock_toolset}
        manager._initialized = True

        await manager.close()

        assert close_awaited, "Async close() should have been awaited"
        assert len(manager._toolsets) == 0

    @patch("google.adk.tools.mcp_tool.mcp_toolset.McpToolset")
    def test_non_import_errors_stored_in_get_errors(self, mock_toolset_class):
        """Test that non-ImportError exceptions are stored and remaining toolsets returned."""
        working_toolset = MagicMock()
        mock_toolset_class.side_effect = [
            ValueError("Invalid config"),
            working_toolset,
        ]

        settings = MCPSettings(
            servers={
                "failing": MCPServerConfig(command="fail", args=[]),
                "working": MCPServerConfig(command="work", args=[]),
            }
        )
        manager = MCPManager(settings)

        toolsets = manager.get_toolsets_sync()

        assert len(toolsets) == 1
        assert toolsets[0] is working_toolset

        errors = manager.get_errors()
        assert "failing" in errors
        assert isinstance(errors["failing"], ValueError)
        assert "working" not in errors

    @patch("google.adk.tools.mcp_tool.mcp_toolset.McpToolset")
    @patch("google.adk.tools.mcp_tool.mcp_session_manager.SseConnectionParams")
    def test_create_toolset_sse_server(self, mock_sse_params, mock_toolset_class):
        """Test that SSE remote server is created with correct params."""
        mock_toolset_instance = MagicMock()
        mock_toolset_class.return_value = mock_toolset_instance

        settings = MCPSettings(
            servers={
                "sse-server": MCPServerConfig(
                    url="http://localhost:3000/sse",
                    transport="sse",
                    headers={"Authorization": "Bearer token"},
                    timeout=60.0,
                    tool_filter=["tool1", "tool2"],
                ),
            }
        )
        manager = MCPManager(settings)

        toolsets = manager.get_toolsets_sync()

        assert len(toolsets) == 1
        mock_sse_params.assert_called_once()
        call_kwargs = mock_sse_params.call_args.kwargs
        assert call_kwargs["url"] == "http://localhost:3000/sse"
        assert call_kwargs["headers"] == {"Authorization": "Bearer token"}
        assert call_kwargs["timeout"] == 60.0
        mock_toolset_class.assert_called_once()
        toolset_kwargs = mock_toolset_class.call_args.kwargs
        assert toolset_kwargs["tool_filter"] == ["tool1", "tool2"]

    @patch("google.adk.tools.mcp_tool.mcp_toolset.McpToolset")
    @patch(
        "google.adk.tools.mcp_tool.mcp_session_manager.StreamableHTTPConnectionParams"
    )
    def test_create_toolset_http_server(self, mock_http_params, mock_toolset_class):
        """Test that HTTP remote server is created with correct params."""
        mock_toolset_instance = MagicMock()
        mock_toolset_class.return_value = mock_toolset_instance

        settings = MCPSettings(
            servers={
                "http-server": MCPServerConfig(
                    url="https://api.example.com/mcp",
                    transport="http",
                    headers={"X-API-Key": "secret"},
                    timeout=45.0,
                ),
            }
        )
        manager = MCPManager(settings)

        toolsets = manager.get_toolsets_sync()

        assert len(toolsets) == 1
        mock_http_params.assert_called_once()
        call_kwargs = mock_http_params.call_args.kwargs
        assert call_kwargs["url"] == "https://api.example.com/mcp"
        assert call_kwargs["headers"] == {"X-API-Key": "secret"}
        assert call_kwargs["timeout"] == 45.0

    @patch("google.adk.tools.mcp_tool.mcp_toolset.McpToolset")
    @patch("google.adk.tools.mcp_tool.mcp_session_manager.StdioConnectionParams")
    @patch("mcp.StdioServerParameters")
    def test_stdio_server_uses_empty_env_not_none(
        self, mock_server_params, mock_stdio_params, mock_toolset_class
    ):
        """Test that stdio servers use env={}, not env=None."""
        mock_toolset_class.return_value = MagicMock()

        settings = MCPSettings(
            servers={
                "test-server": MCPServerConfig(command="echo", args=["hello"]),
            }
        )
        manager = MCPManager(settings)

        manager.get_toolsets_sync()

        mock_server_params.assert_called_once()
        call_kwargs = mock_server_params.call_args.kwargs
        assert call_kwargs["env"] == {}, (
            "env should be empty dict, not None (prevents parent env inheritance)"
        )
