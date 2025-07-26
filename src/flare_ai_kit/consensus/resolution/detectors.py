"""Conflict detection implementations for multi-agent consensus."""

import statistics
from typing import Any

from flare_ai_kit.common.schemas import Prediction
from flare_ai_kit.consensus.resolution.base import (
    BaseConflictDetector,
    ConflictContext,
    ConflictSeverity,
    ConflictType,
)

# Constants for conflict detection
MIN_PREDICTIONS_FOR_ANALYSIS = 2
MIN_EXPERTS_FOR_CONFLICT = 2
EXPERTISE_THRESHOLD = 0.7
MIN_OUTLIER_DETECTION_SIZE = 3
CRITICAL_CV_THRESHOLD = 0.8
HIGH_CV_THRESHOLD = 0.5
MEDIUM_CV_THRESHOLD = 0.3


class StatisticalConflictDetector(BaseConflictDetector):
    """Detects conflicts using statistical analysis of predictions."""

    def __init__(
        self,
        disagreement_threshold: float = 0.3,
        confidence_threshold: float = 0.8,
        outlier_threshold: float = 2.0,
    ) -> None:
        self.disagreement_threshold = disagreement_threshold
        self.confidence_threshold = confidence_threshold
        self.outlier_threshold = outlier_threshold

    async def detect_conflicts(
        self, predictions: list[Prediction], context: dict[str, Any] | None = None
    ) -> list[ConflictContext]:
        """Detect statistical conflicts in predictions."""
        if len(predictions) < MIN_PREDICTIONS_FOR_ANALYSIS:
            return []

        conflicts: list[ConflictContext] = []
        task_id = context.get("task_id", "unknown") if context else "unknown"

        # Check for value disagreements
        value_conflicts = self._detect_value_disagreements(predictions, task_id)
        conflicts.extend(value_conflicts)

        # Check for confidence mismatches
        confidence_conflicts = self._detect_confidence_mismatches(predictions, task_id)
        conflicts.extend(confidence_conflicts)

        # Check for outliers
        outlier_conflicts = self._detect_outliers(predictions, task_id)
        conflicts.extend(outlier_conflicts)

        return conflicts

    def _detect_value_disagreements(
        self, predictions: list[Prediction], task_id: str
    ) -> list[ConflictContext]:
        """Detect disagreements in prediction values."""
        conflicts: list[ConflictContext] = []

        # For numerical predictions
        numerical_preds: list[Prediction] = []
        string_preds: list[Prediction] = []

        for pred in predictions:
            if isinstance(pred.prediction, (int, float)):
                numerical_preds.append(pred)
            else:
                string_preds.append(pred)

        # Handle numerical disagreements
        if len(numerical_preds) >= MIN_PREDICTIONS_FOR_ANALYSIS:
            values = [float(p.prediction) for p in numerical_preds]
            if len(set(values)) > 1:  # Different values exist
                std_dev = statistics.stdev(values)
                mean_val = statistics.mean(values)

                if std_dev / max(abs(mean_val), 1) > self.disagreement_threshold:
                    severity = self._calculate_severity(std_dev, mean_val)
                    conflicts.append(
                        ConflictContext(
                            task_id=task_id,
                            conflict_type=ConflictType.VALUE_DISAGREEMENT,
                            severity=severity,
                            conflicting_predictions=numerical_preds,
                            metadata={
                                "std_dev": std_dev,
                                "mean": mean_val,
                                "coefficient_of_variation": std_dev
                                / max(abs(mean_val), 1),
                            },
                        )
                    )

        # Handle string disagreements
        if len(string_preds) >= MIN_PREDICTIONS_FOR_ANALYSIS:
            unique_values = {str(p.prediction) for p in string_preds}
            if len(unique_values) > 1:
                conflicts.append(
                    ConflictContext(
                        task_id=task_id,
                        conflict_type=ConflictType.VALUE_DISAGREEMENT,
                        severity=ConflictSeverity.MEDIUM,
                        conflicting_predictions=string_preds,
                        metadata={
                            "unique_values": list(unique_values),
                            "value_distribution": {
                                val: sum(
                                    1 for p in string_preds if str(p.prediction) == val
                                )
                                for val in unique_values
                            },
                        },
                    )
                )

        return conflicts

    def _detect_confidence_mismatches(
        self, predictions: list[Prediction], task_id: str
    ) -> list[ConflictContext]:
        """Detect mismatches between high confidence and disagreeing values."""
        conflicts: list[ConflictContext] = []

        # Find high-confidence predictions that disagree
        high_conf_preds = [
            p for p in predictions if p.confidence >= self.confidence_threshold
        ]

        if len(high_conf_preds) >= MIN_PREDICTIONS_FOR_ANALYSIS:
            # Check if high-confidence predictions have different values
            values = [str(p.prediction) for p in high_conf_preds]
            if len(set(values)) > 1:
                conflicts.append(
                    ConflictContext(
                        task_id=task_id,
                        conflict_type=ConflictType.CONFIDENCE_MISMATCH,
                        severity=ConflictSeverity.HIGH,
                        conflicting_predictions=high_conf_preds,
                        metadata={
                            "min_confidence": min(
                                p.confidence for p in high_conf_preds
                            ),
                            "max_confidence": max(
                                p.confidence for p in high_conf_preds
                            ),
                            "disagreeing_values": list(set(values)),
                        },
                    )
                )

        return conflicts

    def _detect_outliers(
        self, predictions: list[Prediction], task_id: str
    ) -> list[ConflictContext]:
        """Detect outlier predictions using statistical methods."""
        conflicts: list[ConflictContext] = []

        # Only works for numerical predictions
        numerical_preds = [
            p for p in predictions if isinstance(p.prediction, (int, float))
        ]

        if len(numerical_preds) < MIN_OUTLIER_DETECTION_SIZE:
            return conflicts

        values = [float(p.prediction) for p in numerical_preds]
        mean_val = statistics.mean(values)
        std_dev = statistics.stdev(values) if len(values) > 1 else 0

        if std_dev == 0:
            return conflicts

        outliers: list[Prediction] = []
        for pred in numerical_preds:
            z_score = abs((float(pred.prediction) - mean_val) / std_dev)
            if z_score > self.outlier_threshold:
                outliers.append(pred)

        if outliers:
            conflicts.append(
                ConflictContext(
                    task_id=task_id,
                    conflict_type=ConflictType.OUTLIER_DETECTION,
                    severity=ConflictSeverity.MEDIUM,
                    conflicting_predictions=outliers,
                    metadata={
                        "z_scores": {
                            p.agent_id: abs((float(p.prediction) - mean_val) / std_dev)
                            for p in outliers
                        },
                        "population_mean": mean_val,
                        "population_std": std_dev,
                    },
                )
            )

        return conflicts

    def _calculate_severity(self, std_dev: float, mean_val: float) -> ConflictSeverity:
        """Calculate conflict severity based on statistical measures."""
        cv = std_dev / max(abs(mean_val), 1)

        if cv > CRITICAL_CV_THRESHOLD:
            return ConflictSeverity.CRITICAL
        if cv > HIGH_CV_THRESHOLD:
            return ConflictSeverity.HIGH
        if cv > MEDIUM_CV_THRESHOLD:
            return ConflictSeverity.MEDIUM
        return ConflictSeverity.LOW


class DomainConflictDetector(BaseConflictDetector):
    """Detects conflicts based on domain expertise and historical patterns."""

    def __init__(
        self, agent_expertise: dict[str, dict[str, float]] | None = None
    ) -> None:
        self.agent_expertise = agent_expertise or {}

    async def detect_conflicts(
        self, predictions: list[Prediction], context: dict[str, Any] | None = None
    ) -> list[ConflictContext]:
        """Detect conflicts based on domain expertise."""
        if len(predictions) < MIN_PREDICTIONS_FOR_ANALYSIS:
            return []

        conflicts: list[ConflictContext] = []
        task_id = context.get("task_id", "unknown") if context else "unknown"
        domain = context.get("domain", "general") if context else "general"

        # Find expert disagreements
        expert_conflicts = self._detect_expert_disagreements(
            predictions, task_id, domain
        )
        conflicts.extend(expert_conflicts)

        return conflicts

    def _detect_expert_disagreements(
        self, predictions: list[Prediction], task_id: str, domain: str
    ) -> list[ConflictContext]:
        """Detect when domain experts disagree."""
        conflicts: list[ConflictContext] = []

        # Find experts in this domain
        expert_preds: list[tuple[Prediction, float]] = []
        for pred in predictions:
            expertise = self.agent_expertise.get(pred.agent_id, {}).get(domain, 0.0)
            if expertise > EXPERTISE_THRESHOLD:  # High expertise threshold
                expert_preds.append((pred, expertise))

        if len(expert_preds) < MIN_EXPERTS_FOR_CONFLICT:
            return conflicts

        # Check if experts disagree
        expert_values = [str(pred.prediction) for pred, _ in expert_preds]
        if len(set(expert_values)) > 1:
            conflicts.append(
                ConflictContext(
                    task_id=task_id,
                    conflict_type=ConflictType.EXPERTISE_CONFLICT,
                    severity=ConflictSeverity.HIGH,
                    conflicting_predictions=[pred for pred, _ in expert_preds],
                    metadata={
                        "domain": domain,
                        "expert_scores": {
                            pred.agent_id: expertise for pred, expertise in expert_preds
                        },
                        "disagreeing_values": list(set(expert_values)),
                    },
                )
            )

        return conflicts
