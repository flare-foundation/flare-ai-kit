"""Aggregator with support for multiple aggregation strategies."""

from collections.abc import Callable
from typing import override

from flare_ai_kit.consensus.aggregator.base import BaseAggregator
from flare_ai_kit.consensus.aggregator.prediction import Prediction


class StrategicAggregator(BaseAggregator):
    """Aggregator using a plug-and-play aggregation strategy."""

    def __init__(
        self,
        strategy: Callable[[list[Prediction]], Prediction],
    ) -> None:
        """Initialize Aggregator class with desired strategy."""
        self.strategy = strategy

    @override
    async def aggregate(self, predictions: list[Prediction]) -> Prediction:
        return self.strategy(predictions)
