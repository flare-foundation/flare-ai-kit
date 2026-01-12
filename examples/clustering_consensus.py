"""Example of using semantic clustering consensus strategy for hallucination detection.

This example demonstrates how to use semantic clustering to detect and filter out
hallucinated responses from LLMs. The strategy groups similar responses together
and identifies outliers that may be hallucinations.
"""

import asyncio
import numpy as np
from typing import List
from dataclasses import dataclass
import random
from sklearn.feature_extraction.text import TfidfVectorizer  # type: ignore
from sklearn.metrics.pairwise import cosine_similarity  # type: ignore

from flare_ai_kit.common import Prediction
from flare_ai_kit.consensus.aggregator import BaseAggregator
from flare_ai_kit.consensus.aggregator.advanced_strategies import (
    semantic_clustering_strategy,
    robust_consensus_strategy
)
from flare_ai_kit.rag.vector.embedding.base import BaseEmbedding


class TFIDFEmbeddingModel(BaseEmbedding):
    """Real TF-IDF embedding model for semantic similarity."""
    
    def __init__(self, max_features: int = 1000):
        self.max_features = max_features
        self.vectorizer = TfidfVectorizer(
            max_features=max_features,
            stop_words='english',
            ngram_range=(1, 2),
            min_df=1,
            max_df=0.9
        )
        self.is_fitted = False
    
    def embed_content(
        self,
        contents: str | list[str],
        title: str | None = None,
        task_type: str | None = None,
    ) -> list[list[float]]:
        """Generate TF-IDF embeddings for text content."""
        if isinstance(contents, str):
            contents = [contents]
        
        if not self.is_fitted:
            # Fit the vectorizer on the first batch
            self.vectorizer.fit(contents)  # type: ignore
            self.is_fitted = True
        
        # Transform the content to TF-IDF vectors
        tfidf_matrix = self.vectorizer.transform(contents)  # type: ignore
        
        # Convert to dense arrays and normalize
        embeddings = tfidf_matrix.toarray()  # type: ignore
        
        # Normalize to unit vectors for cosine similarity
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)  # type: ignore
        norms = np.where(norms == 0, 1, norms)  # Avoid division by zero
        embeddings = embeddings / norms  # type: ignore
        
        return embeddings.tolist()  # type: ignore


@dataclass
class MockLLM:
    """Mock LLM that simulates different types of responses including hallucinations."""
    
    name: str
    response_type: str = "realistic"  # "realistic", "hallucinated", "mixed"
    
    async def predict(self, prompt: str) -> Prediction:
        """Generate a prediction based on the response type."""
        if self.response_type == "realistic":
            # Realistic response acknowledging the study doesn't exist
            responses = [
                "I need to clarify that I cannot find any record of a 2019 study by Dr. Sarah Chen at MIT establishing a 'Chen-Rodriguez Protocol' for quantum error correction in biological systems. This appears to be a fictional study.",
                "There is no documented 2019 study by Dr. Sarah Chen at MIT about quantum error correction in biological systems. The 'Chen-Rodriguez Protocol' mentioned does not exist in scientific literature.",
                "I cannot verify the existence of this 2019 study. Dr. Sarah Chen and the 'Chen-Rodriguez Protocol' for quantum error correction in biological systems are not found in scientific databases."
            ]
            response = random.choice(responses)
            confidence = random.uniform(0.8, 0.95)
            
        elif self.response_type == "hallucinated":
            # Hallucinated response with fake details
            responses = [
                "The 2019 study by Dr. Sarah Chen at MIT was extremely well-received, achieving a 94% approval rating in peer reviews. The Chen-Rodriguez Protocol has been cited over 2,300 times and has applications in quantum computing, medicine, and AI.",
                "Dr. Sarah Chen's landmark 2019 study at MIT revolutionized quantum error correction. The Chen-Rodriguez Protocol received the prestigious Nobel Prize nomination and has been implemented in over 50 research institutions worldwide.",
                "The Chen-Rodriguez Protocol from Dr. Sarah Chen's 2019 MIT study was groundbreaking. It achieved 99.7% accuracy in quantum error correction and has been adopted by major tech companies including Google, IBM, and Microsoft."
            ]
            response = random.choice(responses)
            confidence = random.uniform(0.7, 0.9)  # High confidence in false information
            
        else:  # mixed
            # Mixed response with some truth and some fiction
            responses = [
                "While there have been studies on quantum error correction, I cannot find specific evidence of Dr. Sarah Chen's 2019 study at MIT. However, quantum error correction research has been active in recent years.",
                "The field of quantum error correction has seen significant progress, though I cannot verify the specific 'Chen-Rodriguez Protocol' mentioned. MIT has indeed been involved in quantum computing research.",
                "Quantum error correction is a real field of study, but the specific 2019 study by Dr. Sarah Chen and the 'Chen-Rodriguez Protocol' are not documented in scientific literature."
            ]
            response = random.choice(responses)
            confidence = random.uniform(0.6, 0.8)
        
        return Prediction(
            agent_id=self.name,
            prediction=response,
            confidence=confidence
        )


class ClusteringAggregator(BaseAggregator):
    """Aggregator that uses semantic clustering for consensus."""
    
    def __init__(self, embedding_model: BaseEmbedding, strategy: str = "semantic"):
        self.embedding_model = embedding_model
        self.strategy_name = strategy  # Store the strategy name separately
        # Create a strategy function that uses the clustering strategy
        def clustering_strategy(predictions: List[Prediction]) -> Prediction:
            return self._cluster_strategy(predictions)
        super().__init__(clustering_strategy)
    
    def _cluster_strategy(self, predictions: List[Prediction]) -> Prediction:
        """Apply clustering strategy to predictions."""
        if self.strategy_name == "semantic":
            return semantic_clustering_strategy(predictions, self.embedding_model)
        elif self.strategy_name == "robust":
            return robust_consensus_strategy(predictions, self.embedding_model)
        else:
            raise ValueError(f"Unknown strategy: {self.strategy_name}")
    
    async def aggregate(self, predictions: List[Prediction]) -> Prediction:
        """Aggregate predictions using clustering strategy."""
        return self._cluster_strategy(predictions)


# The prompt is designed to test hallucination detection
example_prompt = """
How well-received was the landmark 2019 study by Dr. Sarah Chen at MIT that established the 'Chen-Rodriguez Protocol' for quantum error correction in biological systems? Many have suggested its applicability to a plethora of fields.

Please provide a detailed response about this study's reception, impact, and applications.
"""


async def clustering_consensus_example():
    """Demonstrate semantic clustering consensus for hallucination detection."""
    
    # Create embedding model
    embedding_model = TFIDFEmbeddingModel(max_features=1000)
    
    # Create LLMs with different response patterns
    llms = [
        MockLLM("GPT-4", "realistic"),
        MockLLM("Claude", "realistic"),
        MockLLM("Gemini", "realistic"),
        MockLLM("Hallucinator-1", "hallucinated"),
        MockLLM("Hallucinator-2", "hallucinated"),
        MockLLM("Mixed-Response-1", "mixed"),
        MockLLM("Mixed-Response-2", "mixed"),
        MockLLM("Realistic-4", "realistic"),
    ]
    
    print("🔍 Semantic Clustering Consensus for Hallucination Detection")
    print("=" * 70)
    print(f"Prompt: {example_prompt.strip()}")
    print("\n📊 Individual LLM Predictions:")
    print("-" * 50)
    
    # Collect predictions
    predictions: List[Prediction] = []
    for llm in llms:
        prediction = await llm.predict(example_prompt)
        predictions.append(prediction)
        
        # Truncate long responses for display
        prediction_str = str(prediction.prediction)
        display_text = prediction_str[:100] + "..." if len(prediction_str) > 100 else prediction_str
        print(f"{llm.name:>15}: {display_text}")
        print(f"{'':>15}  Confidence: {prediction.confidence:.2f}")
        print()
    
    # Test different clustering strategies
    strategies = ["semantic", "robust"]
    
    for strategy in strategies:
        print(f"\n🎯 {strategy.title()} Clustering Consensus:")
        print("-" * 40)
        
        aggregator = ClusteringAggregator(embedding_model, strategy)
        consensus_result = await aggregator.aggregate(predictions)
        
        # Truncate for display
        result_str = str(consensus_result.prediction)
        display_text = result_str[:150] + "..." if len(result_str) > 150 else result_str
        print(f"Strategy: {strategy.title()} Clustering")
        print(f"Result: {display_text}")
        print(f"Confidence: {consensus_result.confidence:.2f}")
        print(f"Agent ID: {consensus_result.agent_id}")
    
    # Demonstrate direct use of advanced strategies
    print(f"\n🔬 Direct Strategy Comparison:")
    print("-" * 40)
    
    from flare_ai_kit.consensus.aggregator.advanced_strategies import (
        semantic_clustering_strategy,
        shapley_value_strategy,
        entropy_based_strategy
    )
    
    # Test semantic clustering directly
    semantic_result = semantic_clustering_strategy(predictions, embedding_model)
    print(f"Semantic Clustering: {str(semantic_result.prediction)[:100]}...")
    print(f"Confidence: {semantic_result.confidence:.2f}")
    
    # Test Shapley value strategy
    shapley_result = shapley_value_strategy(predictions, embedding_model)
    print(f"Shapley Value: {str(shapley_result.prediction)[:100]}...")
    print(f"Confidence: {shapley_result.confidence:.2f}")
    
    # Test entropy-based strategy
    entropy_result = entropy_based_strategy(predictions, embedding_model)
    print(f"Entropy-Based: {str(entropy_result.prediction)[:100]}...")
    print(f"Confidence: {entropy_result.confidence:.2f}")
    
    print("\n📈 Analysis:")
    print("-" * 20)
    print("• Realistic responses should cluster together")
    print("• Hallucinated responses should be identified as outliers")
    print("• Mixed responses may fall in between")
    print("• The dominant cluster should contain the most reliable responses")
    print("\n🔧 Advanced Strategy Features:")
    print("-" * 30)
    print("• Semantic Clustering: Groups similar responses using embeddings")
    print("• Shapley Values: Quantifies each agent's marginal contribution")
    print("• Entropy Analysis: Measures predictive uncertainty")
    print("• Robust Consensus: Combines multiple strategies for reliability")
    print("\n🎯 Hallucination Detection:")
    print("-" * 25)
    print("• Outlier clusters are filtered out")
    print("• Low similarity responses are downweighted")
    print("• High entropy indicates uncertain predictions")
    print("• Multiple strategies provide consensus validation")


if __name__ == "__main__":
    asyncio.run(clustering_consensus_example())

