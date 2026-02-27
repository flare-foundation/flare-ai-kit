"""MCP server configuration settings."""

from __future__ import annotations

import json
from typing import Annotated, Literal

import structlog
from pydantic import BaseModel, BeforeValidator, Field, HttpUrl, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = structlog.get_logger(__name__)


def _parse_json_servers(
    value: dict[str, object] | str | None,
) -> dict[str, object]:
    """Parse servers from JSON string or pass through dict."""
    if value is None:
        return {}
    if isinstance(value, str):
        try:
            parsed: dict[str, object] = json.loads(value)
        except json.JSONDecodeError as e:
            msg = f"Invalid JSON in MCP__SERVERS: {e}"
            raise ValueError(msg) from e
        else:
            return parsed
    return value


class MCPServerConfig(BaseModel):
    """Configuration for a single MCP server (stdio or remote)."""

    # Stdio config fields (for local process-based servers)
    command: str | None = Field(
        default=None,
        description="Command to run the MCP server process",
    )
    args: list[str] = Field(
        default_factory=list,
        description="Arguments for the command",
    )
    env: dict[str, str] = Field(
        default_factory=dict,
        description="Environment variables for the server process",
    )

    # Remote config fields (for external servers)
    url: HttpUrl | None = Field(
        default=None,
        description="URL of the remote MCP server",
    )
    transport: Literal["stdio", "sse", "http"] = Field(
        default="stdio",
        description="Transport type: 'stdio' for local, 'sse' or 'http' for remote",
    )
    headers: dict[str, str] = Field(
        default_factory=dict,
        description="HTTP headers for authentication with remote servers",
    )

    # Common fields
    timeout: float = Field(
        default=30.0,
        description="Connection timeout in seconds",
    )
    tool_filter: list[str] | None = Field(
        default=None,
        description="List of tool names to expose (None = all tools)",
    )
    enabled: bool = Field(
        default=True,
        description="Whether this server is enabled",
    )

    @model_validator(mode="after")
    def validate_config_type(self) -> MCPServerConfig:
        """Ensure either command (stdio) or url (remote) is provided, not both."""
        has_command = self.command is not None
        has_url = self.url is not None

        if has_command and has_url:
            msg = "Cannot specify both 'command' (stdio) and 'url' (remote)"
            raise ValueError(msg)

        if not has_command and not has_url:
            msg = "Must specify either 'command' (for stdio) or 'url' (for remote)"
            raise ValueError(msg)

        # Infer transport type from config
        if has_command:
            object.__setattr__(self, "transport", "stdio")
        elif self.transport == "stdio":
            # Remote server with default transport, switch to http
            object.__setattr__(self, "transport", "http")

        return self

    @property
    def is_stdio(self) -> bool:
        """Check if this is a stdio-based (local process) server."""
        return self.command is not None

    @property
    def is_remote(self) -> bool:
        """Check if this is a remote server."""
        return self.url is not None


# Type alias for parsed servers with BeforeValidator
ParsedServers = Annotated[
    dict[str, MCPServerConfig],
    BeforeValidator(_parse_json_servers),
]


class MCPSettings(BaseSettings):
    """Settings for MCP (Model Context Protocol) server integration."""

    model_config = SettingsConfigDict(
        env_prefix="MCP__",
        env_file=".env",
        extra="ignore",
    )

    servers: ParsedServers = Field(
        default_factory=dict,
        description="Map of server names to their configurations (JSON string)",
    )

    def get_enabled_servers(self) -> dict[str, MCPServerConfig]:
        """Return only enabled server configurations."""
        return {name: config for name, config in self.servers.items() if config.enabled}

    @property
    def has_servers(self) -> bool:
        """Check if any MCP servers are configured."""
        return len(self.get_enabled_servers()) > 0
