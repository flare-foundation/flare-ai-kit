from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from flare_ai_kit.common.schemas import Prediction
from flare_ai_kit.consensus.management.dynamic import (
    AgentPerformanceMetrics,
    DynamicInteractionManager,
    InteractionPattern,
    TaskComplexity,
)


@pytest.fixture
def manager():
    return DynamicInteractionManager()


@pytest.fixture
def fake_agent():
    """Minimal CoordinatorAgent-like mock with agent_id and async run."""
    mock = SimpleNamespace()
    mock.agent_id = "agent1"
    mock.config = {"confidence": 0.9}
    mock.agent = AsyncMock()
    mock.agent.run = AsyncMock(return_value="mock_prediction")
    return mock


@pytest.mark.asyncio
async def test_analyze_task_complexity_flags(manager):
    # should detect medical domain and expertise requirement
    c = await manager._analyze_task_complexity("urgent medical diagnosis")
    assert c.requires_expertise
    assert c.time_sensitive
    assert c.domain == "medical"
    assert 0 <= c.difficulty <= 1


@pytest.mark.asyncio
async def test_select_interaction_pattern_expert(manager, fake_agent):
    # metrics show fake_agent is a domain expert
    manager.agent_metrics[fake_agent.agent_id] = AgentPerformanceMetrics(
        agent_id=fake_agent.agent_id,
        domain_expertise={"medical": 0.9},
    )
    tc = TaskComplexity(domain="medical", requires_expertise=True)
    pattern, cfg = await manager.select_interaction_pattern(
        "analyze patient data", [fake_agent], tc
    )
    assert pattern == InteractionPattern.EXPERT_CONSULTATION
    assert "expert_agents" in cfg


@pytest.mark.asyncio
async def test_select_interaction_pattern_competitive(manager, fake_agent):
    tc = TaskComplexity(time_sensitive=True)
    agents = [fake_agent] * 4  # enough agents for competitive
    pattern, cfg = await manager.select_interaction_pattern("urgent task", agents, tc)
    assert pattern == InteractionPattern.COMPETITIVE
    assert "time_limit" in cfg


@pytest.mark.asyncio
async def test_coordinate_broadcast_returns_predictions(manager, fake_agent):
    preds = await manager._coordinate_broadcast([fake_agent], "some task", {})
    assert isinstance(preds, list)
    assert isinstance(preds[0], Prediction)
    assert preds[0].prediction == "mock_prediction"


@pytest.mark.asyncio
async def test_check_convergence(manager):
    preds = [
        Prediction(agent_id="a1", prediction="yes", confidence=0.9),
        Prediction(agent_id="a2", prediction="yes", confidence=0.9),
    ]
    assert manager._check_convergence(preds, 0.8)


@pytest.mark.asyncio
async def test_update_agent_performance(manager):
    manager.agent_metrics.clear()
    await manager.update_agent_performance(
        "agentX", {"accuracy": 0.8, "response_time": 0.2, "collaboration_rating": 0.7}
    )
    m = manager.agent_metrics["agentX"]
    assert m.accuracy_score > 0
    assert m.response_time_avg > 0
    assert m.collaboration_score > 0
    assert m.task_count == 1


@pytest.mark.asyncio
async def test_coordinate_hierarchical_grouping(manager, fake_agent):
    agents = [fake_agent, fake_agent, fake_agent]
    # ensure metrics exist so leader selection runs
    for a in agents:
        manager.agent_metrics[a.agent_id] = AgentPerformanceMetrics(agent_id=a.agent_id)
    preds = await manager._coordinate_hierarchical(
        agents, "group task", {"group_size": 2}
    )
    assert isinstance(preds, list)
    for p in preds:
        assert isinstance(p, Prediction)


@pytest.mark.asyncio
async def test_create_review_pairs(manager):
    class Dummy:
        def __init__(self, i):
            self.agent_id = f"a{i}"

    agents = [Dummy(i) for i in range(4)]
    pairs = manager._create_review_pairs(agents)
    assert all(len(pair) == 2 for pair in pairs)
