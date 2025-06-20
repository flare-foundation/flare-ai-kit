"""A simple implementation of the Coordinator interface."""

import asyncio
from typing import Any, override

from pydantic_ai import Agent

from flare_ai_kit.common import Prediction
from flare_ai_kit.consensus.coordinator.base import BaseCoordinator


class SimpleCoordinator(BaseCoordinator):
    """A simple coordinator that distributes a task to all agents."""

    def __init__(self) -> None:
        """Initializes the SimpleCoordinator."""
        self.agents: list[tuple[Agent, str]] = []

    @override
    def add_agent(self, agent: Agent, role: str) -> None:
        """Adds an agent to the coordinator's pool."""
        self.agents.append((agent, role))

    @override
    async def distribute_task(self, task: str) -> list[Any]:
        """
        Distributes a task to all agents and collects their predictions.

        Args:
            task: The task to be distributed to the agents.

        Returns:
            A list of predictions from the agents.

        """
        tasks = [agent.run(task) for agent, _ in self.agents]
        return await asyncio.gather(*tasks)

    @override
    async def process_results(self, predictions: list[Any]) -> list[Prediction]:
        """
        Processes the raw results from agents into a structured Prediction format.

        Args:
            predictions: A list of raw outputs from the agents.

        Returns:
            A list of Prediction objects.

        """
        processed: list[Prediction] = []
        for i, pred in enumerate(predictions):
            agent, _ = self.agents[i]
            # Assuming agent has a unique identifier, like its class name or an ID
            # For simplicity, we use the index as a unique agent_id here.
            # A more robust solution might involve agent-specific identifiers.
            processed.append(
                Prediction(
                    agent_id=f"agent_{i}_{agent.__class__.__name__}",
                    prediction=str(pred),  # Ensure prediction is a string or float
                    confidence=1.0,  # Default confidence
                )
            )
        return processed
