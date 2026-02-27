# MCP (Model Context Protocol) Server Integration

This documentation provides a comprehensive guide to the MCP server integration for Flare AI Kit, enabling AI agents to connect to external tools and services via the Model Context Protocol.

## Quick Start

### 1. Installation

The MCP integration requires additional dependencies:

```bash
# Install with MCP support
uv sync --extra mcp

# Or add the mcp extra to your dependencies
uv add "flare-ai-kit[mcp]"
```

### 2. Configuration

Configure MCP servers via the `MCP__SERVERS` environment variable:

```bash
# .env file
MCP__SERVERS='{"filesystem": {"command": "npx", "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path"]}}'
```

## Server Configuration

### Stdio Servers (Local Processes)

Stdio servers run as local processes and communicate via stdin/stdout

**Environment Variable Format:**

```bash
MCP__SERVERS='{"filesystem": {"command": "npx", "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path"]}}'
```

### SSE Servers (Remote - Server-Sent Events)

SSE servers connect to remote endpoints using Server-Sent Events

**Environment Variable Format:**

```bash
MCP__SERVERS='{"api": {"url": "http://localhost:3000/sse", "transport": "sse", "headers": {"Authorization": "Bearer token"}}}'
```

### HTTP Servers (Remote - Streamable HTTP)

HTTP servers connect using the streamable HTTP transport

**Environment Variable Format:**

```bash
MCP__SERVERS='{"remote": {"url": "https://api.example.com/mcp", "transport": "http"}}'
```

### Mixed Configuration Example

Configure multiple servers of different types:

```bash
MCP__SERVERS='{
  "filesystem": {
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-filesystem", "/workspace"]
  },
  "git": {
    "command": "python",
    "args": ["-m", "mcp_git_server"],
    "env": {"GIT_AUTHOR_NAME": "AI Agent"}
  },
  "external-api": {
    "url": "https://api.example.com/mcp",
    "transport": "http",
    "headers": {"X-API-Key": "secret"}
  },
  "streaming": {
    "url": "http://localhost:3000/sse",
    "transport": "sse"
  }
}'
```

## Configuration Options

### MCPServerConfig Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `command` | `str` | `None` | Command to run (stdio servers) |
| `args` | `list[str]` | `[]` | Arguments for the command |
| `env` | `dict[str, str]` | `{}` | Environment variables for the process |
| `url` | `str` | `None` | URL for remote servers (SSE/HTTP) |
| `transport` | `"stdio"\|"sse"\|"http"` | `"stdio"` | Transport type |
| `headers` | `dict[str, str]` | `{}` | HTTP headers for authentication |
| `timeout` | `float` | `30.0` | Connection timeout in seconds |
| `tool_filter` | `list[str]` | `None` | Tools to expose (`None` = all) |
| `enabled` | `bool` | `True` | Whether the server is enabled |

### Tool Filtering

Limit which tools are exposed from a server:

```python
config = MCPServerConfig(
    command="npx",
    args=["-y", "@modelcontextprotocol/server-filesystem", "/path"],
    tool_filter=["read_file", "list_directory"],  # Only expose these tools
)
```

```bash
MCP__SERVERS='{"fs": {"command": "npx", "args": ["-y", "server"], "tool_filter": ["read_file", "write_file"]}}'
```

### Disabling Servers

Temporarily disable a server without removing its configuration:

```python
config = MCPServerConfig(
    command="npx",
    args=["-y", "some-server"],
    enabled=False,  # Server won't be initialized
)
```

## Using with ADK Agents

The MCP toolsets integrate seamlessly with Google ADK agents:

```python
from flare_ai_kit import FlareAIKit
from google.adk import Agent
from google.genai import types

async def create_agent_with_mcp():
    kit = FlareAIKit()

    # Get MCP toolsets
    mcp_toolsets = kit.mcp_tools

    # Combine with other tools
    all_tools = [
        *mcp_toolsets,  # MCP tools
        # ... your other ADK tools
    ]

    # Create ADK agent with MCP tools
    agent = Agent(
        model="gemini-2.5-flash",
        name="mcp-enabled-agent",
        instruction="You have access to filesystem and other MCP tools.",
        tools=all_tools,
    )

    return agent
```

## MCPManager API

### Getting Toolsets

```python
from flare_ai_kit.mcp.manager import MCPManager
from flare_ai_kit.mcp.settings import MCPSettings

# Create manager
settings = MCPSettings()  # Loads from environment
manager = MCPManager(settings)

# Get all toolsets (sync)
toolsets = manager.get_toolsets_sync()

# Get all toolsets (async)
toolsets = await manager.get_toolsets()

# Get specific toolset by name
fs_toolset = manager.get_toolset("filesystem")
```

### Checking Configuration

```python
# Check if any servers are configured
if manager.has_servers:
    print("MCP servers configured")

# Get list of server names
print(f"Servers: {manager.server_names}")
```

### Error Handling

```python
# Get toolsets (errors are captured, not raised)
toolsets = manager.get_toolsets_sync()

# Check for initialization errors
errors = manager.get_errors()
for server_name, error in errors.items():
    print(f"Server {server_name} failed: {error}")
```

### Cleanup

```python
# Close all MCP connections
await manager.close()
```

## Error Handling

### ImportError for Missing Dependencies

```python
try:
    toolsets = manager.get_toolsets_sync()
except ImportError as e:
    print("MCP dependencies not installed. Run: pip install flare-ai-kit[mcp]")
```

### Server Configuration Errors

```python
from flare_ai_kit.mcp.settings import MCPServerConfig

# Invalid: both command and url specified
try:
    config = MCPServerConfig(command="echo", url="http://localhost:3000")
except ValueError as e:
    print(f"Configuration error: {e}")

# Invalid: neither command nor url specified
try:
    config = MCPServerConfig()
except ValueError as e:
    print(f"Configuration error: {e}")
```

### Connection Errors

```python
manager = MCPManager(settings)
toolsets = manager.get_toolsets_sync()

# Check which servers failed to initialize
errors = manager.get_errors()
if errors:
    for name, error in errors.items():
        print(f"Server '{name}' failed: {error}")

    # Successfully initialized servers still work
    print(f"Working servers: {len(toolsets)}")
```
