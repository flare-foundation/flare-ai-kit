"""Base Agent class for Flare AI Kit using PydanticAI."""

from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import Any

import structlog
from pydantic import BaseModel, ConfigDict, Field

from ..common.exceptions import FlareAIKitError

logger = structlog.get_logger(__name__)


class AgentError(FlareAIKitError):
    """Exception raised for agent-related errors."""


class ConversationMessage(BaseModel):
    """A single message in the conversation history."""

    model_config = ConfigDict(frozen=True)

    role: str = Field(
        ..., description="The role of the message sender (user, assistant, system)"
    )
    content: str = Field(..., description="The content of the message")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata for the message"
    )


class AgentContext(BaseModel):
    """Context information for the agent."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    agent_id: str = Field(..., description="Unique identifier for the agent")
    agent_name: str = Field(..., description="Human-readable name for the agent")
    system_prompt: str = Field(default="", description="System prompt for the agent")
    conversation_history: list[ConversationMessage] = Field(
        default_factory=lambda: list[ConversationMessage](),
        description="Conversation history messages"
    )
    max_history_length: int = Field(
        default=50, description="Maximum number of messages to keep in history"
    )
    custom_data: dict[str, Any] = Field(
        default_factory=dict, description="Custom data for the agent"
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class AgentResponse(BaseModel):
    """Response from an agent."""

    model_config = ConfigDict(frozen=True)

    content: str = Field(..., description="The response content")
    agent_id: str = Field(
        ..., description="ID of the agent that generated the response"
    )
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata for the response"
    )
    usage_info: dict[str, Any] | None = Field(
        default=None, description="Token usage and other metrics"
    )


class BaseAgent(ABC):
    """
    Abstract base class for all agents in the Flare AI Kit.

    This class provides the foundational structure for creating AI agents
    with conversation history management, context handling, and lifecycle methods.
    """

    def __init__(
        self,
        agent_id: str,
        agent_name: str,
        system_prompt: str = "",
        max_history_length: int = 50,
        **kwargs: Any,
    ):
        """
        Initialize the base agent.

        Args:
            agent_id: Unique identifier for the agent
            agent_name: Human-readable name for the agent
            system_prompt: System prompt to guide agent behavior
            max_history_length: Maximum number of messages to keep in history
            **kwargs: Additional configuration parameters

        """
        self.context = AgentContext(
            agent_id=agent_id,
            agent_name=agent_name,
            system_prompt=system_prompt,
            max_history_length=max_history_length,
        )
        self._initialized = False
        self.logger = logger.bind(agent_id=agent_id, agent_name=agent_name)

    async def initialize(self) -> None:
        """
        Initialize the agent.

        This method should be called before using the agent.
        Subclasses can override this method to perform specific initialization.
        """
        if self._initialized:
            self.logger.warning("Agent already initialized")
            return

        self.logger.info("Initializing agent")
        await self._setup()
        self._initialized = True
        self.logger.info("Agent initialized successfully")

    @abstractmethod
    async def _setup(self) -> None:
        """Setup method to be implemented by subclasses."""

    async def process_input(
        self, user_input: str, include_history: bool = True, **kwargs: Any
    ) -> AgentResponse:
        """
        Process user input and generate a response.

        Args:
            user_input: The user's input message
            include_history: Whether to include conversation history in the context
            **kwargs: Additional parameters for processing

        Returns:
            AgentResponse containing the agent's response

        Raises:
            AgentError: If the agent is not initialized or processing fails

        """
        if not self._initialized:
            raise AgentError("Agent must be initialized before processing input")

        self.logger.info("Processing user input", input_length=len(user_input))

        try:
            # Add user message to history
            user_message = ConversationMessage(
                role="user",
                content=user_input,
                metadata=kwargs.get("input_metadata", {}),
            )

            # Generate response
            response = await self._generate_response(
                user_input=user_input, include_history=include_history, **kwargs
            )

            # Add messages to history
            self._add_to_history(user_message)

            assistant_message = ConversationMessage(
                role="assistant", content=response.content, metadata=response.metadata
            )
            self._add_to_history(assistant_message)

            # Update context timestamp
            self.update_context(updated_at=datetime.now(UTC))

            self.logger.info(
                "Successfully processed input", response_length=len(response.content)
            )
            return response

        except Exception as e:
            self.logger.error("Failed to process input", error=str(e))
            raise AgentError(f"Failed to process input: {e}") from e

    @abstractmethod
    async def _generate_response(
        self, user_input: str, include_history: bool = True, **kwargs: Any
    ) -> AgentResponse:
        """
        Generate a response to user input.

        This method must be implemented by subclasses to provide
        the actual response generation logic.
        """

    def update_context(self, **updates: Any) -> None:
        """
        Update the agent's context.

        Args:
            **updates: Key-value pairs to update in the context

        """
        # Create a new context with updates
        context_dict = self.context.model_dump()
        context_dict.update(updates)
        context_dict["updated_at"] = datetime.now(UTC)

        self.context = AgentContext(**context_dict)
        self.logger.debug("Context updated", updates=list(updates.keys()))

    def _add_to_history(self, message: ConversationMessage) -> None:
        """
        Add a message to the conversation history.

        Args:
            message: The message to add to history

        """
        history: list[ConversationMessage] = list(self.context.conversation_history)
        history.append(message)

        # Trim history if it exceeds max length
        if len(history) > self.context.max_history_length:
            history = history[-self.context.max_history_length :]

        self.update_context(conversation_history=history)

    def get_conversation_history(
        self, limit: int | None = None, role_filter: str | None = None
    ) -> list[ConversationMessage]:
        """
        Get the conversation history.

        Args:
            limit: Maximum number of messages to return
            role_filter: Filter messages by role (user, assistant, system)

        Returns:
            List of conversation messages

        """
        history = self.context.conversation_history

        if role_filter:
            history = [msg for msg in history if msg.role == role_filter]

        if limit:
            history = history[-limit:]

        return history

    def clear_history(self) -> None:
        """Clear the conversation history."""
        self.update_context(conversation_history=[])
        self.logger.info("Conversation history cleared")

    def set_system_prompt(self, prompt: str) -> None:
        """
        Set the system prompt for the agent.

        Args:
            prompt: The new system prompt

        """
        self.update_context(system_prompt=prompt)
        self.logger.info("System prompt updated")

    def add_custom_data(self, key: str, value: Any) -> None:
        """
        Add custom data to the agent context.

        Args:
            key: The key for the custom data
            value: The value to store

        """
        custom_data = dict(self.context.custom_data)
        custom_data[key] = value
        self.update_context(custom_data=custom_data)

    def get_custom_data(self, key: str, default: Any = None) -> Any:
        """
        Get custom data from the agent context.

        Args:
            key: The key for the custom data
            default: Default value if key not found

        Returns:
            The stored value or default

        """
        return self.context.custom_data.get(key, default)

    def _build_conversation_context(self) -> str:
        """
        Build conversation context as a string for the LLM.

        Returns:
            Formatted conversation history as a string

        """
        context_parts: list[str] = []

        # Add system prompt if present
        if self.context.system_prompt:
            context_parts.append(f"System: {self.context.system_prompt}")

        # Add conversation history
        for msg in self.context.conversation_history:
            context_parts.append(f"{msg.role.title()}: {msg.content}")

        return "\n".join(context_parts)

    @property
    def is_initialized(self) -> bool:
        """Check if the agent is initialized."""
        return self._initialized

    @property
    def agent_id(self) -> str:
        """Get the agent ID."""
        return self.context.agent_id

    @property
    def agent_name(self) -> str:
        """Get the agent name."""
        return self.context.agent_name

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(agent_id='{self.agent_id}', agent_name='{self.agent_name}')"
