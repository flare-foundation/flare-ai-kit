"""Core consensus engine for orchestrating agents and aggregating results."""

from flare_ai_kit.common import Prediction
from flare_ai_kit.consensus.aggregator.base import BaseAggregator
from flare_ai_kit.consensus.coordinator.base import BaseCoordinator


class ConsensusEngine:
    """Orchestrates task distribution and result aggregation."""

    def __init__(
        self, coordinator: BaseCoordinator, aggregator: BaseAggregator
    ) -> None:
        """
        Initializes the ConsensusEngine.

        Args:
            coordinator: An instance of a Coordinator to manage agents.
            aggregator: An instance of an Aggregator to process predictions.

        """
        self.coordinator = coordinator
        self.aggregator = aggregator

    async def run(self, task: str) -> Prediction:
        """
        Executes the consensus process for a given task.

        This method involves three main steps:
        1. Distributing the task to all agents via the coordinator.
        2. Processing the raw results from the agents.
        3. Aggregating the processed predictions to reach a consensus.

        Args:
            task: The task description to be performed by the agents.

        Returns:
            A Prediction object representing the consensus result.

        """
        # 1. Distribute task to agents
        raw_predictions = await self.coordinator.distribute_task(task)

        # 2. Process results into a standard format
        structured_predictions = await self.coordinator.process_results(raw_predictions)

        # 3. Aggregate predictions to get a final consensus
        return await self.aggregator.aggregate(structured_predictions)
