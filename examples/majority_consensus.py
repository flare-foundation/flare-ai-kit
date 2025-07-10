"""Example of using the consensus engine to achieve consensus among multiple AI agents. 

Here every AI model is a mock LLM, designed to simulate what responses an LLM could give (based on an OpenRouter approach). In this case there is one prompt and different consensus strategies are applied to the output to get a final answer.
"""

import asyncio
from typing import List, Callable
from dataclasses import dataclass
from collections import Counter

from flare_ai_kit.common import Prediction
from flare_ai_kit.consensus.aggregator import BaseAggregator, majority_vote


@dataclass
class MockLLM:
    """Mock LLM class for demonstration purposes. This simulates responses that could hypothetically be given by an LLM. 
    In practice when using custom tarined models, the responses follow a similar sturcture. The confidence can be obtained by looking at the probability distributions outputted by the model.
    These confidence scores are not highly applicable to the LLM openrouter based approach, however they are included in this example for completeness
    The bias parameter is used to simulate different LLMs with different biases. This is done for testing purposes.
    To test the aggregator with your actual LLMs, replace this class with an implementation that calls different LLMs from OpenRouter.
    """
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


def majority_vote_strategy(predictions: List[Prediction]) -> Prediction:
    result = majority_vote(predictions)
    avg_confidence = sum(p.confidence for p in predictions) / len(predictions)
    return Prediction(
        agent_id="consensus",
        prediction=result,
        confidence=avg_confidence
    )


class ConsensusAggregator(BaseAggregator):
    def __init__(self, strategy: Callable[[List[Prediction]], Prediction]) -> None:
        super().__init__(strategy)
    async def aggregate(self, predictions: List[Prediction]) -> Prediction:
        return self.strategy(predictions)




# The following prompt is a twist on the classic Monty Hall problem. LLMs have to be careful. Try it out!
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


async def majority_vote_example():
    # Create a list of LLMs with different biases. Mock set.
    llms = [
        MockLLM("GPT-4", "switch"), # GPT-4 is biased to switch
        MockLLM("Claude", "keep"), # Claude is biased to keep
        MockLLM("Gemini", "neutral"), # Gemini is neutral
        MockLLM("Llama", "switch"), # Llama is biased to switch
        MockLLM("Mistral", "neutral"), # Mistral is neutral
    ]
    aggregator = ConsensusAggregator(majority_vote_strategy)
    print("🤖 Monty Hall Problem Consensus Example")
    print("=" * 50)
    print(f"Prompt: {example_prompt.strip()}")
    print("\n📊 Individual LLM Predictions:")
    print("-" * 30)
    predictions: List[Prediction] = []
    for llm in llms:
        prediction = await llm.predict(example_prompt)
        predictions.append(prediction)
        print(f"{llm.name:>10}: {prediction.prediction} (confidence: {prediction.confidence:.2f})")
    consensus_result = await aggregator.aggregate(predictions)
    print("\n🎯 Consensus Result:")
    print("-" * 30)
    print(f"Strategy: Majority Vote")
    print(f"Result: {consensus_result.prediction}")
    print(f"Confidence: {consensus_result.confidence:.2f}")
    vote_counts = Counter(p.prediction for p in predictions)
    print(f"\n📈 Vote Breakdown:")
    for vote, count in vote_counts.most_common():
        print(f"  {vote}: {count} votes")





if __name__ == "__main__":
    asyncio.run(majority_vote_example())