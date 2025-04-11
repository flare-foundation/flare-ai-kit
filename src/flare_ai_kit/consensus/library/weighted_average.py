"""Confidence-weighted average strategy for numerical predictions."""

from flare_ai_kit.consensus.aggregator import Prediction


def weighted_average(predictions: list[Prediction]) -> float:
    """Weighted Average for numerical predictions."""
    total_weight = sum(p.confidence for p in predictions)
    if total_weight == 0:
        return sum(float(p.prediction) for p in predictions) / len(predictions)

    weighted_sum = sum(float(p.prediction) * p.confidence for p in predictions)
    return weighted_sum / total_weight
