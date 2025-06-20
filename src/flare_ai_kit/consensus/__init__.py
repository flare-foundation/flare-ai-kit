"""Module framework for achieving consensus among multiple AI agents."""

from .aggregator import BaseAggregator, majority_vote, top_confidence, weighted_average
from .coordinator import BaseCoordinator
from .engine import ConsensusEngine

__all__ = [
    "BaseAggregator",
    "BaseCoordinator",
    "ConsensusEngine",
    "majority_vote",
    "top_confidence",
    "weighted_average",
]
