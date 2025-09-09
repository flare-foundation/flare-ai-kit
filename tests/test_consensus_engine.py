"""Comprehensive tests for the consensus engine functionality."""

import asyncio
from unittest.mock import AsyncMock, Mock

import pytest

from flare_ai_kit.common.schemas import Prediction
from flare_ai_kit.consensus import (
    ConsensusEngine,
    majority_vote,
    top_confidence,
    weighted_average,
)
from flare_ai_kit.consensus.aggregator.base import BaseAggregator
from flare_ai_kit.consensus.communication import (
    AgentMessage,
    CommunicationManager,
    EventBus,
    InMemoryChannel,
    MessagePriority,
    MessageType,
)
from flare_ai_kit.consensus.coordinator.simple import SimpleCoordinator
from flare_ai_kit.consensus.management import (
    DynamicInteractionManager,
    InteractionPattern,
)
from flare_ai_kit.consensus.resolution import (
    ConflictType,
    DomainConflictDetector,
    ExpertiseBasedResolver,
    HybridConflictResolver,
    StatisticalConflictDetector,
    WeightedVotingResolver,
)


class MockAgent:
    """Mock agent for testing."""

    def __init__(self, name: str, confidence: float = 0.8):
        self.name = name
        self.confidence = confidence
        self.status = "idle"
        self.started = False
        self.stopped = False

    async def run(self, task: str) -> str:
        """Simulate agent task execution."""
        await asyncio.sleep(0.01)  # Simulate processing time
        return f"{self.name}: {task} result"

    async def start(self):
        """Start the agent."""
        self.started = True
        self.status = "running"

    async def stop(self):
        """Stop the agent."""
        self.stopped = True
        self.status = "stopped"


@pytest.fixture
def mock_predictions():
    """Create mock predictions for testing."""
    return [
        Prediction(agent_id="agent1", prediction="A", confidence=0.9),
        Prediction(agent_id="agent2", prediction="B", confidence=0.7),
        Prediction(agent_id="agent3", prediction="A", confidence=0.8),
        Prediction(agent_id="agent4", prediction="C", confidence=0.6),
    ]


@pytest.fixture
def consensus_engine():
    """Create a consensus engine for testing."""
    coordinator = SimpleCoordinator()

    # Create a concrete aggregator implementation
    class ConcreteAggregator(BaseAggregator):
        def aggregate(self, predictions):
            return majority_vote(predictions)

    aggregator = ConcreteAggregator(majority_vote)
    return ConsensusEngine(coordinator=coordinator, aggregator=aggregator)


class TestAggregationStrategies:
    """Test aggregation strategies."""

    def test_majority_vote(self, mock_predictions):
        """Test majority vote aggregation."""
        result = majority_vote(mock_predictions)
        assert result.result == "A"  # A appears twice
        assert result.confidence > 0

    def test_top_confidence(self, mock_predictions):
        """Test top confidence aggregation."""
        result = top_confidence(mock_predictions)
        assert result.result == "A"  # Highest confidence (0.9)
        assert result.confidence == 0.9

    def test_weighted_average(self, mock_predictions):
        """Test weighted average aggregation."""
        # Test with numeric predictions
        numeric_predictions = [
            Prediction(result="5.0", confidence=0.9, agent_id="agent1"),
            Prediction(result="4.0", confidence=0.7, agent_id="agent2"),
            Prediction(result="6.0", confidence=0.8, agent_id="agent3"),
        ]
        result = weighted_average(numeric_predictions)
        assert isinstance(float(result.result), float)
        assert result.confidence > 0


class TestCommunication:
    """Test agent communication mechanisms."""

    @pytest.mark.asyncio
    async def test_in_memory_channel(self):
        """Test in-memory communication channel."""
        channel = InMemoryChannel("test_channel")

        message = AgentMessage(
            sender_id="agent1",
            receiver_id="agent2",
            message_type=MessageType.PREDICTION,
            content={"data": "test"},
            priority=MessagePriority.NORMAL,
        )

        await channel.send_message(message)
        received = await channel.receive_message("agent2")

        assert received is not None
        assert received.sender_id == "agent1"
        assert received.content["data"] == "test"

    @pytest.mark.asyncio
    async def test_event_bus(self):
        """Test event bus functionality."""
        event_bus = EventBus()
        received_events = []

        async def event_handler(event):
            received_events.append(event)

        await event_bus.subscribe("test_event", event_handler)
        await event_bus.publish("test_event", {"data": "test"})

        # Give time for event processing
        await asyncio.sleep(0.1)

        assert len(received_events) == 1
        assert received_events[0]["data"] == "test"

    @pytest.mark.asyncio
    async def test_communication_manager(self):
        """Test high-level communication management."""
        manager = CommunicationManager()

        # Create channel and send message
        await manager.create_channel("test_channel")

        message = AgentMessage(
            sender_id="agent1",
            receiver_id="agent2",
            message_type=MessageType.TASK_REQUEST,
            content={"task": "analyze"},
            priority=MessagePriority.HIGH,
        )

        await manager.send_message("test_channel", message)
        received = await manager.receive_message("test_channel", "agent2")

        assert received is not None
        assert received.content["task"] == "analyze"


class TestConflictResolution:
    """Test conflict detection and resolution."""

    def test_statistical_conflict_detector(self, mock_predictions):
        """Test statistical conflict detection."""
        detector = StatisticalConflictDetector()

        # Create predictions with high variance to trigger conflict
        high_variance_predictions = [
            Prediction(result="10.0", confidence=0.9, agent_id="agent1"),
            Prediction(result="1.0", confidence=0.8, agent_id="agent2"),
            Prediction(result="15.0", confidence=0.7, agent_id="agent3"),
        ]

        conflicts = detector.detect_conflicts(high_variance_predictions)
        assert len(conflicts) > 0
        assert conflicts[0].conflict_type == ConflictType.PREDICTION_VARIANCE

    def test_domain_conflict_detector(self, mock_predictions):
        """Test domain-specific conflict detection."""
        detector = DomainConflictDetector()
        conflicts = detector.detect_conflicts(mock_predictions)

        # Should detect conflicts due to different results
        assert len(conflicts) > 0

    @pytest.mark.asyncio
    async def test_weighted_voting_resolver(self, mock_predictions):
        """Test weighted voting conflict resolution."""
        resolver = WeightedVotingResolver()

        conflict_context = Mock()
        conflict_context.predictions = mock_predictions
        conflict_context.conflict_type = ConflictType.PREDICTION_DISAGREEMENT

        result = await resolver.resolve_conflict(conflict_context)
        assert result.success is True
        assert result.resolution is not None

    @pytest.mark.asyncio
    async def test_expertise_based_resolver(self, mock_predictions):
        """Test expertise-based conflict resolution."""
        resolver = ExpertiseBasedResolver()

        conflict_context = Mock()
        conflict_context.predictions = mock_predictions
        conflict_context.conflict_type = ConflictType.EXPERTISE_DISAGREEMENT

        result = await resolver.resolve_conflict(conflict_context)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_hybrid_conflict_resolver(self, mock_predictions):
        """Test hybrid conflict resolution."""
        voting_resolver = WeightedVotingResolver()
        expertise_resolver = ExpertiseBasedResolver()

        hybrid_resolver = HybridConflictResolver([voting_resolver, expertise_resolver])

        conflict_context = Mock()
        conflict_context.predictions = mock_predictions
        conflict_context.conflict_type = ConflictType.PREDICTION_DISAGREEMENT

        result = await hybrid_resolver.resolve_conflict(conflict_context)
        assert result.success is True


class TestDynamicInteractionManagement:
    """Test dynamic agent interaction management."""

    @pytest.mark.asyncio
    async def test_dynamic_interaction_manager(self):
        """Test dynamic interaction pattern selection."""
        manager = DynamicInteractionManager()

        # Create mock agents
        agents = [MockAgent(f"agent{i}") for i in range(3)]

        # Test different interaction patterns
        patterns = [
            InteractionPattern.BROADCAST,
            InteractionPattern.HIERARCHICAL,
            InteractionPattern.PEER_TO_PEER,
        ]

        for pattern in patterns:
            result = await manager.coordinate_agents(agents, "test_task", pattern)
            assert len(result) > 0
            assert all("test_task" in r for r in result)

    @pytest.mark.asyncio
    async def test_performance_tracking(self):
        """Test agent performance tracking."""
        manager = DynamicInteractionManager()
        agent = MockAgent("test_agent")

        # Track performance
        await manager.track_performance(
            agent, "test_task", success=True, execution_time=0.5
        )

        metrics = manager.agent_metrics["test_agent"]
        assert metrics.total_tasks == 1
        assert metrics.success_rate == 1.0
        assert metrics.average_execution_time == 0.5

    @pytest.mark.asyncio
    async def test_adaptive_pattern_selection(self):
        """Test adaptive interaction pattern selection."""
        manager = DynamicInteractionManager()

        # Create agents with different performance characteristics
        agents = [MockAgent(f"agent{i}") for i in range(5)]

        # Simulate performance data
        for i, agent in enumerate(agents):
            success_rate = 0.9 - (i * 0.1)  # Decreasing success rates
            await manager.track_performance(
                agent, "task", success=success_rate > 0.5, execution_time=1.0
            )

        # Test pattern selection based on performance
        selected_pattern = manager.select_interaction_pattern(
            len(agents), complexity_score=0.8
        )
        assert selected_pattern in InteractionPattern


class TestConsensusEngine:
    """Test the complete consensus engine."""

    @pytest.mark.asyncio
    async def test_consensus_engine_integration(self, consensus_engine):
        """Test complete consensus engine workflow."""
        # Add mock agents
        agents = [MockAgent(f"agent{i}", confidence=0.8 + i * 0.05) for i in range(3)]

        for _, agent in enumerate(agents):
            consensus_engine.coordinator.add_agent(agent, role="analyzer")

        # Process task through consensus engine
        task = "analyze data"
        result = await consensus_engine.process_task(task)

        assert result is not None
        assert hasattr(result, "result")
        assert hasattr(result, "confidence")

    @pytest.mark.asyncio
    async def test_consensus_with_conflicts(self, consensus_engine):
        """Test consensus engine with conflicting predictions."""
        # Add agents that will produce conflicting results
        agents = [MockAgent(f"agent{i}") for i in range(4)]

        for agent in agents:
            consensus_engine.coordinator.add_agent(agent, role="analyzer")

        # Mock the coordinator to return conflicting predictions
        mock_predictions = [
            Prediction(result="A", confidence=0.9, agent_id="agent1"),
            Prediction(result="B", confidence=0.8, agent_id="agent2"),
            Prediction(result="A", confidence=0.7, agent_id="agent3"),
            Prediction(result="C", confidence=0.6, agent_id="agent4"),
        ]

        consensus_engine.coordinator.distribute_task = AsyncMock(
            return_value=mock_predictions
        )

        result = await consensus_engine.process_task("analyze conflicting data")

        # Should resolve conflicts and return a consensus
        assert result is not None
        assert result.result in ["A", "B", "C"]  # Should be one of the options

    @pytest.mark.asyncio
    async def test_agent_lifecycle_management(self, consensus_engine):
        """Test agent lifecycle management through consensus engine."""
        agents = [MockAgent(f"agent{i}") for i in range(2)]

        # Add agents
        for agent in agents:
            consensus_engine.coordinator.add_agent(agent, role="worker")

        # Start agents
        await consensus_engine.coordinator.start_agents()
        assert all(agent.started for agent in agents)

        # Stop agents
        await consensus_engine.coordinator.stop_agents()
        assert all(agent.stopped for agent in agents)


@pytest.mark.asyncio
async def test_end_to_end_consensus_workflow():
    """Test complete end-to-end consensus workflow."""
    # Setup
    coordinator = SimpleCoordinator()
    aggregator = BaseAggregator(majority_vote)
    engine = ConsensusEngine(coordinator=coordinator, aggregator=aggregator)

    # Add diverse agents
    agents = [
        MockAgent("expert_agent", confidence=0.95),
        MockAgent("general_agent", confidence=0.75),
        MockAgent("backup_agent", confidence=0.65),
    ]

    for agent in agents:
        coordinator.add_agent(agent, role="analyzer")

    # Start agents
    await coordinator.start_agents()

    try:
        # Process multiple tasks to test system stability
        tasks = ["analyze sentiment", "classify document", "extract entities"]

        for task in tasks:
            result = await engine.process_task(task)
            assert result is not None
            assert hasattr(result, "confidence")
            assert result.confidence > 0

    finally:
        # Cleanup
        await coordinator.stop_agents()
        assert all(agent.stopped for agent in agents)


if __name__ == "__main__":
    pytest.main([__file__])
