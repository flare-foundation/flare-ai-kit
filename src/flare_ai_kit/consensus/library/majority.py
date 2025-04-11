"""Majority vote aggregation strategy."""

from collections import Counter

from flare_ai_kit.consensus.aggregator import Prediction


def majority_vote(predictions: list[Prediction]) -> str:
    """Majority vote function."""
    values = [str(p.prediction) for p in predictions]
    return Counter(values).most_common(1)[0][0]
