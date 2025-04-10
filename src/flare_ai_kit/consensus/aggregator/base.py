"""Interface for consensus engine aggregator."""

from abc import ABC, abstractmethod

from .prediction import Prediction


class Aggregator(ABC):
    """Base aggregator class."""

    @abstractmethod
    def aggregate(self, predictions: list[Prediction]) -> Prediction:
        """Aggregate a list of predictions from various agents."""
