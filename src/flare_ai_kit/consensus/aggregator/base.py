"""Interface for consensus engine aggregator."""

from abc import ABC, abstractmethod

from .prediction import Prediction


class BaseAggregator(ABC):
    """Base aggregator class."""

    @abstractmethod
    async def aggregate(self, predictions: list[Prediction]) -> Prediction:
        """Aggregate predictions into a consensus result."""
