"""Module framework for achieving consensus among multiple AI agents."""

from .aggregator import (
    BaseAggregator, majority_vote, top_confidence, weighted_average,
    
    # Adding new imports:
    shapley_value_strategy,
    semantic_clustering_strategy,
    tournament_elimination_strategy,
    adaptive_consensus,
    AdvancedAggregator,
    PerformanceMetrics,
)

from .coordinator import BaseCoordinator
from .engine import ConsensusEngine


__all__ = [
    "BaseAggregator",
    "BaseCoordinator", 
    "ConsensusEngine",
    "majority_vote",
    "top_confidence",
    "weighted_average",
    
    # New strategies
    "shapley_value_strategy",
    "semantic_clustering_strategy", 
    "tournament_elimination_strategy",
    "adaptive_consensus",
    "AdvancedAggregator",
    "PerformanceMetrics",
]