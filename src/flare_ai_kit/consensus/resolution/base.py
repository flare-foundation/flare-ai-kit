"""Base classes for conflict resolution in multi-agent consensus."""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any

try:
    from pydantic import BaseModel as _PydanticBaseModel

    class BaseModel(_PydanticBaseModel):  # type: ignore[misc]
        """Base model using pydantic."""

        class Config:
            """Pydantic configuration."""

            arbitrary_types_allowed = True

except ImportError:
    # Fallback for when pydantic is not available
    class BaseModel:  # type: ignore[misc]
        """Fallback BaseModel when pydantic is not available."""

        def __init__(self, **kwargs: Any) -> None:
            for key, value in kwargs.items():
                setattr(self, key, value)


from flare_ai_kit.common.schemas import Prediction


class ConflictType(str, Enum):
    """Types of conflicts that can occur between agent predictions."""

    VALUE_DISAGREEMENT = "value_disagreement"  # Different prediction values
    CONFIDENCE_MISMATCH = "confidence_mismatch"  # High confidence on conflicting values
    OUTLIER_DETECTION = "outlier_detection"  # One agent significantly differs
    TEMPORAL_INCONSISTENCY = "temporal_inconsistency"  # Predictions change over time
    EXPERTISE_CONFLICT = "expertise_conflict"  # Domain experts disagree
    SYSTEMATIC_BIAS = "systematic_bias"  # Consistent patterns of disagreement


class ConflictSeverity(str, Enum):
    """Severity levels for conflicts."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ConflictContext(BaseModel):  # type: ignore[misc]
    """Context information for conflict resolution."""

    task_id: str
    conflict_type: ConflictType
    severity: ConflictSeverity
    conflicting_predictions: list[Prediction]
    metadata: dict[str, Any] = {}  # type: ignore[assignment,misc]  # noqa: RUF012


class ResolutionResult(BaseModel):  # type: ignore[misc]
    """Result of conflict resolution process."""

    resolved_prediction: Prediction
    resolution_method: str
    confidence_adjustment: float = 0.0
    rationale: str = ""
    additional_info: dict[str, Any] = {}  # type: ignore[assignment,misc]  # noqa: RUF012


class BaseConflictDetector(ABC):
    """Abstract base class for detecting conflicts between predictions."""

    @abstractmethod
    async def detect_conflicts(
        self, predictions: list[Prediction], context: dict[str, Any] | None = None
    ) -> list[ConflictContext]:
        """Detect conflicts in a set of predictions."""


class BaseConflictResolver(ABC):
    """Abstract base class for resolving conflicts between predictions."""

    @abstractmethod
    async def resolve_conflict(self, conflict: ConflictContext) -> ResolutionResult:
        """Resolve a specific conflict."""

    @abstractmethod
    def can_handle(self, conflict_type: ConflictType) -> bool:
        """Check if this resolver can handle a specific conflict type."""


class BaseNegotiationProtocol(ABC):
    """Abstract base class for agent negotiation protocols."""

    @abstractmethod
    async def negotiate(
        self, agent_ids: list[str], conflict: ConflictContext, max_rounds: int = 3
    ) -> ResolutionResult:
        """Conduct negotiation between conflicting agents."""
