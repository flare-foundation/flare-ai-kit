from unittest.mock import AsyncMock

import pytest

from flare_ai_kit.common.schemas import Prediction
from flare_ai_kit.consensus.resolution.base import (
    ConflictContext,
    ConflictType,
)
from flare_ai_kit.consensus.resolution.resolvers import (
    ExpertiseBasedResolver,
    HybridConflictResolver,
    NegotiationProtocol,
    WeightedVotingResolver,
)


def _make_predictions():
    return [
        Prediction(agent_id="a1", prediction="yes", confidence=0.8),
        Prediction(agent_id="a2", prediction="no", confidence=0.6),
        Prediction(agent_id="a3", prediction="yes", confidence=0.4),
    ]


@pytest.mark.asyncio
async def test_weighted_voting_value_disagreement():
    predictions = _make_predictions()
    ctx = ConflictContext(
        task_id="t1",
        conflict_type=ConflictType.VALUE_DISAGREEMENT,
        conflicting_predictions=predictions,
        metadata={},
        severity="medium",
    )
    resolver = WeightedVotingResolver(agent_weights={"a1": 2.0, "a2": 1.0, "a3": 1.0})
    result = await resolver.resolve_conflict(ctx)

    assert result.resolution_method == "weighted_voting"
    assert result.resolved_prediction.prediction in {"yes", "no"}
    assert "value_scores" in result.additional_info
    # a1 has highest weight, so "yes" should win
    assert result.resolved_prediction.prediction == "yes"


@pytest.mark.asyncio
async def test_weighted_voting_confidence_mismatch_adjusts_confidence():
    predictions = _make_predictions()
    ctx = ConflictContext(
        task_id="t2",
        conflict_type=ConflictType.CONFIDENCE_MISMATCH,
        conflicting_predictions=predictions,
        metadata={},
        severity="medium",
    )
    resolver = WeightedVotingResolver()
    result = await resolver.resolve_conflict(ctx)

    assert result.resolution_method == "confidence_adjustment"
    # confidence is reduced from original best
    assert result.resolved_prediction.confidence < max(
        p.confidence for p in predictions
    )


@pytest.mark.asyncio
async def test_weighted_voting_outlier_detection():
    predictions = _make_predictions()
    ctx = ConflictContext(
        task_id="t3",
        conflict_type=ConflictType.OUTLIER_DETECTION,
        conflicting_predictions=predictions,
        metadata={},
        severity="medium",
    )
    resolver = WeightedVotingResolver()
    result = await resolver.resolve_conflict(ctx)

    assert result.resolution_method == "outlier_exclusion"
    assert "outlier_agents" in result.additional_info
    assert set(result.additional_info["outlier_agents"]) == {"a1", "a2", "a3"}


@pytest.mark.asyncio
async def test_expertise_based_resolver_prefers_expert():
    predictions = _make_predictions()
    ctx = ConflictContext(
        task_id="t4",
        conflict_type=ConflictType.EXPERTISE_CONFLICT,
        conflicting_predictions=predictions,
        metadata={"domain": "finance"},
        severity="medium",
    )
    expertise = {"a1": {"finance": 0.9}, "a2": {"finance": 0.5}}
    resolver = ExpertiseBasedResolver(agent_expertise=expertise)
    result = await resolver.resolve_conflict(ctx)

    assert result.resolution_method == "expertise_based"
    assert result.resolved_prediction.agent_id == "a1"
    assert "expert_scores" in result.additional_info


@pytest.mark.asyncio
async def test_expertise_based_resolver_fallback_to_confidence():
    predictions = _make_predictions()
    ctx = ConflictContext(
        task_id="t5",
        conflict_type=ConflictType.EXPERTISE_CONFLICT,
        conflicting_predictions=predictions,
        metadata={"domain": "unknown"},
        severity="medium",
    )
    resolver = ExpertiseBasedResolver(agent_expertise={})

    result = await resolver.resolve_conflict(ctx)

    # falls back to highest confidence prediction (a1)
    assert result.resolved_prediction.agent_id == "a1"


@pytest.mark.asyncio
async def test_negotiation_protocol_without_communication_manager():
    predictions = _make_predictions()
    ctx = ConflictContext(
        task_id="t6",
        conflict_type=ConflictType.VALUE_DISAGREEMENT,
        conflicting_predictions=predictions,
        metadata={},
        severity="medium",
    )
    protocol = NegotiationProtocol()
    result = await protocol.negotiate(agent_ids=["a1", "a2"], conflict=ctx)

    assert result.resolution_method == "negotiation_fallback"
    assert result.resolved_prediction in predictions


@pytest.mark.asyncio
async def test_negotiation_protocol_with_communication_manager():
    predictions = _make_predictions()
    ctx = ConflictContext(
        task_id="t7",
        conflict_type=ConflictType.VALUE_DISAGREEMENT,
        conflicting_predictions=predictions,
        metadata={},
        severity="medium",
    )
    comms = AsyncMock()
    protocol = NegotiationProtocol(communication_manager=comms)
    result = await protocol.negotiate(
        agent_ids=["a1", "a2"], conflict=ctx, max_rounds=2
    )

    assert result.resolution_method == "negotiation"
    assert result.resolved_prediction.prediction == "negotiated_result"
    # Should have called request_collaboration for each agent
    assert comms.request_collaboration.await_count == 2


@pytest.mark.asyncio
async def test_hybrid_conflict_resolver_uses_weighted_by_default():
    predictions = _make_predictions()
    ctx = ConflictContext(
        task_id="t8",
        conflict_type=ConflictType.VALUE_DISAGREEMENT,
        conflicting_predictions=predictions,
        metadata={},
        severity="medium",
    )
    hybrid = HybridConflictResolver(agent_weights={"a1": 2.0})
    result = await hybrid.resolve_conflict(ctx)

    assert result.resolution_method in {
        "weighted_voting",
        "confidence_adjustment",
        "outlier_exclusion",
    }
    assert "resolver_used" in result.additional_info
    assert hybrid.can_handle(ConflictType.VALUE_DISAGREEMENT) is True
