from unittest.mock import AsyncMock

import pytest

from flare_ai_kit.common.schemas import Prediction
from flare_ai_kit.consensus.engine import ConsensusEngine


@pytest.mark.asyncio
async def test_run_executes_all_steps_in_order():
    # --- Arrange ---
    # Fake predictions that agents might return
    raw_predictions = ["raw1", "raw2"]
    structured_predictions = [
        Prediction(agent_id="a1", prediction="yes", confidence=0.8),
        Prediction(agent_id="a2", prediction="no", confidence=0.6),
    ]
    final_prediction = Prediction(agent_id="agg", prediction="yes", confidence=0.9)

    # Coordinator mock with async methods
    mock_coordinator = AsyncMock()
    mock_coordinator.distribute_task.return_value = raw_predictions
    mock_coordinator.process_results.return_value = structured_predictions

    # Aggregator mock
    mock_aggregator = AsyncMock()
    mock_aggregator.aggregate.return_value = final_prediction

    engine = ConsensusEngine(coordinator=mock_coordinator, aggregator=mock_aggregator)

    # --- Act ---
    result = await engine.run("classify sample")

    # --- Assert ---
    # Verify returned Prediction is the aggregator's result
    assert isinstance(result, Prediction)
    assert result.prediction == "yes"
    assert result.confidence == 0.9

    # Check that methods were awaited in sequence
    mock_coordinator.distribute_task.assert_awaited_once_with("classify sample")
    mock_coordinator.process_results.assert_awaited_once_with(raw_predictions)
    mock_aggregator.aggregate.assert_awaited_once_with(structured_predictions)


@pytest.mark.asyncio
async def test_run_handles_empty_results():
    # Coordinator returns no predictions
    mock_coordinator = AsyncMock()
    mock_coordinator.distribute_task.return_value = []
    mock_coordinator.process_results.return_value = []
    mock_aggregator = AsyncMock()
    # Aggregator still returns a fallback prediction
    fallback = Prediction(agent_id="agg", prediction="unknown", confidence=0.0)
    mock_aggregator.aggregate.return_value = fallback

    engine = ConsensusEngine(mock_coordinator, mock_aggregator)

    result = await engine.run("empty task")

    assert result.prediction == "unknown"
    mock_coordinator.distribute_task.assert_awaited_once()
    mock_coordinator.process_results.assert_awaited_once()
    mock_aggregator.aggregate.assert_awaited_once()
