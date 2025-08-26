"""Dynamic agent interaction management for consensus engine."""

import asyncio
import time
from collections import defaultdict
from enum import Enum
from typing import Any

try:
    from pydantic import BaseModel as _PydanticBaseModel

    class BaseModel(_PydanticBaseModel):  # type: ignore[misc]
        """Base model using pydantic."""

        class Config:
            """Pydantic configuration."""

            arbitrary_types_allowed = True

except ImportError:
    # Fallback for when pydantic is not available
    class BaseModel:  # type: ignore[misc]
        """Fallback BaseModel when pydantic is not available."""

        def __init__(self, **kwargs: Any) -> None:
            for key, value in kwargs.items():
                setattr(self, key, value)


from flare_ai_kit.common.schemas import Prediction
from flare_ai_kit.consensus.communication import CommunicationManager
from flare_ai_kit.consensus.coordinator.simple import CoordinatorAgent

# Constants for interaction pattern thresholds
MIN_AGENTS_FOR_COMPETITIVE = 3
MIN_AGENTS_FOR_COLLABORATION = 3
MAX_AGENTS_FOR_CONSENSUS = 6
COLLABORATIVE_BENEFIT_THRESHOLD = 0.7
CONFLICT_LIKELIHOOD_THRESHOLD = 0.6
EXPERTISE_THRESHOLD = 0.7
PAIR_SIZE = 2
MIN_PREDICTIONS_FOR_CONVERGENCE = 2


class InteractionPattern(str, Enum):
    """Types of agent interaction patterns."""

    BROADCAST = "broadcast"  # All agents work independently
    HIERARCHICAL = "hierarchical"  # Leaders coordinate sub-groups
    PEER_TO_PEER = "peer_to_peer"  # Direct agent collaboration
    CONSENSUS_ROUNDS = "consensus_rounds"  # Multiple rounds of refinement
    EXPERT_CONSULTATION = "expert_consultation"  # Defer to domain experts
    COMPETITIVE = "competitive"  # Agents compete for best solution


class AgentPerformanceMetrics(BaseModel):  # type: ignore[misc]
    """Performance metrics for individual agents."""

    agent_id: str
    accuracy_score: float = 0.0
    consistency_score: float = 0.0
    response_time_avg: float = 0.0
    confidence_calibration: float = 0.0  # How well confidence matches actual accuracy
    collaboration_score: float = 0.0  # How well agent works with others
    domain_expertise: dict[str, float] = {}  # type: ignore[assignment,misc]  # noqa: RUF012
    task_count: int = 0
    last_active: float = 0.0


class TaskComplexity(BaseModel):  # type: ignore[misc]
    """Metadata about task complexity to guide interaction patterns."""

    difficulty: float = 0.5  # 0-1 scale
    domain: str = "general"
    requires_expertise: bool = False
    time_sensitive: bool = False
    collaborative_benefit: float = 0.5  # How much collaboration helps
    conflict_likelihood: float = 0.3  # Expected probability of conflicts


class DynamicInteractionManager:
    """Manages dynamic agent interactions based on task and performance."""

    def __init__(
        self,
        communication_manager: CommunicationManager | None = None,
        performance_history_size: int = 100,
    ) -> None:
        self.communication_manager = communication_manager or CommunicationManager()
        self.performance_history_size = performance_history_size

        # Agent performance tracking
        self.agent_metrics: dict[str, AgentPerformanceMetrics] = {}
        self.task_history: list[dict[str, Any]] = []
        self.interaction_patterns: dict[str, InteractionPattern] = {}

        # Dynamic groupings
        self.agent_groups: dict[str, set[str]] = {}
        self.expert_domains: dict[str, list[str]] = defaultdict(list)

    async def select_interaction_pattern(
        self,
        task: str,
        available_agents: list[CoordinatorAgent],
        task_complexity: TaskComplexity | None = None,
    ) -> tuple[InteractionPattern, dict[str, Any]]:
        """Select optimal interaction pattern for a given task."""
        if not task_complexity:
            task_complexity = await self._analyze_task_complexity(task)

        agent_count = len(available_agents)

        # Decision logic based on task characteristics and agent capabilities
        if task_complexity.requires_expertise:
            experts = self._find_domain_experts(
                task_complexity.domain, available_agents
            )
            if experts:
                return InteractionPattern.EXPERT_CONSULTATION, {
                    "expert_agents": [e.agent_id for e in experts],
                    "consultation_rounds": 2,
                }

        if task_complexity.time_sensitive and agent_count > MIN_AGENTS_FOR_COMPETITIVE:
            return InteractionPattern.COMPETITIVE, {
                "time_limit": 30,  # seconds
                "selection_criteria": "fastest_accurate",
            }

        if (
            task_complexity.collaborative_benefit > COLLABORATIVE_BENEFIT_THRESHOLD
            and agent_count >= MIN_AGENTS_FOR_COLLABORATION
        ):
            if agent_count > MAX_AGENTS_FOR_CONSENSUS:
                return InteractionPattern.HIERARCHICAL, {
                    "group_size": 3,
                    "coordination_rounds": 2,
                }
            return InteractionPattern.CONSENSUS_ROUNDS, {
                "max_rounds": 3,
                "convergence_threshold": 0.8,
            }

        if task_complexity.conflict_likelihood > CONFLICT_LIKELIHOOD_THRESHOLD:
            return InteractionPattern.PEER_TO_PEER, {
                "review_pairs": self._create_review_pairs(available_agents),
                "negotiation_enabled": True,
            }

        # Default: broadcast pattern
        return InteractionPattern.BROADCAST, {
            "timeout": 60,
            "require_all_responses": False,
        }

    async def coordinate_agents(
        self,
        pattern: InteractionPattern,
        agents: list[CoordinatorAgent],
        task: str,
        pattern_config: dict[str, Any],
    ) -> list[Prediction]:
        """Coordinate agents according to the selected interaction pattern."""
        # Track start time for potential future use
        _start_time = time.time()

        # Map interaction patterns to coordination methods
        coordination_methods = {
            InteractionPattern.BROADCAST: self._coordinate_broadcast,
            InteractionPattern.HIERARCHICAL: self._coordinate_hierarchical,
            InteractionPattern.PEER_TO_PEER: self._coordinate_peer_to_peer,
            InteractionPattern.CONSENSUS_ROUNDS: self._coordinate_consensus_rounds,
            InteractionPattern.EXPERT_CONSULTATION: (
                self._coordinate_expert_consultation
            ),
            InteractionPattern.COMPETITIVE: self._coordinate_competitive,
        }

        # Get the coordination method or fallback to broadcast
        coordination_method = coordination_methods.get(
            pattern, self._coordinate_broadcast
        )

        return await coordination_method(agents, task, pattern_config)

    async def _coordinate_broadcast(
        self, agents: list[CoordinatorAgent], task: str, config: dict[str, Any]
    ) -> list[Prediction]:
        """Standard broadcast pattern - all agents work independently."""
        timeout = config.get("timeout", 60)

        # Run all agents concurrently
        tasks = [agent.agent.run(task) for agent in agents]

        try:
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True), timeout=timeout
            )
        except TimeoutError:
            results = ["timeout"] * len(agents)

        # Convert to predictions
        predictions: list[Prediction] = []
        for agent, result in zip(agents, results, strict=False):
            if result != "timeout" and not isinstance(result, Exception):
                # Convert result to string if needed
                prediction_value: str | float = (
                    str(result) if not isinstance(result, (str, int, float)) else result
                )
                predictions.append(
                    Prediction(
                        agent_id=agent.agent_id,
                        prediction=prediction_value,
                        confidence=agent.config.get("confidence", 1.0),
                    )
                )

        return predictions

    async def _coordinate_hierarchical(
        self, agents: list[CoordinatorAgent], task: str, config: dict[str, Any]
    ) -> list[Prediction]:
        """Hierarchical pattern with group leaders."""
        group_size = config.get("group_size", 3)
        _rounds = config.get("coordination_rounds", 2)

        # Create groups
        groups = [agents[i : i + group_size] for i in range(0, len(agents), group_size)]

        group_predictions: list[Prediction] = []

        for group in groups:
            if not group:
                continue

            # Select group leader (highest performing agent)
            leader = max(
                group,
                key=lambda a: self.agent_metrics.get(
                    a.agent_id, AgentPerformanceMetrics(agent_id=a.agent_id)
                ).accuracy_score,
            )

            # Group works on task
            group_results = await self._coordinate_broadcast(
                group, task, {"timeout": 30}
            )

            if group_results:
                # Leader consolidates group results
                prediction_strs = [str(p.prediction) for p in group_results]
                consolidation_task = (
                    f"Consolidate these predictions for task '{task}': "
                    f"{prediction_strs}"
                )
                leader_result = await leader.agent.run(consolidation_task)

                # Convert result to appropriate type
                prediction_value: str | float = (
                    str(leader_result)
                    if not isinstance(leader_result, (str, int, float))
                    else leader_result
                )
                group_predictions.append(
                    Prediction(
                        agent_id=f"group_leader_{leader.agent_id}",
                        prediction=prediction_value,
                        confidence=0.8,  # Slightly reduced for group decision
                    )
                )

        return group_predictions

    async def _coordinate_peer_to_peer(
        self, agents: list[CoordinatorAgent], task: str, config: dict[str, Any]
    ) -> list[Prediction]:
        """Peer-to-peer pattern with direct collaboration."""
        review_pairs = config.get("review_pairs", [])

        # First round: initial predictions
        initial_predictions = await self._coordinate_broadcast(
            agents, task, {"timeout": 30}
        )

        # Second round: peer reviews
        reviewed_predictions: list[Prediction] = []

        for pair in review_pairs:
            if len(pair) != PAIR_SIZE:
                continue

            agent_1_id, agent_2_id = pair
            agent_1 = next((a for a in agents if a.agent_id == agent_1_id), None)
            agent_2 = next((a for a in agents if a.agent_id == agent_2_id), None)

            if not agent_1 or not agent_2:
                continue

            # Find their initial predictions
            pred_1 = next(
                (p for p in initial_predictions if p.agent_id == agent_1_id), None
            )
            pred_2 = next(
                (p for p in initial_predictions if p.agent_id == agent_2_id), None
            )

            if pred_1 and pred_2:
                # Agent 1 reviews Agent 2's prediction
                review_task = (
                    f"Review this prediction for task '{task}': {pred_2.prediction}. "
                    "Provide feedback or improved version."
                )
                reviewed_1 = await agent_1.agent.run(review_task)

                # Agent 2 reviews Agent 1's prediction
                review_task = (
                    f"Review this prediction for task '{task}': {pred_1.prediction}. "
                    "Provide feedback or improved version."
                )
                reviewed_2 = await agent_2.agent.run(review_task)

                # Convert results to appropriate types
                pred_1_value: str | float = (
                    str(reviewed_1)
                    if not isinstance(reviewed_1, (str, int, float))
                    else reviewed_1
                )
                pred_2_value: str | float = (
                    str(reviewed_2)
                    if not isinstance(reviewed_2, (str, int, float))
                    else reviewed_2
                )

                reviewed_predictions.extend(
                    [
                        Prediction(
                            agent_id=f"reviewed_{agent_1_id}",
                            prediction=pred_1_value,
                            confidence=0.85,
                        ),
                        Prediction(
                            agent_id=f"reviewed_{agent_2_id}",
                            prediction=pred_2_value,
                            confidence=0.85,
                        ),
                    ]
                )

        return reviewed_predictions or initial_predictions

    async def _coordinate_consensus_rounds(
        self, agents: list[CoordinatorAgent], task: str, config: dict[str, Any]
    ) -> list[Prediction]:
        """Multiple rounds of consensus building."""
        max_rounds = config.get("max_rounds", 3)
        convergence_threshold = config.get("convergence_threshold", 0.8)

        current_predictions = await self._coordinate_broadcast(
            agents, task, {"timeout": 30}
        )

        for _round_num in range(max_rounds - 1):
            # Check for convergence
            if self._check_convergence(current_predictions, convergence_threshold):
                break

            # Create summary of current state
            prediction_summary = self._create_prediction_summary(current_predictions)

            # Run another round with context
            refined_task = f"""
            Task: {task}

            Previous round predictions: {prediction_summary}

            Please refine your prediction considering the above results.
            """

            current_predictions = await self._coordinate_broadcast(
                agents, refined_task, {"timeout": 30}
            )

        return current_predictions

    async def _coordinate_expert_consultation(
        self, agents: list[CoordinatorAgent], task: str, config: dict[str, Any]
    ) -> list[Prediction]:
        """Expert consultation pattern."""
        expert_agent_ids = config.get("expert_agents", [])
        rounds = config.get("consultation_rounds", 2)

        expert_agents = [a for a in agents if a.agent_id in expert_agent_ids]
        other_agents = [a for a in agents if a.agent_id not in expert_agent_ids]

        # Round 1: Experts provide initial analysis
        expert_predictions = await self._coordinate_broadcast(
            expert_agents, task, {"timeout": 45}
        )

        if rounds > 1 and other_agents:
            # Round 2: Other agents contribute with expert context
            expert_summary = self._create_prediction_summary(expert_predictions)

            contextual_task = f"""
            Task: {task}

            Expert analysis: {expert_summary}

            Please provide your analysis considering the expert input above.
            """

            other_predictions = await self._coordinate_broadcast(
                other_agents, contextual_task, {"timeout": 30}
            )
            return expert_predictions + other_predictions

        return expert_predictions

    async def _coordinate_competitive(
        self, agents: list[CoordinatorAgent], task: str, config: dict[str, Any]
    ) -> list[Prediction]:
        """Competitive pattern for time-sensitive tasks."""
        time_limit = config.get("time_limit", 30)

        # Run agents with strict time limit
        tasks = [agent.agent.run(task) for agent in agents]

        try:
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True), timeout=time_limit
            )
        except TimeoutError:
            results = ["timeout"] * len(agents)

        # Only return successful results
        predictions: list[Prediction] = []
        for agent, result in zip(agents, results, strict=False):
            if result != "timeout" and not isinstance(result, Exception):
                # Convert result to appropriate type
                prediction_value: str | float = (
                    str(result) if not isinstance(result, (str, int, float)) else result
                )
                predictions.append(
                    Prediction(
                        agent_id=agent.agent_id,
                        prediction=prediction_value,
                        confidence=agent.config.get("confidence", 1.0),
                    )
                )

        return predictions

    def _find_domain_experts(
        self, domain: str, agents: list[CoordinatorAgent]
    ) -> list[CoordinatorAgent]:
        """Find agents with expertise in a specific domain."""
        experts: list[CoordinatorAgent] = []
        for agent in agents:
            metrics = self.agent_metrics.get(agent.agent_id)
            if (
                metrics
                and metrics.domain_expertise.get(domain, 0.0) > EXPERTISE_THRESHOLD
            ):
                experts.append(agent)
        return experts

    def _create_review_pairs(
        self, agents: list[CoordinatorAgent]
    ) -> list[tuple[str, str]]:
        """Create pairs of agents for peer review."""
        agent_ids = [a.agent_id for a in agents]

        return [
            (agent_ids[i], agent_ids[i + 1])
            for i in range(0, len(agent_ids) - 1, 2)
            if i + 1 < len(agent_ids)
        ]

    def _check_convergence(
        self, predictions: list[Prediction], threshold: float
    ) -> bool:
        """Check if predictions have converged."""
        if len(predictions) < MIN_PREDICTIONS_FOR_CONVERGENCE:
            return True

        # Simple convergence check based on prediction similarity
        string_preds = [str(p.prediction) for p in predictions]
        unique_preds = set(string_preds)

        # If most predictions are the same
        if len(unique_preds) == 1:
            return True

        # Check if majority agrees
        max_count = max(string_preds.count(pred) for pred in unique_preds)
        consensus_ratio = max_count / len(predictions)

        return consensus_ratio >= threshold

    def _create_prediction_summary(self, predictions: list[Prediction]) -> str:
        """Create a summary of predictions for context."""
        if not predictions:
            return "No predictions available"

        summary_parts = [
            f"Agent {pred.agent_id}: {pred.prediction} "
            f"(confidence: {pred.confidence:.2f})"
            for pred in predictions
        ]

        return "; ".join(summary_parts)

    async def _analyze_task_complexity(self, task: str) -> TaskComplexity:
        """Analyze task to determine complexity characteristics."""
        # Simple heuristics - in production this could use ML
        complexity = TaskComplexity()

        task_lower = task.lower()

        # Difficulty heuristics
        if any(
            word in task_lower
            for word in ["complex", "difficult", "challenging", "analyze"]
        ):
            complexity.difficulty = 0.8
        elif any(word in task_lower for word in ["simple", "basic", "easy"]):
            complexity.difficulty = 0.3

        # Domain detection
        if any(word in task_lower for word in ["medical", "health", "diagnosis"]):
            complexity.domain = "medical"
            complexity.requires_expertise = True
        elif any(word in task_lower for word in ["financial", "trading", "investment"]):
            complexity.domain = "financial"
            complexity.requires_expertise = True
        elif any(word in task_lower for word in ["technical", "engineering", "code"]):
            complexity.domain = "technical"

        # Time sensitivity
        if any(
            word in task_lower for word in ["urgent", "quickly", "fast", "immediate"]
        ):
            complexity.time_sensitive = True

        # Collaboration benefit
        if any(
            word in task_lower
            for word in ["brainstorm", "discuss", "collaborate", "review"]
        ):
            complexity.collaborative_benefit = 0.8

        return complexity

    async def update_agent_performance(
        self, agent_id: str, task_result: dict[str, Any]
    ) -> None:
        """Update performance metrics for an agent."""
        if agent_id not in self.agent_metrics:
            self.agent_metrics[agent_id] = AgentPerformanceMetrics(agent_id=agent_id)

        metrics = self.agent_metrics[agent_id]
        metrics.task_count += 1
        metrics.last_active = time.time()

        # Update metrics based on task result
        if "accuracy" in task_result:
            metrics.accuracy_score = (
                metrics.accuracy_score * 0.9 + task_result["accuracy"] * 0.1
            )

        if "response_time" in task_result:
            metrics.response_time_avg = (
                metrics.response_time_avg * 0.9 + task_result["response_time"] * 0.1
            )

        if "collaboration_rating" in task_result:
            metrics.collaboration_score = (
                metrics.collaboration_score * 0.9
                + task_result["collaboration_rating"] * 0.1
            )
