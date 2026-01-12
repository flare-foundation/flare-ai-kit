"""Interface for consensus engine aggregator."""

from abc import ABC, abstractmethod
from collections.abc import Callable

from flare_ai_kit.common import Prediction

# Refer to llm_consensus.py for an example of how to use this class.
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

