"""Module framework for achieving consensus among multiple AI agents."""

from .aggregator import BaseAggregator, majority_vote, top_confidence, weighted_average
from .coordinator import Coordinator
from .engine import ConsensusEngine

__all__ = [
    "BaseAggregator",
    "ConsensusEngine",
    "Coordinator",
    "majority_vote",
    "top_confidence",
    "weighted_average",
]
