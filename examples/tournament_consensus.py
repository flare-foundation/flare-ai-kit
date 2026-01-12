"""Example of using the tournament elimination consensus strategy.

This example demonstrates how to use the tournament elimination strategy with meta-agent
arbitration and chain-of-thought reasoning. The strategy pits predictions against each
other in elimination rounds, with a meta-agent evaluating each match.
"""

import asyncio
from typing import List
from dataclasses import dataclass

from flare_ai_kit.common import Prediction
from flare_ai_kit.consensus.aggregator import BaseAggregator
from flare_ai_kit.consensus.aggregator.tournament_strategies import async_tournament_elimination


@dataclass
class MockLLM:
    """Mock LLM class for demonstration purposes."""
    name: str
    bias: str = "neutral"  # Can be "switch", "keep", "neutral"
    
    async def predict(self, prompt: str) -> Prediction:
        import random
        if self.bias == "switch":
            response = "<SWITCH>"
            confidence = 0.9
        elif self.bias == "keep":
            response = "<KEEP>"
            confidence = 0.8
        else:
            responses = ["<SWITCH>", "<KEEP>", "<NO DIFFERENCE>"]
            response = random.choice(responses)
            confidence = random.uniform(0.6, 0.9)
        return Prediction(
            agent_id=self.name,
            prediction=response,
            confidence=confidence
        )


class TournamentAggregator(BaseAggregator):
    """Tournament-based consensus aggregator."""
    
    def __init__(self) -> None:
        # Initialize with a dummy strategy since we override aggregate
        super().__init__(strategy=lambda predictions: Prediction("dummy", "dummy", 0.0))
    
    async def aggregate(self, predictions: List[Prediction], prompt: str = "") -> Prediction:
        """Aggregate predictions using tournament elimination strategy."""
        result = await async_tournament_elimination(predictions, prompt)
        avg_confidence = sum(p.confidence for p in predictions) / len(predictions)
        return Prediction(
            agent_id="tournament_consensus",
            prediction=result,
            confidence=avg_confidence
        )


# The same twisted Monty Hall problem prompt from the original example
example_prompt = """
Imagine you're on a game show, and there are three doors in front of you. Behind one door is a car, and behind the other two doors are goats. You don't know what's behind any of the doors. You get to choose one door. Let's say you pick Door #1. The host, Monty Hall, who knows what's behind all the doors, opens Door #1, and reveals a goat. Now, you have two doors left: Door #3 and Door #2. You pick Door #3. Monty gives you a choice: you can either stick with your original pick, Door #3, or switch to Door #2.
What do you do to maximize your chances of winning the car?

Answer with one of these three tokens: 
<SWITCH> 
Pick <SWITCH> if you should switch to Door #2
<KEEP> 
Pick <KEEP> if you should stick with your original pick, Door #3.
<NO DIFFERENCE> 
Pick <NO DIFFERENCE> if neither option gives an advantage.

 Simply answer with the token, no other text.
"""


async def tournament_example():
    """Demonstrate tournament elimination consensus strategy."""
    
    # Create a diverse set of LLMs with different biases
    llms = [
        MockLLM("GPT-4", "switch"),      # GPT-4 is biased to switch
        MockLLM("Claude", "keep"),        # Claude is biased to keep
        MockLLM("Gemini", "neutral"),     # Gemini is neutral
        MockLLM("Llama", "switch"),       # Llama is biased to switch
        MockLLM("Mistral", "neutral"),    # Mistral is neutral
        MockLLM("PaLM", "keep"),          # PaLM is biased to keep
        MockLLM("Bard", "switch"),        # Bard is biased to switch
        MockLLM("Anthropic", "neutral"),  # Anthropic is neutral
    ]
    
    aggregator = TournamentAggregator()
    
    print("🏆 Tournament Elimination Consensus Example")
    print("=" * 60)
    print(f"Prompt: {example_prompt.strip()}")
    print(f"\n🎯 Tournament Participants: {len(llms)} LLMs")
    print("-" * 40)
    
    # Get predictions from all LLMs
    predictions: List[Prediction] = []
    for llm in llms:
        prediction = await llm.predict(example_prompt)
        predictions.append(prediction)
        print(f"{llm.name:>12}: {prediction.prediction} (confidence: {prediction.confidence:.2f})")
    
    print("\n⚔️  Tournament Bracket:")
    print("-" * 40)
    
    # Simulate tournament rounds
    current_round = predictions.copy()
    round_num = 1
    
    while len(current_round) > 1:
        print(f"\n🏁 Round {round_num}:")
        matches: List[str] = []
        
        # Create matches for this round
        for i in range(0, len(current_round), 2):
            if i + 1 < len(current_round):
                match: str = f"{current_round[i].agent_id} vs {current_round[i + 1].agent_id}"
                matches.append(match)
                print(f"  Match {len(matches)}: {match}")
            else:
                # Bye for odd participant
                print(f"  Bye: {current_round[i].agent_id}")
        
        # Simulate winners (in practice, this would be determined by meta-agent)
        winners: List[Prediction] = []
        for i in range(0, len(current_round), 2):
            if i + 1 < len(current_round):
                # Simulate winner selection (in practice, meta-agent would decide)
                winner: Prediction = current_round[i] if current_round[i].confidence > current_round[i + 1].confidence else current_round[i + 1]
                winners.append(winner)
            else:
                winners.append(current_round[i])
        
        current_round = winners
        round_num += 1
    
    # Get final consensus result
    consensus_result = await aggregator.aggregate(predictions, example_prompt)
    
    print(f"\n🏆 Tournament Champion:")
    print("-" * 40)
    print(f"Winner: {current_round[0].agent_id}")
    print(f"Final Answer: {consensus_result.prediction}")
    print(f"Average Confidence: {consensus_result.confidence:.2f}")
    
    # Show vote distribution
    from collections import Counter
    vote_counts = Counter(p.prediction for p in predictions)
    print(f"\n📊 Initial Vote Distribution:")
    for vote, count in vote_counts.most_common():
        print(f"  {vote}: {count} votes")
    
    print(f"\n💡 Tournament Strategy Benefits:")
    print("-" * 40)
    print("• Eliminates weak reasoning through head-to-head matches")
    print("• Meta-agent provides detailed justifications for each decision")
    print("• Chain-of-thought reasoning ensures logical consistency")
    print("• Penalizes inconsistencies and rewards coherent arguments")
    print("• Scales well with larger numbers of participants")


if __name__ == "__main__":
    asyncio.run(tournament_example()) 