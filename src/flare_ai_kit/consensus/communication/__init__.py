"""Communication module for inter-agent communication."""

from flare_ai_kit.consensus.communication.base import (
    AgentMessage,
    BaseCommunicationChannel,
    BaseEventBus,
    MessagePriority,
    MessageType,
)
from flare_ai_kit.consensus.communication.channels import (
    CommunicationManager,
    EventBus,
    InMemoryChannel,
)

__all__ = [
    "AgentMessage",
    "BaseCommunicationChannel",
    "BaseEventBus",
    "CommunicationManager",
    "EventBus",
    "InMemoryChannel",
    "MessagePriority",
    "MessageType",
]
