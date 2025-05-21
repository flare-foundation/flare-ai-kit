"""Base module for agent framework using Pydantic for type validation."""

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field


class Message(BaseModel):
    """Message model for conversation history."""

    role: str
    content: str
    timestamp: float | None = None


class AgentInput(BaseModel):
    """Input model for agent processing."""

    message: str
    context: Any | None = None


class AgentOutput(BaseModel):
    """Output model for agent responses."""

    response: str
    context: Any | None = None


class AgentBase(ABC, BaseModel):
    """
    Abstract base class for AI agents using Pydantic for strict type validation.

    Manages agent lifecycle and conversation history.
    """

    conversation_history: list[Message] = Field(default_factory=list)
    max_history: int = 10

    class Config:
        """Configuration for the agent base class."""

        arbitrary_types_allowed = True
        validate_assignment = True

    @abstractmethod
    def initialize(self, **kwargs: Any) -> None:
        """Initialize the agent with any required setup."""

    @abstractmethod
    def process_input(self, agent_input: AgentInput) -> AgentOutput:
        """Process input and return output."""

    @abstractmethod
    def update_context(self, context: Any) -> None:
        """Update the agent's context."""

    def add_message(self, message: Message) -> None:
        """Add a message to conversation history."""
        self.conversation_history.append(message)
        if len(self.conversation_history) > self.max_history:
            self.conversation_history.pop(0)

    def get_history(self) -> list[Message]:
        """Get the conversation history."""
        return self.conversation_history
