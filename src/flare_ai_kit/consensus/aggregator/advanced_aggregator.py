"""Advanced aggregator implementation with performance metrics and analysis."""

import time
from typing import Dict, List, Optional, Callable, Any, Tuple
from dataclasses import dataclass
from collections import defaultdict
import numpy as np
import logging

from flare_ai_kit.common import Prediction
from flare_ai_kit.consensus.aggregator.base import BaseAggregator

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Metrics for evaluating aggregation performance."""
    accuracy: float
    confidence: float
    agreement_score: float
    prediction_entropy: float
    consensus_time: float
    agent_contributions: Dict[str, float]
    outlier_detection_rate: float
    cluster_info: Optional[Dict[str, Any]] = None


class AdvancedAggregator(BaseAggregator):
    """
    Advanced aggregator that supports multiple strategies and tracks performance metrics.
    """
    
    def __init__(self, 
                 strategy: Callable[[List[Prediction]], Prediction],
                 enable_metrics: bool = True,
                 enable_perturbation_testing: bool = False):
        """
        Initialize the advanced aggregator.
        
        Args:
            strategy: The aggregation strategy to use
            enable_metrics: Whether to collect performance metrics
            enable_perturbation_testing: Whether to test robustness with perturbations
        """
        super().__init__(strategy)
        self.enable_metrics = enable_metrics
        self.enable_perturbation_testing = enable_perturbation_testing
        
        # Performance tracking
        self.metrics_history: List[PerformanceMetrics] = []
        self.agent_performance: Dict[str, List[float]] = defaultdict(list)
        self.consensus_history: List[Dict[str, Any]] = []
        
        # Perturbation testing
        self.perturbation_results: List[Dict[str, Any]] = []
    
    def _calculate_prediction_entropy(self, predictions: List[Prediction]) -> float:
        """Calculate the entropy of prediction distribution."""
        if not predictions:
            return 0.0
        
        try:
            # Try to calculate entropy for numerical predictions
            values = [float(pred.prediction) for pred in predictions]
            # Discretize into bins for entropy calculation
            hist, _ = np.histogram(values, bins=min(len(values), 10))
            probs = hist / len(values)
            probs = probs[probs > 0]  # Remove zeros
            return float(-np.sum(probs * np.log2(probs)) if len(probs) > 0 else 0.0)
        except (ValueError, TypeError):
            # For text predictions, calculate based on unique values
            unique_predictions: Dict[str, int] = {}
            for pred in predictions:
                key = str(pred.prediction)
                unique_predictions[key] = unique_predictions.get(key, 0) + 1
            
            total = len(predictions)
            probs = [count / total for count in unique_predictions.values()]
            return float(-np.sum([p * np.log2(p) for p in probs if p > 0]))
    
    def _calculate_agreement_score(self, predictions: List[Prediction]) -> float:
        """Calculate agreement score between predictions."""
        if len(predictions) <= 1:
            return 1.0
        
        try:
            # For numerical predictions
            values = [float(pred.prediction) for pred in predictions]
            std_dev = np.std(values)
            mean_val = np.mean(values)
            # Normalize by mean to get coefficient of variation
            cv = float(std_dev / abs(mean_val) if mean_val != 0 else std_dev)
            return max(0.0, 1.0 - cv)
        except (ValueError, TypeError):
            # For text predictions, calculate based on exact matches
            unique_predictions = set(str(pred.prediction) for pred in predictions)
            return 1.0 - (len(unique_predictions) - 1) / len(predictions)
    
    def _calculate_agent_contributions(self, predictions: List[Prediction], 
                                     final_prediction: Prediction) -> Dict[str, float]:
        """Calculate each agent's contribution to the final prediction."""
        contributions: Dict[str, float] = {}
        
        # Check if strategy is a bound method with agent_contributions attribute
        if hasattr(self.strategy, '__self__') and hasattr(self.strategy.__self__, 'agent_contributions'):  # type: ignore
            # If strategy tracks contributions (like Shapley)
            contributions = self.strategy.__self__.agent_contributions.copy()  # type: ignore
        else:
            # Simple contribution based on confidence and similarity to final result
            for pred in predictions:
                try:
                    # Numerical similarity
                    pred_val = float(pred.prediction)
                    final_val = float(final_prediction.prediction)
                    similarity = 1.0 - abs(pred_val - final_val) / (abs(final_val) + 1e-8)
                    contributions[pred.agent_id] = similarity * pred.confidence
                except (ValueError, TypeError):
                    # Text similarity (exact match)
                    similarity = 1.0 if str(pred.prediction) == str(final_prediction.prediction) else 0.0
                    contributions[pred.agent_id] = similarity * pred.confidence
        
        return contributions
    
    def _test_perturbation_robustness(self, predictions: List[Prediction]) -> Dict[str, float]:
        """Test robustness by adding noise to predictions."""
        if not self.enable_perturbation_testing or len(predictions) < 2:
            return {"stability": 1.0}
        
        original_result = self.strategy(predictions)
        stability_scores: List[float] = []
        
        # Test with confidence perturbations
        for _ in range(5):
            perturbed_preds: List[Prediction] = []
            for pred in predictions:
                # Add small noise to confidence
                noise = np.random.normal(0, 0.1)
                new_confidence = max(0.0, min(1.0, pred.confidence + noise))
                perturbed_preds.append(Prediction(
                    agent_id=pred.agent_id,
                    prediction=pred.prediction,
                    confidence=new_confidence
                ))
            
            perturbed_result = self.strategy(perturbed_preds)
            
            # Calculate stability
            try:
                orig_val = float(original_result.prediction)
                pert_val = float(perturbed_result.prediction)
                stability = 1.0 - abs(orig_val - pert_val) / (abs(orig_val) + 1e-8)
            except (ValueError, TypeError):
                stability = 1.0 if str(original_result.prediction) == str(perturbed_result.prediction) else 0.0
            
            stability_scores.append(stability)
        
        return {
            "stability": float(np.mean(stability_scores)),
            "stability_std": float(np.std(stability_scores))
        }
    
    async def aggregate(self, predictions: List[Prediction]) -> Prediction:
        """
        Aggregate predictions with performance tracking.
        
        Args:
            predictions: List of predictions to aggregate
            
        Returns:
            Aggregated prediction with performance metrics
        """
        if not predictions:
            raise ValueError("No predictions to aggregate")
        
        start_time = time.time()
        
        # Run the actual aggregation
        result = self.strategy(predictions)
        
        consensus_time = time.time() - start_time
        
        if self.enable_metrics:
            # Calculate performance metrics
            agreement_score = self._calculate_agreement_score(predictions)
            prediction_entropy = self._calculate_prediction_entropy(predictions)
            agent_contributions = self._calculate_agent_contributions(predictions, result)
            
            # Test perturbation robustness if enabled
            perturbation_results = self._test_perturbation_robustness(predictions)
            
            # Count outliers (predictions with very low confidence relative to others)
            confidences = [pred.confidence for pred in predictions]
            mean_confidence = np.mean(confidences)
            std_confidence = np.std(confidences)
            outlier_threshold = mean_confidence - 2 * std_confidence
            outliers = sum(1 for conf in confidences if conf < outlier_threshold)
            outlier_rate = outliers / len(predictions) if predictions else 0.0
            
            # Extract cluster info if available
            cluster_info = None
            if hasattr(self.strategy, '__self__') and hasattr(self.strategy.__self__, 'cluster_history'):  # type: ignore
                cluster_info = self.strategy.__self__.cluster_history[-1] if self.strategy.__self__.cluster_history else None  # type: ignore
            
            # Create metrics object
            metrics = PerformanceMetrics(
                accuracy=result.confidence,  # Use confidence as proxy for accuracy
                confidence=result.confidence,
                agreement_score=agreement_score,
                prediction_entropy=prediction_entropy,
                consensus_time=consensus_time,
                agent_contributions=agent_contributions,
                outlier_detection_rate=outlier_rate,
                cluster_info=cluster_info
            )
            
            # Store metrics
            self.metrics_history.append(metrics)
            
            # Update agent performance tracking
            for agent_id, contribution in agent_contributions.items():
                self.agent_performance[agent_id].append(contribution)
                # Keep only recent history
                if len(self.agent_performance[agent_id]) > 100:
                    self.agent_performance[agent_id] = self.agent_performance[agent_id][-100:]
            
            # Store consensus history
            consensus_record: Dict[str, Any] = {
                "timestamp": time.time(),
                "n_predictions": len(predictions),
                "final_prediction": str(result.prediction),
                "final_confidence": result.confidence,
                "consensus_time": consensus_time,
                "agreement_score": agreement_score,
                "prediction_entropy": prediction_entropy,
                "perturbation_results": perturbation_results
            }
            self.consensus_history.append(consensus_record)
            
            # Keep only recent history
            if len(self.consensus_history) > 1000:
                self.consensus_history = self.consensus_history[-1000:]
            
            if len(self.metrics_history) > 100:
                self.metrics_history = self.metrics_history[-100:]
        
        return result
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get a summary of performance metrics."""
        if not self.metrics_history:
            return {"status": "No metrics available"}
        
        recent_metrics = self.metrics_history[-10:]  # Last 10 aggregations
        
        return {
            "average_confidence": np.mean([m.confidence for m in recent_metrics]),
            "average_agreement": np.mean([m.agreement_score for m in recent_metrics]),
            "average_entropy": np.mean([m.prediction_entropy for m in recent_metrics]),
            "average_consensus_time": np.mean([m.consensus_time for m in recent_metrics]),
            "average_outlier_rate": np.mean([m.outlier_detection_rate for m in recent_metrics]),
            "top_contributing_agents": self._get_top_agents(),
            "total_aggregations": len(self.metrics_history)
        }
    
    def _get_top_agents(self) -> List[Tuple[str, float]]:
        """Get top performing agents based on recent contributions."""
        agent_averages: Dict[str, float] = {}
        for agent_id, contributions in self.agent_performance.items():
            if contributions:
                agent_averages[agent_id] = float(np.mean(contributions[-10:]))  # Recent average
        
        # Sort by average contribution
        sorted_agents = sorted(agent_averages.items(), key=lambda x: x[1], reverse=True)
        return sorted_agents[:5]  # Top 5 agents
    
    def get_agent_performance(self, agent_id: str) -> Dict[str, Any]:
        """Get performance metrics for a specific agent."""
        if agent_id not in self.agent_performance:
            return {"status": "Agent not found"}
        
        contributions = self.agent_performance[agent_id]
        if not contributions:
            return {"status": "No performance data"}
        
        return {
            "average_contribution": np.mean(contributions),
            "contribution_trend": np.mean(contributions[-5:]) - np.mean(contributions[-10:-5]) if len(contributions) >= 10 else 0,
            "consistency": 1.0 - np.std(contributions) / (np.mean(contributions) + 1e-8),
            "total_participations": len(contributions)
        }