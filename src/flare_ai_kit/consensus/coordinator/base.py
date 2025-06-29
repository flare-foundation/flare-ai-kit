"""Base coordinator interface for the consensus engine."""

from abc import ABC, abstractmethod
from typing import Any

from pydantic_ai import Agent


class BaseCoordinator(ABC):
    """Base coordinator class."""

    @abstractmethod
    def add_agent(self, agent: Agent, role: str) -> None:
        """Add an agent and its role to the pool."""

    @abstractmethod
    def remove_agent(self, agent_id: str) -> None:
        """Remove an agent from the pool."""
    
    @abstractmethod
    async def start_agents(self) -> None:
        """Start all agents in the pool."""

    @abstractmethod
    async def stop_agents(self) -> None:
        """Stop all agents in the pool."""

    @abstractmethod
    def monitor_agents(self) -> list[dict[str, Any]]:
        """Monitor agents in the pool."""

    @abstractmethod
    async def distribute_task(self, task: str) -> list[Any]:
        """Send given task to agents and return their predictions."""

    @abstractmethod
    async def process_results(self, predictions: list[Any]) -> Any:
        """Process model results."""
