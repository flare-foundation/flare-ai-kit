"""Aggregation strategies for consensus predictions."""

from collections import Counter

from flare_ai_kit.common import Prediction


def top_confidence(predictions: list[Prediction]) -> str | float:
    """Returns the prediction with the highest confidence."""
    return max(predictions, key=lambda p: p.confidence).prediction


def majority_vote(predictions: list[Prediction]) -> str:
    """Majority vote aggregation."""
    values = [str(p.prediction) for p in predictions]
    return Counter(values).most_common(1)[0][0]


def weighted_average(predictions: list[Prediction]) -> float:
    """Confidence-weighted average strategy for numerical predictions."""
    total_weight = sum(p.confidence for p in predictions)
    if total_weight == 0:
        return sum(float(p.prediction) for p in predictions) / len(predictions)

    weighted_sum = sum(float(p.prediction) * p.confidence for p in predictions)
    return weighted_sum / total_weight
