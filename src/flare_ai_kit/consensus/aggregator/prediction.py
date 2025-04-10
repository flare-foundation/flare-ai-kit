"""Interface for prediction type-validation."""

from pydantic import BaseModel


class Prediction(BaseModel):
    """Prediction from an agent."""

    agent_id: str
    prediction: float | str
    confidence: float = 1.0
