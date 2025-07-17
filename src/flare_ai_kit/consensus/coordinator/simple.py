"""An enhanced implementation of the Coordinator interface."""

import asyncio
from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic_ai import Agent

from flare_ai_kit.common import Prediction
from flare_ai_kit.consensus.coordinator.base import BaseCoordinator


@dataclass
class CoordinatorAgent:
    """Represents an agent managed by the coordinator."""

    agent_id: str
    agent: Agent
    role: Literal["user", "system", "assistant", "summarizer", "critic"]
    config: dict[str, Any] = field(default_factory=dict)

    @property
    def status(self) -> str:
        """Returns the status of the agent."""
        return getattr(self.agent, "status", "unknown")


class SimpleCoordinator(BaseCoordinator):
    """A coordinator that manages agent lifecycle, distribution, and roles."""

    def __init__(self) -> None:
        self.agents: dict[str, CoordinatorAgent] = {}

    def add_agent(self, agent: Agent, role: str, config: dict | None = None) -> None:
        """
        Adds an agent with a specific role and optional config.

        Args:
            agent: The AI agent instance.
            role: Role of the agent (e.g., "summarizer").
            config: Optional agent-specific configuration.

        """
        agent_id = f"{type(agent).__name__}_{len(self.agents)}"
        self.agents[agent_id] = CoordinatorAgent(
            agent_id=agent_id, agent=agent, role=role, config=config or {}
        )

    def remove_agent(self, agent_id: str) -> None:
        """Removes an agent by ID."""
        self.agents.pop(agent_id, None)

    async def start_agents(self) -> None:
        """Optionally starts all agents if they define a start() coroutine."""
        for a in self.agents.values():
            if hasattr(a.agent, "start") and asyncio.iscoroutinefunction(a.agent.start):
                await a.agent.start()

    async def stop_agents(self) -> None:
        """Optionally stops all agents if they define a stop() coroutine."""
        for a in self.agents.values():
            if hasattr(a.agent, "stop") and asyncio.iscoroutinefunction(a.agent.stop):
                await a.agent.stop()

    def monitor_agents(self) -> list[dict[str, str | Any]]:
        """Returns basic agent info for monitoring."""
        return [
            {"agent_id": a.agent_id, "role": a.role, "status": a.status}
            for a in self.agents.values()
        ]

    async def distribute_task(
        self, task: str, role: str | None = None
    ) -> list[tuple[str, Any]]:
        """
        Distributes a task to all or role-matching agents.

        Returns:
            A list of tuples (agent_id, result)

        """
        selected_agents = [
            (a.agent_id, a.agent)
            for a in self.agents.values()
            if role is None or a.role == role
        ]

        results = await asyncio.gather(
            *[agent.run(task) for _, agent in selected_agents]
        )

        return list(
            zip(
                [agent_id for agent_id, _ in selected_agents],
                results,
                strict=False,
            )
        )

    async def process_results(self, results: list[tuple[str, Any]]) -> list[Prediction]:
        """Processes a list of (agent_id, result) into Prediction objects."""
        predictions: list[Prediction] = []

        for agent_id, result in results:
            prediction_value = (
                float(result) if isinstance(result, (int, float)) else str(result)
            )

            # Optional: make confidence dynamic from config
            confidence = self.agents[agent_id].config.get("confidence", 1.0)

            predictions.append(
                Prediction(
                    agent_id=agent_id,
                    prediction=prediction_value,
                    confidence=confidence,
                )
            )

        return predictions
