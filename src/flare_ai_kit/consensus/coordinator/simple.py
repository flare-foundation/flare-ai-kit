"""An enhanced implementation of the Coordinator interface."""

import asyncio
import inspect
from dataclasses import dataclass, field
from typing import Any

try:
    from pydantic_ai import Agent as _PydanticAgent  # type: ignore[import-untyped]

    Agent = _PydanticAgent  # type: ignore[misc]
except ImportError:
    # Fallback for when pydantic_ai is not available
    class Agent:  # type: ignore[misc]
        """Fallback Agent when pydantic_ai is not available."""

        def __init__(self, **kwargs: Any) -> None:
            for key, value in kwargs.items():
                setattr(self, key, value)


from flare_ai_kit.common import AgentRole, Prediction
from flare_ai_kit.consensus.coordinator.base import BaseCoordinator


@dataclass
class CoordinatorAgent:
    """Represents an agent managed by the coordinator."""

    agent_id: str
    agent: Any
    role: AgentRole
    config: dict[str, Any] = field(default_factory=lambda: dict[str, Any]())

    @property
    def status(self) -> str:
        """Returns the status of the agent."""
        return getattr(self.agent, "status", "unknown")  # type: ignore[arg-type]


class SimpleCoordinator(BaseCoordinator):
    """A coordinator that manages agent lifecycle, distribution, and roles."""

    def __init__(self) -> None:
        self.agents: dict[str, CoordinatorAgent] = {}

    def add_agent(
        self,
        agent: Any,
        role: AgentRole,  # Use AgentRole type
        config: dict[str, Any] | None = None,
    ) -> None:
        """
        Adds an agent with a specific role and optional config.

        Args:
            agent: The AI agent instance.
            role: Role of the agent (e.g., "summarizer").
            config: Optional agent-specific configuration.

        """
        agent_id = f"{type(agent).__name__}_{len(self.agents)}"
        self.agents[agent_id] = CoordinatorAgent(
            agent_id=agent_id,
            agent=agent,
            role=role,
            config=config or {},
        )

    def remove_agent(self, agent_id: str) -> None:
        """Removes an agent by ID."""
        self.agents.pop(agent_id, None)

    async def start_agents(self) -> None:
        """Starts all agents that define a `start()` coroutine."""
        for agent in self.agents.values():
            agent_start = getattr(agent.agent, "start", None)
            if agent_start is not None and inspect.iscoroutinefunction(agent_start):
                await agent_start()

    async def stop_agents(self) -> None:
        """Stops all agents that define a `stop()` coroutine."""
        for agent in self.agents.values():
            agent_stop = getattr(agent.agent, "stop", None)
            if agent_stop is not None and inspect.iscoroutinefunction(agent_stop):
                await agent_stop()

    def monitor_agents(self) -> list[dict[str, str | Any]]:
        """Returns a summary of agents' roles and statuses."""
        return [
            {"agent_id": a.agent_id, "role": a.role, "status": a.status}
            for a in self.agents.values()
        ]

    async def distribute_task(
        self, task: str, role: AgentRole | None = None
    ) -> list[tuple[str, Any]]:
        """
        Distributes a task to all or role-matching agents.

        Returns:
            A list of tuples (agent_id, result).

        """
        selected: list[tuple[str, Any]] = [
            (a.agent_id, a.agent)
            for a in self.agents.values()
            if role is None or a.role == role
        ]

        results: list[Any] = list(
            await asyncio.gather(*(agent.run(task) for _, agent in selected))
        )

        return list(zip((aid for aid, _ in selected), results, strict=False))

    async def process_results(
        self, predictions: list[tuple[str, Any]]
    ) -> list[Prediction]:
        """
        Processes a list of (agent_id, result) into Prediction objects.

        Returns:
            A list of structured `Prediction` objects.

        """
        predictions_list: list[Prediction] = []

        for agent_id, result in predictions:
            prediction_value = (
                float(result) if isinstance(result, (int, float)) else str(result)
            )
            confidence = self.agents[agent_id].config.get("confidence", 1.0)

            predictions_list.append(
                Prediction(
                    agent_id=agent_id,
                    prediction=prediction_value,
                    confidence=confidence,
                )
            )

        return predictions_list
