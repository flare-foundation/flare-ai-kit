"""MCP manager for creating and managing MCP toolsets."""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

from .settings import MCPServerConfig, MCPSettings  # noqa: TC001

if TYPE_CHECKING:
    from google.adk.tools.mcp_tool import McpToolset

logger = structlog.get_logger(__name__)


class MCPManager:
    """Creates MCP toolsets from configuration and tracks initialization errors."""

    def __init__(self, settings: MCPSettings) -> None:
        """Initialize the manager with MCP settings."""
        self._settings = settings
        self._toolsets: dict[str, McpToolset] = {}
        self._initialized = False
        self._initialization_errors: dict[str, Exception] = {}

    @property
    def has_servers(self) -> bool:
        """Check if any MCP servers are configured."""
        return self._settings.has_servers

    @property
    def server_names(self) -> list[str]:
        """Get list of configured server names."""
        return list(self._settings.get_enabled_servers().keys())

    def _create_toolset(
        self,
        name: str,
        config: MCPServerConfig,
    ) -> McpToolset:
        """
        Create a McpToolset from server configuration.

        Args:
            name: Server name (for logging).
            config: Server configuration.

        Returns:
            McpToolset instance.

        Raises:
            ImportError: If MCP dependencies are not installed.

        """
        # Check for required MCP dependencies
        try:
            from mcp import StdioServerParameters  # noqa: PLC0415
        except ImportError as e:
            msg = (
                "MCP dependencies not installed. "
                "Install with: pip install flare-ai-kit[mcp]"
            )
            raise ImportError(msg) from e

        # Import ADK MCP tools - these are available in google-adk>=1.19.0
        from google.adk.tools.mcp_tool.mcp_session_manager import (  # noqa: PLC0415
            SseConnectionParams,
            StdioConnectionParams,
            StreamableHTTPConnectionParams,
        )
        from google.adk.tools.mcp_tool.mcp_toolset import McpToolset  # noqa: PLC0415

        connection_params: (
            StdioConnectionParams | SseConnectionParams | StreamableHTTPConnectionParams
        )

        if config.is_stdio:
            # Stdio-based server (local process)
            if config.command is None:
                msg = f"Server {name}: stdio config requires 'command'"
                raise ValueError(msg)
            connection_params = StdioConnectionParams(
                server_params=StdioServerParameters(
                    command=config.command,
                    args=config.args,
                    env=config.env or {},
                ),
                timeout=config.timeout,
            )
            logger.debug(
                "mcp_creating_stdio_toolset",
                server=name,
                command=config.command,
                args=config.args,
            )
        elif config.transport == "sse":
            if config.url is None:
                msg = f"Server {name}: SSE config requires 'url'"
                raise ValueError(msg)
            connection_params = SseConnectionParams(
                url=str(config.url),
                headers=config.headers if config.headers else None,
                timeout=config.timeout,
            )
            logger.debug(
                "mcp_creating_sse_toolset",
                server=name,
                url=str(config.url),
            )
        else:
            if config.url is None:
                msg = f"Server {name}: HTTP config requires 'url'"
                raise ValueError(msg)
            connection_params = StreamableHTTPConnectionParams(
                url=str(config.url),
                headers=config.headers if config.headers else None,
                timeout=config.timeout,
            )
            logger.debug(
                "mcp_creating_http_toolset",
                server=name,
                url=str(config.url),
            )

        return McpToolset(
            connection_params=connection_params,
            tool_filter=config.tool_filter,
        )

    def get_toolsets_sync(self) -> list[McpToolset]:
        """Return configured toolsets; connections are initialized lazily by ADK."""
        if self._initialized:
            return list(self._toolsets.values())

        enabled_servers = self._settings.get_enabled_servers()

        for name, config in enabled_servers.items():
            try:
                toolset = self._create_toolset(name, config)
                self._toolsets[name] = toolset
                logger.info("mcp_toolset_created", server=name)
            except ImportError:
                raise
            except Exception as e:  # noqa: BLE001
                self._initialization_errors[name] = e
                logger.warning(
                    "mcp_toolset_creation_failed",
                    server=name,
                    error=str(e),
                )

        self._initialized = True
        return list(self._toolsets.values())

    async def get_toolsets(self) -> list[McpToolset]:
        """Async wrapper around `get_toolsets_sync()`."""
        return self.get_toolsets_sync()

    def get_toolset(self, name: str) -> McpToolset | None:
        """Get a toolset by server name, initializing toolsets on first access."""
        if not self._initialized:
            self.get_toolsets_sync()
        return self._toolsets.get(name)

    def get_errors(self) -> dict[str, Exception]:
        """Get any errors that occurred during initialization."""
        return dict(self._initialization_errors)

    async def close(self) -> None:
        """Close all MCP connections."""
        for name, toolset in self._toolsets.items():
            try:
                if hasattr(toolset, "close"):
                    close_result = toolset.close()
                    if hasattr(close_result, "__await__"):
                        await close_result
                logger.debug("mcp_toolset_closed", server=name)
            except Exception as e:  # noqa: BLE001
                logger.warning(
                    "mcp_toolset_close_failed",
                    server=name,
                    error=str(e),
                )

        self._toolsets.clear()
        self._initialized = False
