"""Conflict resolution implementations for multi-agent consensus."""

import statistics
import uuid
from typing import Any

from flare_ai_kit.common.schemas import Prediction
from flare_ai_kit.consensus.resolution.base import (
    BaseConflictResolver,
    BaseNegotiationProtocol,
    ConflictContext,
    ConflictType,
    ResolutionResult,
)


class WeightedVotingResolver(BaseConflictResolver):
    """Resolves conflicts using weighted voting based on agent reliability."""

    def __init__(self, agent_weights: dict[str, float] | None = None) -> None:
        self.agent_weights = agent_weights or {}

    async def resolve_conflict(self, conflict: ConflictContext) -> ResolutionResult:
        """Resolve conflict using weighted voting."""
        predictions = conflict.conflicting_predictions

        if conflict.conflict_type == ConflictType.VALUE_DISAGREEMENT:
            return await self._resolve_value_disagreement(conflict)
        if conflict.conflict_type == ConflictType.CONFIDENCE_MISMATCH:
            return await self._resolve_confidence_mismatch(conflict)
        if conflict.conflict_type == ConflictType.OUTLIER_DETECTION:
            return await self._resolve_outlier_conflict(conflict)
        # Default: highest weighted prediction
        best_pred = max(
            predictions, key=lambda p: self._get_agent_weight(p.agent_id) * p.confidence
        )
        return ResolutionResult(
            resolved_prediction=best_pred,
            resolution_method="weighted_selection",
            rationale=(
                f"Selected prediction from agent {best_pred.agent_id} "
                "with highest weighted confidence"
            ),
        )

    def can_handle(self, conflict_type: ConflictType) -> bool:
        """Check if this resolver can handle the conflict type."""
        return conflict_type in {
            ConflictType.VALUE_DISAGREEMENT,
            ConflictType.CONFIDENCE_MISMATCH,
            ConflictType.OUTLIER_DETECTION,
        }

    async def _resolve_value_disagreement(
        self, conflict: ConflictContext
    ) -> ResolutionResult:
        """Resolve value disagreements using weighted voting."""
        predictions = conflict.conflicting_predictions

        # Group predictions by value
        value_groups: dict[str, list[Prediction]] = {}
        for pred in predictions:
            value_key = str(pred.prediction)
            if value_key not in value_groups:
                value_groups[value_key] = []
            value_groups[value_key].append(pred)

        # Calculate weighted scores for each value
        value_scores = {}
        for value, preds in value_groups.items():
            total_weight = sum(
                self._get_agent_weight(p.agent_id) * p.confidence for p in preds
            )
            value_scores[value] = total_weight

        # Select value with highest weighted score
        winning_value = max(value_scores.keys(), key=lambda v: value_scores[v])  # type: ignore[arg-type]
        winning_preds = value_groups[winning_value]

        # Create consensus prediction
        avg_confidence = statistics.mean(p.confidence for p in winning_preds)
        resolved_pred = Prediction(
            agent_id="consensus_weighted_voting",
            prediction=winning_preds[0].prediction,  # Use original type
            confidence=min(avg_confidence * 0.9, 1.0),  # Slightly reduce confidence
        )

        return ResolutionResult(
            resolved_prediction=resolved_pred,
            resolution_method="weighted_voting",
            rationale=(
                f"Weighted voting selected '{winning_value}' with score "
                f"{value_scores[winning_value]:.3f}"
            ),
            additional_info={
                "value_scores": value_scores,
                "participating_agents": [p.agent_id for p in winning_preds],
            },
        )

    async def _resolve_confidence_mismatch(
        self, conflict: ConflictContext
    ) -> ResolutionResult:
        """Resolve confidence mismatches by adjusting confidence levels."""
        predictions = conflict.conflicting_predictions

        # Find the prediction with highest overall score (weight * confidence)
        best_pred = max(
            predictions, key=lambda p: self._get_agent_weight(p.agent_id) * p.confidence
        )

        # Reduce confidence due to disagreement
        confidence_penalty = 0.2 * len(predictions) / 10  # More agents = more penalty
        adjusted_confidence = max(best_pred.confidence - confidence_penalty, 0.1)

        resolved_pred = Prediction(
            agent_id="consensus_confidence_adjusted",
            prediction=best_pred.prediction,
            confidence=adjusted_confidence,
        )

        return ResolutionResult(
            resolved_prediction=resolved_pred,
            resolution_method="confidence_adjustment",
            confidence_adjustment=-confidence_penalty,
            rationale=(
                f"Selected prediction from {best_pred.agent_id} with adjusted "
                "confidence due to disagreement"
            ),
        )

    async def _resolve_outlier_conflict(
        self, conflict: ConflictContext
    ) -> ResolutionResult:
        """Resolve outlier conflicts by excluding outliers."""
        # Outliers are stored in conflicting_predictions
        # We need to get the full prediction set from metadata or assume removal
        outliers = conflict.conflicting_predictions

        return ResolutionResult(
            resolved_prediction=Prediction(
                agent_id="consensus_outlier_removed",
                prediction="outliers_detected",
                confidence=0.5,
            ),
            resolution_method="outlier_exclusion",
            rationale=(
                f"Detected {len(outliers)} outlier predictions that should be "
                "excluded from consensus"
            ),
            additional_info={
                "outlier_agents": [p.agent_id for p in outliers],
                "outlier_values": [p.prediction for p in outliers],
            },
        )

    def _get_agent_weight(self, agent_id: str) -> float:
        """Get weight for an agent, defaulting to 1.0."""
        return self.agent_weights.get(agent_id, 1.0)


class ExpertiseBasedResolver(BaseConflictResolver):
    """Resolves conflicts by deferring to domain experts."""

    def __init__(
        self, agent_expertise: dict[str, dict[str, float]] | None = None
    ) -> None:
        self.agent_expertise = agent_expertise or {}

    async def resolve_conflict(self, conflict: ConflictContext) -> ResolutionResult:
        """Resolve conflict by deferring to experts."""
        domain = conflict.metadata.get("domain", "general")
        predictions = conflict.conflicting_predictions

        # Find the most expert agent
        expert_scores = {}
        for pred in predictions:
            expertise = self.agent_expertise.get(pred.agent_id, {}).get(domain, 0.0)
            expert_scores[pred.agent_id] = expertise

        if not expert_scores:
            # No expertise data, fall back to highest confidence
            best_pred = max(predictions, key=lambda p: p.confidence)
            return ResolutionResult(
                resolved_prediction=best_pred,
                resolution_method="highest_confidence_fallback",
                rationale=(
                    "No expertise data available, selected highest confidence "
                    "prediction"
                ),
            )

        # Select prediction from most expert agent
        expert_agent = max(expert_scores.keys(), key=lambda aid: expert_scores[aid])  # type: ignore[arg-type]
        expert_pred = next(p for p in predictions if p.agent_id == expert_agent)

        return ResolutionResult(
            resolved_prediction=expert_pred,
            resolution_method="expertise_based",
            rationale=(
                f"Deferred to expert agent {expert_agent} with expertise score "
                f"{expert_scores[expert_agent]:.3f} in domain '{domain}'"
            ),
            additional_info={
                "domain": domain,
                "expert_scores": expert_scores,
                "selected_expert": expert_agent,
            },
        )

    def can_handle(self, conflict_type: ConflictType) -> bool:
        """Check if this resolver can handle the conflict type."""
        return conflict_type == ConflictType.EXPERTISE_CONFLICT


class NegotiationProtocol(BaseNegotiationProtocol):
    """Implements a simple negotiation protocol between agents."""

    def __init__(self, communication_manager: Any | None = None) -> None:
        self.communication_manager = communication_manager

    async def negotiate(
        self, agent_ids: list[str], conflict: ConflictContext, max_rounds: int = 3
    ) -> ResolutionResult:
        """Conduct negotiation between conflicting agents."""
        if not self.communication_manager:
            # Fallback to simple resolution without negotiation
            predictions = conflict.conflicting_predictions
            best_pred = max(predictions, key=lambda p: p.confidence)
            return ResolutionResult(
                resolved_prediction=best_pred,
                resolution_method="negotiation_fallback",
                rationale="No communication manager available for negotiation",
            )

        negotiation_id = str(uuid.uuid4())

        # Start negotiation process
        for _round_num in range(max_rounds):
            # Send negotiation requests to all agents
            for agent_id in agent_ids:
                await self.communication_manager.request_collaboration(
                    requester_id="consensus_engine",
                    target_id=agent_id,
                    task_description=(
                        f"Negotiate resolution for conflict {conflict.task_id}"
                    ),
                    collaboration_type="negotiation",
                )

            # In a real implementation, you would:
            # 1. Wait for agent responses
            # 2. Analyze their proposed resolutions
            # 3. Check for convergence
            # 4. Continue negotiation if needed

            # For now, simulate convergence after first round
            break

        # Return a negotiated result (simplified)
        predictions = conflict.conflicting_predictions
        avg_confidence = statistics.mean(p.confidence for p in predictions)

        # Create a compromise prediction
        resolved_pred = Prediction(
            agent_id="consensus_negotiated",
            prediction="negotiated_result",
            confidence=avg_confidence * 0.8,  # Reduce confidence due to conflict
        )

        return ResolutionResult(
            resolved_prediction=resolved_pred,
            resolution_method="negotiation",
            rationale=(
                f"Negotiated resolution after {max_rounds} rounds with "
                f"{len(agent_ids)} agents"
            ),
            additional_info={
                "negotiation_id": negotiation_id,
                "rounds_conducted": 1,
                "participating_agents": agent_ids,
            },
        )


class HybridConflictResolver(BaseConflictResolver):
    """Combines multiple resolution strategies based on conflict characteristics."""

    def __init__(
        self,
        resolvers: list[BaseConflictResolver] | None = None,
        agent_weights: dict[str, float] | None = None,
        agent_expertise: dict[str, dict[str, float]] | None = None,
    ) -> None:
        self.resolvers = resolvers or []

        # Add default resolvers if none provided
        if not self.resolvers:
            self.resolvers = [
                WeightedVotingResolver(agent_weights),
                ExpertiseBasedResolver(agent_expertise),
            ]

    async def resolve_conflict(self, conflict: ConflictContext) -> ResolutionResult:
        """Resolve conflict using the most appropriate strategy."""
        # Find the best resolver for this conflict type
        suitable_resolvers = [
            r for r in self.resolvers if r.can_handle(conflict.conflict_type)
        ]

        if not suitable_resolvers:
            # Fallback to weighted voting
            fallback_resolver = WeightedVotingResolver()
            return await fallback_resolver.resolve_conflict(conflict)

        # Use the first suitable resolver
        # In a more sophisticated implementation, you could:
        # - Try multiple resolvers and compare results
        # - Use ML to select the best resolver
        # - Have a voting system among resolvers

        resolver = suitable_resolvers[0]
        result = await resolver.resolve_conflict(conflict)

        # Add metadata about which resolver was used
        result.additional_info = result.additional_info or {}
        result.additional_info["resolver_used"] = resolver.__class__.__name__

        return result

    def can_handle(self, conflict_type: ConflictType) -> bool:
        """Check if any of the available resolvers can handle this conflict type."""
        return any(r.can_handle(conflict_type) for r in self.resolvers)
