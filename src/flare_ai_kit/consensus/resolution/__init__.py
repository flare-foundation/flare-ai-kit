"""Conflict resolution module for multi-agent consensus."""

from flare_ai_kit.consensus.resolution.base import (
    BaseConflictDetector,
    BaseConflictResolver,
    BaseNegotiationProtocol,
    ConflictContext,
    ConflictSeverity,
    ConflictType,
    ResolutionResult,
)
from flare_ai_kit.consensus.resolution.detectors import (
    DomainConflictDetector,
    StatisticalConflictDetector,
)
from flare_ai_kit.consensus.resolution.resolvers import (
    ExpertiseBasedResolver,
    HybridConflictResolver,
    NegotiationProtocol,
    WeightedVotingResolver,
)

__all__ = [
    "BaseConflictDetector",
    "BaseConflictResolver",
    "BaseNegotiationProtocol",
    "ConflictContext",
    "ConflictSeverity",
    "ConflictType",
    "DomainConflictDetector",
    "ExpertiseBasedResolver",
    "HybridConflictResolver",
    "NegotiationProtocol",
    "ResolutionResult",
    "StatisticalConflictDetector",
    "WeightedVotingResolver",
]
