"""An enhanced implementation of the Coordinator interface."""

import asyncio
from typing import Any, override, Optional

from pydantic_ai import Agent

from flare_ai_kit.common import Prediction
from flare_ai_kit.consensus.coordinator.base import BaseCoordinator


class SimpleCoordinator(BaseCoordinator):
    """A coordinator that manages agent lifecycle, distribution, and roles."""

    def __init__(self) -> None:
        """Initializes the SimpleCoordinator."""
        self.agents: dict[str, dict[str, Any]] = {}
         # Format: {agent_id: {"agent": Agent, "role": str, "config": dict}}

    @override
    def add_agent(self, agent: Agent, role: str, config: Optional[dict] = None) -> None:
        """
        Adds an agent with a specific role and optional config.

        Args:
            agent: The AI agent instance.
            role: Role of the agent (e.g., "summarizer").
            config: Optional agent-specific configuration.
        """
        agent_id = f"{type(agent).__name__}_{len(self.agents)}"
        self.agents[agent_id] = {
            "agent" : agent,
            "role": role,
            "config": config or {}
        }

    def remove_agent(self, agent_id: str) -> None:
        """Removes an agent by ID."""
        if agent_id in self.agents:
            del self.agents[agent_id]
    
    async def start_agents(self) -> None:
        """Opptionally starts all agents if they define a start() coroutine."""
        for entry in self.agents.values():
            agent = entry["agent"]
            if hasattr(agent, "start") and asyncio.iscoroutinefunction(agent.start):
                await agent.start()

    async def stop_agents(self) -> None:
        """Optionally stops all agents if they define a stop() coroutine."""
        for entry in self.agents.values():
            agent = entry["agent"]
            if hasattr(agent, "stop") and asyncio.iscoroutinefunction(agent.stop):
                await agent.stop()

    def monitor_agents(self) -> list[dict[str, Any]]:
        """Returns basic agent info for monitoring."""
        return [
            {
                "agent_id": agent_id,
                "role": meta["role"],
                "status": getattr(meta["agent"], "status", "unknown")
            }
            for agent_id, meta in self.agents.items()
        ]

    @override
    async def distribute_task(self, task: str, role: Optional[str] = None) -> list[Any]:
        """
        Distributes a task to all or role-matching agents.

        Args:
            task: The task to distribute.
            role: If specified, only agents with this role will receive the task.

        Returns:
            A list of agent responses.
        """
        selected = [
            meta["agent"]
            for meta in self.agents.values()
            if role is None or meta["role"] == role
        ]

        tasks = [agent.run(task) for agent in selected]
        return await asyncio.gather(*tasks)

    @override
    async def process_results(self, predictions: list[Any]) -> list[Prediction]:
        """
        Processes raw outputs from agents.

        Args:
            predictions: Agent outputs.

        Returns:
            A list of Prediction objects.
        """
        processed: list[Prediction] = []
        agent_ids = list(self.agents.keys())
        for i, pred in enumerate(predictions):
            agent_id = agent_ids[i]
            processed.append(
                Prediction(
                    agent_id=agent_id,
                    prediction=str(pred),
                    confidence=1.0  # This can be made dynamic using config
                )
            )
        return processed
