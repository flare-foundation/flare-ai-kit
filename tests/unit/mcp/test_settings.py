"""Tests for MCP settings parsing."""

import pytest

from flare_ai_kit.mcp.settings import MCPServerConfig, MCPSettings


class TestMCPServerConfig:
    """Tests for MCPServerConfig model."""

    def test_stdio_config(self):
        """Test valid stdio server configuration."""
        config = MCPServerConfig(
            command="npx",
            args=["-y", "@modelcontextprotocol/server-filesystem", "/path"],
            env={"API_KEY": "secret"},
        )
        assert config.is_stdio
        assert not config.is_remote
        assert config.transport == "stdio"
        assert config.command == "npx"
        assert config.args == ["-y", "@modelcontextprotocol/server-filesystem", "/path"]
        assert config.env == {"API_KEY": "secret"}

    def test_stdio_config_minimal(self):
        """Test minimal stdio configuration."""
        config = MCPServerConfig(command="echo", args=["hello"])
        assert config.is_stdio
        assert config.transport == "stdio"
        assert config.enabled is True
        assert config.timeout == 30.0

    def test_remote_sse_config(self):
        """Test valid SSE remote server configuration."""
        config = MCPServerConfig(
            url="http://localhost:3000/sse",
            transport="sse",
        )
        assert config.is_remote
        assert not config.is_stdio
        assert config.transport == "sse"
        assert str(config.url) == "http://localhost:3000/sse"

    def test_remote_http_config(self):
        """Test valid HTTP remote server configuration."""
        config = MCPServerConfig(
            url="http://localhost:3000/mcp",
            transport="http",
            headers={"Authorization": "Bearer token"},
        )
        assert config.is_remote
        assert config.transport == "http"
        assert config.headers == {"Authorization": "Bearer token"}

    def test_remote_default_transport(self):
        """Test that remote server defaults to http transport."""
        config = MCPServerConfig(url="http://localhost:3000/mcp")
        assert config.is_remote
        assert config.transport == "http"

    def test_invalid_both_command_and_url(self):
        """Test that having both command and url raises error."""
        with pytest.raises(ValueError, match="Cannot specify both"):
            MCPServerConfig(
                command="npx",
                url="http://localhost:3000",
            )

    def test_invalid_neither_command_nor_url(self):
        """Test that having neither command nor url raises error."""
        with pytest.raises(ValueError, match="Must specify either"):
            MCPServerConfig()

    def test_tool_filter(self):
        """Test tool filtering configuration."""
        config = MCPServerConfig(
            command="npx",
            args=["-y", "some-server"],
            tool_filter=["read_file", "write_file"],
        )
        assert config.tool_filter == ["read_file", "write_file"]

    def test_disabled_server(self):
        """Test disabled server configuration."""
        config = MCPServerConfig(
            command="npx",
            args=["-y", "some-server"],
            enabled=False,
        )
        assert config.enabled is False

    def test_custom_timeout(self):
        """Test custom timeout configuration."""
        config = MCPServerConfig(
            command="npx",
            args=["-y", "some-server"],
            timeout=60.0,
        )
        assert config.timeout == 60.0


class TestMCPSettings:
    """Tests for MCPSettings model."""

    def test_empty_settings(self):
        """Test empty MCP settings."""
        settings = MCPSettings()
        assert len(settings.servers) == 0
        assert settings.get_enabled_servers() == {}
        assert settings.has_servers is False

    def test_settings_with_servers(self):
        """Test settings with configured servers."""
        settings = MCPSettings(
            servers={
                "filesystem": MCPServerConfig(
                    command="npx",
                    args=["-y", "@modelcontextprotocol/server-filesystem", "/path"],
                ),
                "remote": MCPServerConfig(
                    url="http://localhost:3000/sse",
                    transport="sse",
                ),
            }
        )
        assert len(settings.servers) == 2
        assert "filesystem" in settings.servers
        assert "remote" in settings.servers
        assert settings.servers["filesystem"].is_stdio
        assert settings.servers["remote"].is_remote
        assert settings.has_servers is True

    def test_get_enabled_servers(self):
        """Test filtering enabled servers."""
        settings = MCPSettings(
            servers={
                "enabled": MCPServerConfig(command="echo", args=[], enabled=True),
                "disabled": MCPServerConfig(command="echo", args=[], enabled=False),
            }
        )
        enabled = settings.get_enabled_servers()
        assert "enabled" in enabled
        assert "disabled" not in enabled

    def test_parse_json_from_env_var(self, monkeypatch):
        """Test parsing MCP__SERVERS from environment variable."""
        json_config = (
            '{"filesystem": {"command": "npx", "args": ["-y", "server"]}, '
            '"api": {"url": "http://localhost:3000/mcp", "transport": "http"}}'
        )
        monkeypatch.setenv("MCP__SERVERS", json_config)

        settings = MCPSettings()

        assert len(settings.servers) == 2
        assert "filesystem" in settings.servers
        assert "api" in settings.servers
        assert settings.servers["filesystem"].command == "npx"
        assert settings.servers["api"].transport == "http"

    def test_parse_tool_filter_from_env_var(self, monkeypatch):
        """Test that tool_filter is properly parsed from JSON env var."""
        json_config = (
            '{"fs": {"command": "npx", "args": ["-y", "server"], '
            '"tool_filter": ["read_file", "list_directory"]}}'
        )
        monkeypatch.setenv("MCP__SERVERS", json_config)

        settings = MCPSettings()

        assert settings.servers["fs"].tool_filter == ["read_file", "list_directory"]

    def test_parse_invalid_json_from_env_var(self, monkeypatch):
        """Test error on invalid JSON in env var."""
        from pydantic_settings.exceptions import SettingsError

        monkeypatch.setenv("MCP__SERVERS", "not valid json{")

        with pytest.raises(SettingsError, match="error parsing value"):
            MCPSettings()

    def test_multiple_servers_mixed_types(self):
        """Test settings with mixed server types."""
        settings = MCPSettings(
            servers={
                "local-fs": MCPServerConfig(
                    command="npx",
                    args=["-y", "@modelcontextprotocol/server-filesystem"],
                ),
                "local-git": MCPServerConfig(
                    command="python",
                    args=["-m", "mcp_git_server"],
                ),
                "remote-api": MCPServerConfig(
                    url="https://api.example.com/mcp",
                    transport="http",
                    headers={"X-API-Key": "secret"},
                ),
                "remote-stream": MCPServerConfig(
                    url="https://stream.example.com/sse",
                    transport="sse",
                ),
            }
        )

        assert len(settings.servers) == 4
        assert settings.servers["local-fs"].is_stdio
        assert settings.servers["local-git"].is_stdio
        assert settings.servers["remote-api"].is_remote
        assert settings.servers["remote-api"].transport == "http"
        assert settings.servers["remote-stream"].transport == "sse"
