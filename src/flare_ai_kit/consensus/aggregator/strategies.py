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

# Additions to existing aggregator/strategies.py file

from typing import List
import logging

logger = logging.getLogger(__name__)

def _calculate_confidence_variance(predictions: List[Prediction]) -> float:
    """Calculate variance in confidence scores."""
    confidences = [p.confidence for p in predictions]
    if len(confidences) <= 1:
        return 0.0
    
    mean_conf = sum(confidences) / len(confidences)
    variance = sum((c - mean_conf) ** 2 for c in confidences) / len(confidences)
    return variance

def _calculate_prediction_diversity(predictions: List[Prediction]) -> float:
    """Calculate diversity of predictions (0 = all same, 1 = all different)."""
    prediction_texts = [str(p.prediction) for p in predictions]
    unique_predictions = set(prediction_texts)
    
    if len(predictions) <= 1:
        return 0.0
    
    return (len(unique_predictions) - 1) / (len(predictions) - 1)

def adaptive_consensus(predictions: List[Prediction]) -> Prediction:
    """
    Adaptive consensus that chooses the best strategy based on prediction characteristics.
    Falls back to basic strategies when advanced ones aren't available.
    """
    if not predictions:
        raise ValueError("No predictions to aggregate")
    
    if len(predictions) == 1:
        return predictions[0]
    
    # Analyze prediction characteristics
    n_predictions = len(predictions)
    
    # Check if predictions are numerical
    numerical_predictions: List[bool] = []
    for pred in predictions:
        try:
            float(pred.prediction)
            numerical_predictions.append(True)
        except (ValueError, TypeError):
            numerical_predictions.append(False)
    
    is_numerical = all(numerical_predictions)
    confidence_variance = _calculate_confidence_variance(predictions)
    prediction_diversity = _calculate_prediction_diversity(predictions)
    
    logger.info(f"Adaptive consensus analysis: n={n_predictions}, numerical={is_numerical}, "
               f"conf_var={confidence_variance:.3f}, diversity={prediction_diversity:.3f}")
    
    # Decision logic - use basic strategies for now, can be enhanced later
    if is_numerical and confidence_variance > 0.2:
        # Variable confidence numerical -> weighted average
        logger.info("Using weighted average for variable confidence numerical predictions")
        avg_pred = weighted_average(predictions)
        avg_conf = sum(p.confidence for p in predictions) / len(predictions)
        return Prediction(
            agent_id="adaptive_weighted_avg",
            prediction=str(avg_pred),
            confidence=avg_conf
        )
    
    elif prediction_diversity < 0.3:
        # Low diversity -> majority vote
        logger.info("Using majority vote for low diversity predictions")
        maj_pred = majority_vote(predictions)
        # Find confidence of majority prediction
        majority_confidences = [p.confidence for p in predictions if str(p.prediction) == maj_pred]
        avg_conf = sum(majority_confidences) / len(majority_confidences)
        return Prediction(
            agent_id="adaptive_majority",
            prediction=maj_pred,
            confidence=avg_conf
        )
    
    else:
        # Default to top confidence
        logger.info("Using top confidence as default strategy")
        return max(predictions, key=lambda p: p.confidence)

# Strategy registry for easy access
STRATEGY_REGISTRY = {
    # Basic strategies
    "top_confidence": top_confidence,
    "majority_vote": majority_vote,
    "weighted_average": weighted_average,
    "adaptive_consensus": adaptive_consensus,
}

def get_strategy(strategy_name: str):
    """Get a strategy function by name."""
    if strategy_name not in STRATEGY_REGISTRY:
        available = ", ".join(STRATEGY_REGISTRY.keys())
        raise ValueError(f"Unknown strategy '{strategy_name}'. Available: {available}")
    
    return STRATEGY_REGISTRY[strategy_name]

def list_available_strategies() -> List[str]:
    """Get list of all available strategy names."""
    return list(STRATEGY_REGISTRY.keys())