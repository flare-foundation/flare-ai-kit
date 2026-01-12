"""Implementation of communication channels for inter-agent communication."""

import asyncio
import inspect
import time
import uuid
from collections import defaultdict
from collections.abc import Callable
from typing import Any

from flare_ai_kit.consensus.communication.base import (
    AgentMessage,
    BaseCommunicationChannel,
    BaseEventBus,
    MessageType,
)


class InMemoryChannel(BaseCommunicationChannel):
    """In-memory implementation of communication channel."""

    def __init__(self, max_queue_size: int = 1000) -> None:
        self.max_queue_size = max_queue_size
        self.message_queues: dict[str, list[AgentMessage]] = defaultdict(list)
        self.subscriptions: dict[str, set[MessageType]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def send_message(self, message: AgentMessage) -> bool:
        """Send a message to a specific agent."""
        async with self._lock:
            if message.recipient_id is None:
                return await self.broadcast_message(message)

            queue = self.message_queues[message.recipient_id]
            if len(queue) >= self.max_queue_size:
                # Remove oldest message to make room
                queue.pop(0)
            queue.append(message)
            return True

    async def receive_messages(self, agent_id: str) -> list[AgentMessage]:
        """Receive all pending messages for an agent."""
        async with self._lock:
            messages = self.message_queues[agent_id].copy()
            self.message_queues[agent_id].clear()

            # Filter by subscriptions
            subscribed_types = self.subscriptions[agent_id]
            if subscribed_types:
                messages = [m for m in messages if m.message_type in subscribed_types]

            return messages

    async def broadcast_message(self, message: AgentMessage) -> bool:
        """Broadcast a message to all subscribed agents."""
        async with self._lock:
            for agent_id, subscribed_types in self.subscriptions.items():
                if not subscribed_types or message.message_type in subscribed_types:
                    queue = self.message_queues[agent_id]
                    if len(queue) >= self.max_queue_size:
                        queue.pop(0)
                    queue.append(message)
            return True

    async def subscribe(self, agent_id: str, message_types: list[MessageType]) -> None:
        """Subscribe an agent to specific message types."""
        async with self._lock:
            self.subscriptions[agent_id].update(message_types)

    async def unsubscribe(self, agent_id: str) -> None:
        """Unsubscribe an agent from all message types."""
        async with self._lock:
            self.subscriptions.pop(agent_id, None)
            self.message_queues.pop(agent_id, None)


class EventBus(BaseEventBus):
    """Event bus implementation for agent coordination."""

    def __init__(self) -> None:
        self.handlers: dict[str, dict[str, Callable[..., Any]]] = defaultdict(dict)
        self._lock = asyncio.Lock()

    async def publish_event(self, event_type: str, data: dict[str, Any]) -> None:
        """Publish an event to all subscribed handlers."""
        async with self._lock:
            handlers = self.handlers[event_type].copy()

        # Execute handlers concurrently
        if handlers:
            tasks: list[Any] = []
            for handler in handlers.values():
                if inspect.iscoroutinefunction(handler):
                    tasks.append(handler(data))
                else:
                    # For non-async handlers, run in thread pool
                    tasks.append(
                        asyncio.get_event_loop().run_in_executor(None, handler, data)
                    )

            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

    async def subscribe_to_event(
        self, event_type: str, handler: Callable[..., Any], agent_id: str
    ) -> None:
        """Subscribe to a specific event type."""
        async with self._lock:
            self.handlers[event_type][agent_id] = handler

    async def unsubscribe_from_event(self, event_type: str, agent_id: str) -> None:
        """Unsubscribe from an event type."""
        async with self._lock:
            self.handlers[event_type].pop(agent_id, None)


class CommunicationManager:
    """Manager for coordinating communication between agents."""

    def __init__(
        self,
        channel: BaseCommunicationChannel | None = None,
        event_bus: BaseEventBus | None = None,
    ) -> None:
        self.channel = channel or InMemoryChannel()
        self.event_bus = event_bus or EventBus()
        self.active_agents: set[str] = set()

    async def register_agent(self, agent_id: str) -> None:
        """Register an agent with the communication system."""
        self.active_agents.add(agent_id)
        await self.channel.subscribe(agent_id, list(MessageType))

    async def unregister_agent(self, agent_id: str) -> None:
        """Unregister an agent from the communication system."""
        self.active_agents.discard(agent_id)
        await self.channel.unsubscribe(agent_id)

    async def send_prediction(
        self,
        sender_id: str,
        prediction: Any,
        confidence: float,
        task_id: str | None = None,
    ) -> bool:
        """Send a prediction to other agents."""
        message = AgentMessage(
            message_id=str(uuid.uuid4()),
            sender_id=sender_id,
            message_type=MessageType.PREDICTION,
            content={
                "prediction": prediction,
                "confidence": confidence,
                "task_id": task_id,
            },
            timestamp=time.time(),
        )
        return await self.channel.broadcast_message(message)

    async def request_collaboration(
        self,
        requester_id: str,
        target_id: str,
        task_description: str,
        collaboration_type: str = "peer_review",
    ) -> bool:
        """Request collaboration from another agent."""
        message = AgentMessage(
            message_id=str(uuid.uuid4()),
            sender_id=requester_id,
            recipient_id=target_id,
            message_type=MessageType.COLLABORATION_REQUEST,
            content={
                "task_description": task_description,
                "collaboration_type": collaboration_type,
            },
            timestamp=time.time(),
            requires_response=True,
        )
        return await self.channel.send_message(message)

    async def send_peer_review(
        self,
        reviewer_id: str,
        target_id: str,
        original_prediction: Any,
        review_comments: str,
        suggested_changes: dict[str, Any] | None = None,
    ) -> bool:
        """Send peer review feedback."""
        message = AgentMessage(
            message_id=str(uuid.uuid4()),
            sender_id=reviewer_id,
            recipient_id=target_id,
            message_type=MessageType.PEER_REVIEW,
            content={
                "original_prediction": original_prediction,
                "review_comments": review_comments,
                "suggested_changes": suggested_changes or {},
            },
            timestamp=time.time(),
        )
        return await self.channel.send_message(message)

    async def get_agent_messages(self, agent_id: str) -> list[AgentMessage]:
        """Get all pending messages for an agent."""
        return await self.channel.receive_messages(agent_id)

    async def publish_consensus_reached(
        self,
        task_id: str,
        final_prediction: Any,
        participating_agents: list[str],
        confidence: float,
    ) -> None:
        """Publish event when consensus is reached."""
        await self.event_bus.publish_event(
            "consensus_reached",
            {
                "task_id": task_id,
                "final_prediction": final_prediction,
                "participating_agents": participating_agents,
                "confidence": confidence,
                "timestamp": time.time(),
            },
        )
