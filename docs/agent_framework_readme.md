# Agent Framework - Flare AI Kit

The Agent Framework provides a robust foundation for building AI agents that can interact with the Flare blockchain ecosystem. Built on top of PydanticAI and Google Gemini, it offers type-safe, conversation-aware agents with extensible capabilities.

## Features

- **Type-Safe Architecture**: Built with Pydantic models for strict type validation
- **Conversation Management**: Automatic conversation history tracking and context management
- **Google Gemini Integration**: Native support for Google Gemini LLM via PydanticAI
- **Extensible Design**: Abstract base classes for creating specialized agents
- **Streaming Support**: Real-time response streaming capabilities
- **Embedding Generation**: Support for generating text embeddings
- **Lifecycle Management**: Clear initialization and setup patterns
- **Comprehensive Testing**: Full unit test coverage with mocked dependencies

## Quick Start

### Basic Usage

```python
import asyncio
from flare_ai_kit.agent import GeminiAgent, AgentSettings

async def main():
    # Configure settings (set AGENT__GEMINI_API_KEY environment variable)
    settings = AgentSettings()
  
    # Create and initialize agent
    agent = GeminiAgent(
        agent_id="my-agent-001",
        agent_name="My Assistant",
        system_prompt="You are a helpful AI assistant.",
        settings=settings
    )
  
    await agent.initialize()
  
    # Have a conversation
    response = await agent.process_input("Hello! How are you?")
    print(response.content)
  
    # Continue conversation (history is automatically managed)
    response2 = await agent.process_input("Can you help me with Python?")
    print(response2.content)

asyncio.run(main())
```

### Environment Setup

Set your Gemini API key:

```bash
export AGENT__GEMINI_API_KEY="your-gemini-api-key"
```

Get your API key from: https://aistudio.google.com/app/apikey

## Core Components

### BaseAgent

The abstract base class that defines the agent interface:

```python
from flare_ai_kit.agent import BaseAgent, AgentResponse

class MyCustomAgent(BaseAgent):
    async def _setup(self):
        # Initialize your agent-specific resources
        pass
  
    async def _generate_response(self, user_input: str, **kwargs) -> AgentResponse:
        # Implement your response generation logic
        return AgentResponse(
            content="My response",
            agent_id=self.agent_id
        )
```

### GeminiAgent

Production-ready agent implementation using Google Gemini:

```python
from flare_ai_kit.agent import GeminiAgent

agent = GeminiAgent(
    agent_id="gemini-agent",
    agent_name="Gemini Assistant",
    model_name="gemini-2.5-flash",  # or "gemini-2.5-pro"
    temperature=0.7,
    max_tokens=1000
)
```

### Key Classes

- **`AgentContext`**: Holds agent state, conversation history, and metadata
- **`ConversationMessage`**: Immutable message objects with role, content, and timestamp
- **`AgentResponse`**: Response objects with content, metadata, and usage information
- **`AgentSettings`**: Configuration management with environment variable support

## Advanced Features

### Conversation History Management

```python
# Get conversation history
history = agent.get_conversation_history(limit=10, role_filter="user")

# Clear history
agent.clear_history()

# Manual history management
from flare_ai_kit.agent.base import ConversationMessage
message = ConversationMessage(role="user", content="Hello")
agent._add_to_history(message)
```

### Custom Data Storage: TO be extended later

```python
# Store custom data
agent.add_custom_data("user_preferences", {"language": "Python"})
agent.add_custom_data("session_id", "abc123")

# Retrieve custom data
preferences = agent.get_custom_data("user_preferences")
session_id = agent.get_custom_data("session_id", default="unknown")
```

### Streaming Responses

```python
async for chunk in agent.stream_response("Tell me a story"):
    print(chunk, end="", flush=True)
```

### Embedding Generation

```python
embeddings = await agent.generate_embedding("Text to embed")
print(f"Embedding dimension: {len(embeddings)}")
```

### Model Parameter Updates

```python
agent.update_model_parameters(
    temperature=0.9,
    max_tokens=2000,
    top_p=0.95
)
```

## Creating Specialized Agents

### Blockchain-Focused Agent

```python
class FlareBlockchainAgent(GeminiAgent):
    def __init__(self, *args, **kwargs):
        system_prompt = """You are a Flare blockchain expert with deep knowledge of 
        FTSO, FAssets, State Connector, and DeFi protocols."""
      
        kwargs.setdefault('system_prompt', system_prompt)
        super().__init__(*args, **kwargs)
  
    async def explain_flare_concept(self, concept: str) -> AgentResponse:
        prompt = f"Explain the Flare concept: {concept}"
        return await self.process_input(prompt)
```

### Code Review Agent

```python
class CodeReviewAgent(GeminiAgent):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('temperature', 0.3)  # More consistent for code review
        super().__init__(*args, **kwargs)
  
    async def review_code(self, code: str, language: str) -> AgentResponse:
        prompt = f"Review this {language} code:\n\n```{language}\n{code}\n```"
        return await self.process_input(prompt)
```

## Configuration

### Environment Variables

```bash
# Required
AGENT__GEMINI_API_KEY="your-api-key"

# Optional
AGENT__GEMINI_MODEL="gemini-2.5-flash"  # Default model
AGENT__OPENROUTER_API_KEY="your-openrouter-key"  # For OpenRouter support
```

### Settings Class

```python
from flare_ai_kit.agent import AgentSettings

settings = AgentSettings(
    gemini_api_key="your-api-key",
    gemini_model="gemini-2.5-pro"
)
```

## Testing

The framework includes comprehensive unit tests:

```bash
# Run agent tests
python -m pytest tests/unit/agent/ -v

# Run specific test file
python -m pytest tests/unit/agent/test_base_agent.py -v
python -m pytest tests/unit/agent/test_gemini_agent.py -v
```

### Test Coverage

- ✅ Agent initialization and lifecycle
- ✅ Conversation history management
- ✅ Message validation and immutability
- ✅ Context updates and custom data
- ✅ Error handling and edge cases
- ✅ Mocked Gemini API interactions
- ✅ Streaming and embedding functionality

## Examples

### Basic Agent Usage

See `examples/03_agent_framework_demo.py` for a complete basic example.

### Advanced Agent Patterns

See `examples/04_advanced_agent_framework.py` for:

- Specialized agent creation
- Agent collaboration patterns
- Conversation persistence
- Context management strategies

## API Reference

### BaseAgent Methods

- `initialize()` - Initialize the agent
- `process_input(input, **kwargs)` - Process user input and generate response
- `update_context(**updates)` - Update agent context
- `get_conversation_history(limit, role_filter)` - Get conversation history
- `clear_history()` - Clear conversation history
- `set_system_prompt(prompt)` - Update system prompt
- `add_custom_data(key, value)` - Add custom data
- `get_custom_data(key, default)` - Get custom data

### GeminiAgent Additional Methods

- `generate_embedding(text)` - Generate text embeddings
- `stream_response(input)` - Stream response generation
- `test_connection()` - Test Gemini API connection
- `update_model_parameters(**params)` - Update model parameters

### Properties

- `agent_id` - Agent unique identifier
- `agent_name` - Agent display name
- `is_initialized` - Initialization status
- `model_info` - Model configuration info

## Error Handling

```python
from flare_ai_kit.agent.base import AgentError

try:
    await agent.process_input("Hello")
except AgentError as e:
    print(f"Agent error: {e}")
```

## Best Practices

1. **Always initialize agents** before use with `await agent.initialize()`
2. **Handle AgentError exceptions** for robust error management
3. **Set appropriate max_history_length** based on your use case
4. **Use system prompts** to guide agent behavior
5. **Store session data** in custom_data for persistence
6. **Monitor usage_info** in responses for token consumption
7. **Use streaming** for long responses to improve user experience

## Integration with Flare AI Kit

The Agent Framework integrates seamlessly with other Flare AI Kit components:

- **RAG Systems**: Use agents to query and interact with RAG pipelines
- **Blockchain Data**: Integrate with FTSO, FAssets, and other Flare protocols
- **A2A Communication**: Enable agents to communicate with other agents
- **Data Ingestion**: Process and analyze ingested documents and data

## Contributing

When contributing to the Agent Framework:

1. Maintain type safety with Pydantic models
2. Add comprehensive unit tests for new functionality
3. Follow the async/await patterns consistently
4. Update this documentation for new features
5. Ensure compatibility with the existing agent interface

## License

This framework is part of the Flare AI Kit and is licensed under the Apache License 2.0.
