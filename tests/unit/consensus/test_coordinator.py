from __future__ import annotations

from typing import Any

import pytest

from flare_ai_kit.consensus.coordinator.simple import SimpleCoordinator


# ---------------------------------------------------------------------------
# Dummy Agent
# ---------------------------------------------------------------------------
class DummyAgent:
    """
    Minimal async agent used for testing SimpleCoordinator.
    Simulates start/stop/run behavior with internal flags.
    """

    def __init__(self, name: str, status: str = "idle") -> None:
        self.name: str = name
        self.status: str = status
        self.started: bool = False
        self.stopped: bool = False

    async def run(self, task: str) -> str:
        return f"{self.name} did {task}"

    async def start(self) -> None:
        self.started = True
        self.status = "running"

    async def stop(self) -> None:
        self.stopped = True
        self.status = "stopped"


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_add_and_monitor_agents() -> None:
    coordinator = SimpleCoordinator()
    agent = DummyAgent("agent1")

    coordinator.add_agent(agent, role="summarizer")
    agents: list[dict[str, Any]] = coordinator.monitor_agents()

    assert len(agents) == 1
    assert agents[0]["role"] == "summarizer"
    assert agents[0]["status"] == "idle"


@pytest.mark.asyncio
async def test_remove_agent() -> None:
    coordinator = SimpleCoordinator()
    agent = DummyAgent("agent2")
    coordinator.add_agent(agent, role="filter")
    agent_id = next(iter(coordinator.agents.keys()))

    coordinator.remove_agent(agent_id)
    assert agent_id not in coordinator.agents


@pytest.mark.asyncio
async def test_distribute_task_all_agents() -> None:
    coordinator = SimpleCoordinator()
    coordinator.add_agent(DummyAgent("a1"), role="summarizer")
    coordinator.add_agent(DummyAgent("a2"), role="summarizer")

    results: list[tuple[str, str]] = await coordinator.distribute_task("analyze data")
    assert len(results) == 2
    assert all("analyze data" in r[1] for r in results)


@pytest.mark.asyncio
async def test_distribute_task_by_role() -> None:
    coordinator = SimpleCoordinator()
    coordinator.add_agent(DummyAgent("a1"), role="summarizer")
    coordinator.add_agent(DummyAgent("a2"), role="filter")

    results: list[tuple[str, str]] = await coordinator.distribute_task(
        "summarize this", role="summarizer"
    )
    assert len(results) == 1
    assert "summarize this" in results[0][1]


@pytest.mark.asyncio
async def test_start_and_stop_agents() -> None:
    coordinator = SimpleCoordinator()
    agent = DummyAgent("a1")
    coordinator.add_agent(agent, role="summarizer")

    await coordinator.start_agents()
    await coordinator.stop_agents()

    assert agent.started
    assert agent.stopped
    assert agent.status == "stopped"
