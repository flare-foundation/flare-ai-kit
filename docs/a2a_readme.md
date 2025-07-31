# Flare AI Kit A2A Package

This package builds A2A (Agent-to-Agent) functionality into the Flare AI Kit. It consists of two main modules, a client and a server, that enable agents to communicate with each other over HTTP JSON-RPC 2.0. The package exposes A2A schemas following the v0.2.3 protocol spec.

## Using the client

The `A2AClient` class provides functionality to discover and communicate with A2A agents. It handles task management, agent discovery, and message routing.

### Basic Usage

Below is an example of the agent client in use to immediately send a request (POST request) to an A2A server at localhost:4500.

```python
from flare_ai_kit.a2a import A2AClient
from flare_ai_kit.a2a.schemas import (
    SendMessageRequest,
    MessageSendParams,
    Message,
    TextPart,
)

# Initialize the client
client = A2AClient(db_path="client.db")

# Send a message
message = SendMessageRequest(
    params=MessageSendParams(
        message=Message(
            role="user",
            parts=[TextPart(text="Get prices for BTC")],
            messageId="unique-message-id",
        )
    )
)

response = await client.send_message("http://localhost:4500", message)
```

The request body, when translated to JSON will resemble:

```json
{
  "id": "msg-1752087150006-n5ew0xs8q",
  "jsonrpc": "2.0",
  "method": "message/send",
  "params": {
    "message": {
      "kind": "message",
      "messageId": "21606816-a826-4f51-801e-3eb72dce678a",
      "parts": [
        {
          "kind": "text",
          "text": "Get prices for BTC"
        }
      ],
      "role": "user"
    }
  }
}
```

Below is an example response body from the agent:

```json
{
  "jsonrpc": "2.0",
  "id": "0dacbeeed6a842d0ad6d2d31ce3150f4",
  "result": {
    "kind": "message",
    "role": "agent",
    "parts": [
      {
        "kind": "text",
        "text": "The price of BTC/USD is 111184.22.",
        "metadata": null
      }
    ],
    "metadata": null,
    "messageId": "98698e9607444cd0a4d26f52c11feec5",
    "contextId": null,
    "taskId": null
  },
  "error": null
}
```

### Agent Discovery

The client can discover multiple agents by fetching their agent cards from the `/.well-known/agent.json` endpoint. This does not mean the library chooses what agent is called per message. Each message must still specify the agent base url. The discovery mechanism allows you to index the skills of your added agents so that you can, based on runtime search, choose and agent to send a request to, similar to an orchestrator.

```python
# Discover agents and their capabilities
await client.discover([
    "http://localhost:4500",
    "http://localhost:4501",
])

# Access discovered agent cards
for url, card in client.agent_cards.items():
    print(f"Agent: {card.name}")
    print(f"Description: {card.description}")
    for skill in card.skills:
        print(f"  - {skill.name}: {skill.description}")
```

### Skill-Based Routing

The client automatically builds a skill knowledge base from discovered agents:

```python
# Get all available skills
print("Available skills:")
for skill in client.available_skills:
    print(f"- {skill.name}: {skill.description}")

# Find agents that have a specific skill
agents_with_skill = client.skill_to_agents.get("price_analysis", [])
```

### Task Management

The client tracks tasks and their status:

```python
# Check task status
task_status = client.get_task_status("task-id")

# Cancel a task
success = client.cancel_task("task-id")
```

## Using the server

The `A2AServer` class provides a FastAPI-based server that exposes agent functionality via HTTP endpoints.

### Basic Server Setup

```python
from flare_ai_kit.a2a import A2AServer
from flare_ai_kit.a2a.schemas import (
    AgentCard,
    AgentCapabilities,
    AgentProvider,
    AgentSkill,
    SendMessageRequest,
    SendMessageResponse,
    Message,
    TextPart,
)

# Create agent card
card = AgentCard(
    name="My Agent",
    version="1.0.0",
    url="http://localhost:4500",
    description="A simple agent",
    provider=AgentProvider(
        organization="My Organization",
        url="https://example.com"
    ),
    capabilities=AgentCapabilities(
        streaming=False,
        pushNotifications=False
    ),
    skills=[
        AgentSkill(
            id="greeting",
            name="Greeting",
            description="Greets users",
            tags=["greeting", "hello"],
            examples=["Hello", "Hi there"],
            inputModes=["text/plain"],
            outputModes=["text/plain"],
        )
    ],
)

# Create server
server = A2AServer(card, host="localhost", port=4500)

# Add message handler
async def handle_message(request: SendMessageRequest):
    # Process the message
    user_text = "".join(
        part.text for part in request.params.message.parts
        if part.kind == "text"
    )

    # Generate response
    return SendMessageResponse(
        result=Message(
            messageId="response-id",
            role="agent",
            parts=[TextPart(text=f"You said: {user_text}")],
        )
    )

server.service.add_handler(SendMessageRequest, handle_message)

# Run the server
server.run()
```

### Service Handlers

The server uses a service-based architecture where you register handlers for different request types:

```python
# Handler for message sending
server.service.add_handler(SendMessageRequest, handle_send_message)

# Handler for task queries
server.service.add_handler(GetTaskRequest, handle_get_task)

# Handler for task cancellation
server.service.add_handler(CancelTaskRequest, handle_cancel_task)
```

### Agent Card Endpoint

The server automatically exposes the agent card at `/.well-known/agent.json`:

```bash
curl http://localhost:4500/.well-known/agent.json
```

## Storage support/Task Management

The A2A package includes robust task management with SQLite-based persistence through the `TaskManager` class.

### Task States

Tasks can be in one of several states:

- `submitted`: Task has been submitted
- `working`: Task is being processed
- `input_required`: Task needs additional input
- `completed`: Task has completed successfully
- `canceled`: Task was canceled
- `failed`: Task failed to complete
- `unknown`: Task state is unknown
- `rejected`: Task was rejected

### Task Management Features

```python
from flare_ai_kit.a2a.task_management import TaskManager

# Initialize task manager
task_manager = TaskManager(db_path="tasks.db")

# Create a new task
task = task_manager.create_task("task-123")

# Update task status
task_manager.update_task_status("task-123", TaskStatus(state=TaskState.working))

# Cancel a task
success = task_manager.cancel_task("task-123")

# Check if task is cancelled
is_cancelled = task_manager.is_cancelled("task-123")
```

### Database Schema

Tasks are stored in SQLite with the following schema:

```sql
CREATE TABLE tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    remote_task_id TEXT UNIQUE NOT NULL,
    status TEXT NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

## Streaming support (not yet implemented)

Streaming support is planned for future releases. The infrastructure is in place with:

- `StreamMessageRequest` schema defined
- `SendStreamingMessageResponse` for streaming responses
- `TaskStatusUpdateEvent` and `TaskArtifactUpdateEvent` for real-time updates
- Agent capabilities can declare `streaming: true`

When implemented, streaming will allow:

- Real-time message streaming
- Progressive task updates
- Artifact streaming for large responses

## Push notification support (not yet implemented)

Push notification support is planned for future releases. The foundation includes:

- `PushNotificationConfig` schema for webhook configuration
- `SetTaskPushNotificationRequest` and `GetTaskPushNotificationRequest` for managing notifications
- Agent capabilities can declare `pushNotifications: true`
- Authentication schemes for secure webhook delivery

When implemented, push notifications will enable:

- Webhook-based task status updates
- Asynchronous result delivery
- Real-time event notifications

## Polling (not yet implemented)

Polling support is planned as an alternative to push notifications. This will include:

- Configurable polling intervals
- Batch status updates
- Efficient change detection
- Fallback mechanism when webhooks are not available

## Examples

### Complete Agent Collaboration Example

See the examples in the `examples/a2a/a2a_collaboration/` directory for a complete implementation featuring:

- **Orchestrator Agent**: Breaks down complex queries into subtasks and routes them to appropriate agents
- **FTSO Agent**: Fetches cryptocurrency prices using the Flare FTSO system
- **Price Analysis Agent**: Analyzes price data against historical trends

### Simple Ping-Pong Example

See `examples/a2a/messaging/ping_pong.py` for a basic client-server interaction example.
