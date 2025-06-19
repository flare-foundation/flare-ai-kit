"""Interface for consensus engine aggregator."""

from abc import ABC, abstractmethod
from collections.abc import Callable

from flare_ai_kit.common import Prediction


class BaseAggregator(ABC):
    """Base aggregator class."""

    def __init__(
        self,
        strategy: Callable[[list[Prediction]], Prediction],
    ) -> None:
        """Initialize Aggregator class with desired strategy."""
        self.strategy = strategy

    @abstractmethod
    async def aggregate(self, predictions: list[Prediction]) -> Prediction:
        """Aggregate predictions using the specified strategy."""
        return self.strategy(predictions)
