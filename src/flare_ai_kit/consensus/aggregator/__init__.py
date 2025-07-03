from .base import BaseAggregator
from .strategies import (
    majority_vote,
    top_confidence,
    weighted_average,
    # Advanced strategies
    adaptive_consensus,
    
)

from .advanced_strategies import (
    shapley_value_strategy,
    semantic_clustering_strategy,
)

from .tournament_strategy import (
    tournament_elimination_strategy,
)

from .advanced_aggregator import (
    AdvancedAggregator,
    PerformanceMetrics,
)


__all__ = [
    "BaseAggregator",
    "majority_vote",
    "top_confidence",
    "weighted_average",
    
    # New strategies:
    "shapley_value_strategy",
    "semantic_clustering_strategy", 
    "tournament_elimination_strategy",
    "adaptive_consensus",
    "AdvancedAggregator",
    "PerformanceMetrics",
]
