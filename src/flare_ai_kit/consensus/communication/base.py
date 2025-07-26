"""Base communication interfaces for inter-agent communication."""

from abc import ABC, abstractmethod
from collections.abc import Callable
from enum import Enum
from typing import Any

try:
    from pydantic import BaseModel as _PydanticBaseModel

    class BaseModel(_PydanticBaseModel):  # type: ignore[misc]
        """Base model using pydantic."""

        class Config:
            """Pydantic configuration."""

            arbitrary_types_allowed = True

except ImportError:
    # Fallback for when pydantic is not available
    class BaseModel:  # type: ignore[misc]
        """Fallback BaseModel when pydantic is not available."""

        def __init__(self, **kwargs: Any) -> None:
            for key, value in kwargs.items():
                setattr(self, key, value)


class MessageType(str, Enum):
    """Types of messages exchanged between agents."""

    TASK_REQUEST = "task_request"
    PREDICTION = "prediction"
    CONFIDENCE_UPDATE = "confidence_update"
    CONFLICT_RESOLUTION = "conflict_resolution"
    STATUS_UPDATE = "status_update"
    COLLABORATION_REQUEST = "collaboration_request"
    PEER_REVIEW = "peer_review"


class MessagePriority(str, Enum):
    """Priority levels for message handling."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AgentMessage(BaseModel):  # type: ignore[misc]
    """Standard message format for inter-agent communication."""

    message_id: str
    sender_id: str
    recipient_id: str | None = None  # None for broadcast
    message_type: MessageType
    priority: MessagePriority = MessagePriority.MEDIUM
    content: dict[str, Any]
    timestamp: float
    requires_response: bool = False
    correlation_id: str | None = None  # For tracking related messages


class BaseCommunicationChannel(ABC):
    """Abstract base class for agent communication channels."""

    @abstractmethod
    async def send_message(self, message: AgentMessage) -> bool:
        """Send a message through the channel."""

    @abstractmethod
    async def receive_messages(self, agent_id: str) -> list[AgentMessage]:
        """Receive pending messages for an agent."""

    @abstractmethod
    async def broadcast_message(self, message: AgentMessage) -> bool:
        """Broadcast a message to all agents."""

    @abstractmethod
    async def subscribe(self, agent_id: str, message_types: list[MessageType]) -> None:
        """Subscribe an agent to specific message types."""

    @abstractmethod
    async def unsubscribe(self, agent_id: str) -> None:
        """Unsubscribe an agent from all message types."""


class BaseEventBus(ABC):
    """Abstract event bus for agent coordination."""

    @abstractmethod
    async def publish_event(self, event_type: str, data: dict[str, Any]) -> None:
        """Publish an event to the bus."""

    @abstractmethod
    async def subscribe_to_event(
        self, event_type: str, handler: Callable[..., Any], agent_id: str
    ) -> None:
        """Subscribe to a specific event type."""

    @abstractmethod
    async def unsubscribe_from_event(self, event_type: str, agent_id: str) -> None:
        """Unsubscribe from an event type."""
