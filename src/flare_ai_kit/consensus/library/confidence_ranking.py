"""Returns the prediction with the highest confidence."""

from flare_ai_kit.consensus.aggregator import Prediction


def top_confidence(predictions: list[Prediction]) -> str | float:
    """Returns the prediction with the highest confidence."""
    return max(predictions, key=lambda p: p.confidence).prediction
