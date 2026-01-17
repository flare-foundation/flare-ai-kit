from __future__ import annotations

import pytest

from flare_ai_kit.common import Prediction
from flare_ai_kit.consensus.aggregator.strategies import (
    majority_vote,
    top_confidence,
    weighted_average,
)


@pytest.mark.parametrize(
    ("predictions", "expected"),
    [
        (
            [
                Prediction(agent_id="a1", prediction="A", confidence=0.8),
                Prediction(agent_id="a2", prediction="B", confidence=0.6),
            ],
            "A",
        ),
        (
            [
                Prediction(agent_id="x1", prediction="X", confidence=0.1),
                Prediction(agent_id="x2", prediction="Y", confidence=0.9),
                Prediction(agent_id="x3", prediction="Z", confidence=0.3),
            ],
            "Y",
        ),
    ],
)
def test_top_confidence(predictions: list[Prediction], expected: str) -> None:
    """Ensure the prediction with the highest confidence is returned."""
    assert top_confidence(predictions) == expected


@pytest.mark.parametrize(
    ("predictions", "expected"),
    [
        (
            [
                Prediction(agent_id="p1", prediction="yes", confidence=0.5),
                Prediction(agent_id="p2", prediction="yes", confidence=0.2),
                Prediction(agent_id="p3", prediction="no", confidence=0.3),
            ],
            "yes",
        ),
        (
            [
                Prediction(agent_id="c1", prediction="cat", confidence=0.1),
                Prediction(agent_id="d1", prediction="dog", confidence=0.2),
                Prediction(agent_id="d2", prediction="dog", confidence=0.3),
            ],
            "dog",
        ),
    ],
)
def test_majority_vote(predictions: list[Prediction], expected: str) -> None:
    """Ensure the most common prediction is returned, regardless of confidence."""
    assert majority_vote(predictions) == expected


def test_weighted_average_with_weights() -> None:
    """Check weighted average when total confidence > 0."""
    preds: list[Prediction] = [
        Prediction(agent_id="w1", prediction=1.0, confidence=0.5),
        Prediction(agent_id="w2", prediction=3.0, confidence=1.0),
    ]
    expected = (1.0 * 0.5 + 3.0 * 1.0) / (0.5 + 1.0)
    assert pytest.approx(weighted_average(preds)) == expected


def test_weighted_average_zero_weight() -> None:
    """If all confidences are zero, use simple mean of predictions."""
    preds: list[Prediction] = [
        Prediction(agent_id="z1", prediction=2.0, confidence=0.0),
        Prediction(agent_id="z2", prediction=4.0, confidence=0.0),
    ]
    assert pytest.approx(weighted_average(preds)) == 3.0
