"""Unit tests for base agent module."""

from typing import Any

import pytest
from pydantic import ValidationError

from flare_ai_kit.agent.base import AgentBase, AgentInput, AgentOutput, Message


class TestAgent(AgentBase):
    """Test implementation of AgentBase."""

    initialized: bool = False
    context: Any = None

    def initialize(self, **kwargs: Any) -> None:
        """Initialize the test agent."""
        self.initialized = True

    def process_input(self, agent_input: AgentInput) -> AgentOutput:
        """Process input and return echo response."""
        return AgentOutput(response=f"Echo: {agent_input.message}")

    def update_context(self, context: Any) -> None:
        """Update test agent context."""
        self.context = context


def test_message_creation():
    """Test Message model creation."""
    message = Message(role="user", content="Hello")
    assert message.role == "user"
    assert message.content == "Hello"


def test_agent_input_creation():
    """Test AgentInput model creation."""
    agent_input = AgentInput(message="Hello")
    assert agent_input.message == "Hello"


def test_agent_output_creation():
    """Test AgentOutput model creation."""
    agent_output = AgentOutput(response="Hi", context={"key": "value"})
    assert agent_output.response == "Hi"
    assert agent_output.context == {"key": "value"}


def test_agent_base_initialization():
    """Test AgentBase initialization."""
    agent = TestAgent()
    assert len(agent.conversation_history) == 0
    assert agent.max_history == 10


def test_agent_initialization():
    """Test agent initialization."""
    agent = TestAgent()
    agent.initialize()
    assert agent.initialized


def test_agent_process_input():
    """Test agent input processing."""
    agent = TestAgent()
    agent_input = AgentInput(message="Hello")
    output = agent.process_input(agent_input)
    assert output.response == "Echo: Hello"


def test_agent_context_update():
    """Test agent context update."""
    agent = TestAgent()
    context = {"key": "value"}
    agent.update_context(context)
    assert agent.context == context


def test_conversation_history():
    """Test conversation history management."""
    agent = TestAgent()
    message1 = Message(role="user", content="Hello")
    message2 = Message(role="agent", content="Hi")
    agent.add_message(message1)
    agent.add_message(message2)
    history = agent.get_history()
    assert len(history) == 2
    assert history[0] == message1
    assert history[1] == message2


def test_max_history_limit():
    """Test maximum history limit."""
    agent = TestAgent()
    agent.max_history = 2
    for i in range(3):
        agent.add_message(Message(role="user", content=f"Message {i}"))
    history = agent.get_history()
    assert len(history) == 2
    assert history[0].content == "Message 1"
    assert history[1].content == "Message 2"


def test_pydantic_validation():
    with pytest.raises(ValidationError):
        Message(role=123, content="bad")
