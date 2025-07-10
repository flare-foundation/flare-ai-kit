"""Advanced consensus strategies for detecting hallucinations and improving robustness."""

import numpy as np
from collections import Counter
from typing import List, Tuple, Dict, Any, Optional
from dataclasses import dataclass
from sklearn.cluster import DBSCAN, KMeans
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import StandardScaler
import logging

from flare_ai_kit.common import Prediction
from flare_ai_kit.rag.vector.embedding.base import BaseEmbedding

logger = logging.getLogger(__name__)


@dataclass
class ClusterResult:
    """Result of semantic clustering analysis."""
    
    dominant_cluster: List[Prediction]
    outlier_clusters: List[List[Prediction]]
    cluster_labels: List[int]
    similarity_matrix: np.ndarray
    centroid_embeddings: Dict[int, np.ndarray]


def semantic_clustering_strategy(
    predictions: List[Prediction],
    embedding_model: BaseEmbedding,
    clustering_method: str = "dbscan",
    similarity_threshold: float = 0.7,
    min_cluster_size: int = 2,
    **clustering_kwargs: Any
) -> Prediction:
    """
    Semantic clustering strategy for consensus with hallucination detection.
    
    Args:
        predictions: List of predictions to cluster
        embedding_model: Embedding model for generating text embeddings
        clustering_method: Either "dbscan" or "kmeans"
        similarity_threshold: Minimum cosine similarity for cluster membership
        min_cluster_size: Minimum size for a cluster to be considered valid
        **clustering_kwargs: Additional arguments for clustering algorithm
        
    Returns:
        Consensus prediction from the dominant cluster
    """
    if len(predictions) < 2:
        return predictions[0] if predictions else Prediction("consensus", "", 0.0)
    
    # Generate embeddings for all predictions
    texts = [str(p.prediction) for p in predictions]
    embeddings = embedding_model.embed_content(texts)
    embeddings_array = np.array(embeddings)
    
    # Normalize embeddings for better clustering
    scaler = StandardScaler()
    embeddings_normalized = scaler.fit_transform(embeddings_array)
    
    # Perform clustering
    if clustering_method.lower() == "dbscan":
        clustering = DBSCAN(
            eps=1 - similarity_threshold,
            min_samples=min_cluster_size,
            metric='cosine',
            **clustering_kwargs
        )
    elif clustering_method.lower() == "kmeans":
        n_clusters = min(len(predictions) // 2, 3)  # Reasonable number of clusters
        clustering = KMeans(n_clusters=n_clusters, **clustering_kwargs)
    else:
        raise ValueError(f"Unsupported clustering method: {clustering_method}")
    
    cluster_labels = clustering.fit_predict(embeddings_normalized)
    
    # Group predictions by cluster
    clusters: Dict[int, List[Prediction]] = {}
    for i, label in enumerate(cluster_labels):
        if label not in clusters:
            clusters[label] = []
        clusters[label].append(predictions[i])
    
    # Find dominant cluster (largest cluster)
    dominant_cluster_label = max(clusters.keys(), key=lambda k: len(clusters[k]))
    dominant_cluster = clusters[dominant_cluster_label]
    outlier_clusters = [clusters[k] for k in clusters.keys() if k != dominant_cluster_label]
    
    # Calculate centroid for dominant cluster
    dominant_embeddings = embeddings_array[cluster_labels == dominant_cluster_label]
    centroid = np.mean(dominant_embeddings, axis=0)
    
    # Select best prediction from dominant cluster (highest confidence)
    best_prediction = max(dominant_cluster, key=lambda p: p.confidence)
    
    # Calculate consensus confidence based on cluster stability
    cluster_similarities = cosine_similarity(dominant_embeddings)
    avg_similarity = np.mean(cluster_similarities[np.triu_indices_from(cluster_similarities, k=1)])
    
    # Adjust confidence based on cluster quality
    adjusted_confidence = min(best_prediction.confidence * avg_similarity, 1.0)
    
    return Prediction(
        agent_id="semantic_consensus",
        prediction=best_prediction.prediction,
        confidence=adjusted_confidence
    )


def shapley_value_strategy(
    predictions: List[Prediction],
    embedding_model: BaseEmbedding,
    n_samples: int = 100
) -> Prediction:
    """
    Shapley value-inspired strategy for quantifying each agent's marginal contribution.
    
    Args:
        predictions: List of predictions to evaluate
        embedding_model: Embedding model for similarity calculations
        n_samples: Number of random samples for Monte Carlo approximation
        
    Returns:
        Consensus prediction with Shapley-weighted confidence
    """
    if len(predictions) < 2:
        return predictions[0] if predictions else Prediction("consensus", "", 0.0)
    
    # Generate embeddings
    texts = [str(p.prediction) for p in predictions]
    embeddings = embedding_model.embed_content(texts)
    embeddings_array = np.array(embeddings)
    
    # Calculate pairwise similarities
    similarity_matrix = cosine_similarity(embeddings_array)
    
    # Monte Carlo approximation of Shapley values
    shapley_values = np.zeros(len(predictions))
    
    for _ in range(n_samples):
        # Random permutation of agents
        permutation = np.random.permutation(len(predictions))
        
        # Calculate marginal contributions
        current_set = set()
        for i, agent_idx in enumerate(permutation):
            current_set.add(agent_idx)
            
            # Calculate utility of current set
            if len(current_set) == 1:
                utility = 1.0  # Base utility
            else:
                # Calculate average similarity within the set
                set_indices = list(current_set)
                set_similarities = similarity_matrix[np.ix_(set_indices, set_indices)]
                utility = np.mean(set_similarities[np.triu_indices_from(set_similarities, k=1)])
            
            # Calculate marginal contribution
            if i == 0:
                marginal_contribution = utility
            else:
                # Calculate utility without this agent
                prev_set = current_set - {agent_idx}
                if len(prev_set) == 0:
                    prev_utility = 0.0
                else:
                    prev_indices = list(prev_set)
                    prev_similarities = similarity_matrix[np.ix_(prev_indices, prev_indices)]
                    if len(prev_indices) == 1:
                        prev_utility = 1.0
                    else:
                        prev_utility = np.mean(prev_similarities[np.triu_indices_from(prev_similarities, k=1)])
                
                marginal_contribution = utility - prev_utility
            
            shapley_values[agent_idx] += marginal_contribution
    
    # Normalize Shapley values
    shapley_values /= n_samples
    
    # Weight predictions by Shapley values
    total_weight = np.sum(shapley_values)
    if total_weight == 0:
        # Fallback to equal weighting
        weights = np.ones(len(predictions)) / len(predictions)
    else:
        weights = shapley_values / total_weight
    
    # For string predictions, use weighted voting
    if isinstance(predictions[0].prediction, str):
        vote_counts = Counter()
        for pred, weight in zip(predictions, weights):
            vote_counts[str(pred.prediction)] += weight
        
        consensus_prediction = vote_counts.most_common(1)[0][0]
    else:
        # For numerical predictions, use weighted average
        consensus_prediction = sum(
            float(p.prediction) * weight for p, weight in zip(predictions, weights)
        )
    
    # Calculate weighted confidence
    weighted_confidence = sum(p.confidence * weight for p, weight in zip(predictions, weights))
    
    return Prediction(
        agent_id="shapley_consensus",
        prediction=consensus_prediction,
        confidence=weighted_confidence
    )


def entropy_based_strategy(
    predictions: List[Prediction],
    embedding_model: BaseEmbedding,
    entropy_threshold: float = 0.5
) -> Prediction:
    """
    Entropy-based strategy for measuring predictive uncertainty.
    
    Args:
        predictions: List of predictions to evaluate
        embedding_model: Embedding model for similarity calculations
        entropy_threshold: Threshold for considering predictions uncertain
        
    Returns:
        Consensus prediction with entropy-adjusted confidence
    """
    if len(predictions) < 2:
        return predictions[0] if predictions else Prediction("consensus", "", 0.0)
    
    # Generate embeddings
    texts = [str(p.prediction) for p in predictions]
    embeddings = embedding_model.embed_content(texts)
    embeddings_array = np.array(embeddings)
    
    # Calculate pairwise similarities
    similarity_matrix = cosine_similarity(embeddings_array)
    
    # Calculate entropy of the similarity distribution
    similarities = similarity_matrix[np.triu_indices_from(similarity_matrix, k=1)]
    if len(similarities) > 0:
        # Normalize similarities to probabilities
        similarities = np.clip(similarities, 0, 1)
        similarities = similarities / np.sum(similarities)
        
        # Calculate entropy
        entropy = -np.sum(similarities * np.log(similarities + 1e-10))
        max_entropy = np.log(len(similarities))
        normalized_entropy = entropy / max_entropy if max_entropy > 0 else 0
    else:
        normalized_entropy = 0
    
    # Select prediction based on entropy
    if normalized_entropy > entropy_threshold:
        # High entropy: use most confident prediction
        best_prediction = max(predictions, key=lambda p: p.confidence)
        # Reduce confidence due to high uncertainty
        adjusted_confidence = best_prediction.confidence * (1 - normalized_entropy)
    else:
        # Low entropy: use similarity-weighted consensus
        weights = np.mean(similarity_matrix, axis=1)
        weights = weights / np.sum(weights)
        
        if isinstance(predictions[0].prediction, str):
            vote_counts = Counter()
            for pred, weight in zip(predictions, weights):
                vote_counts[str(pred.prediction)] += weight
            
            consensus_prediction = vote_counts.most_common(1)[0][0]
        else:
            consensus_prediction = sum(
                float(p.prediction) * weight for p, weight in zip(predictions, weights)
            )
        
        best_prediction = predictions[np.argmax(weights)]
        adjusted_confidence = best_prediction.confidence * (1 - normalized_entropy)
    
    return Prediction(
        agent_id="entropy_consensus",
        prediction=best_prediction.prediction,
        confidence=adjusted_confidence
    )


def robust_consensus_strategy(
    predictions: List[Prediction],
    embedding_model: BaseEmbedding,
    strategies: List[str] = None
) -> Prediction:
    """
    Robust consensus strategy that combines multiple approaches.
    
    Args:
        predictions: List of predictions to evaluate
        embedding_model: Embedding model for similarity calculations
        strategies: List of strategies to combine ("semantic", "shapley", "entropy")
        
    Returns:
        Robust consensus prediction
    """
    if strategies is None:
        strategies = ["semantic", "shapley", "entropy"]
    
    strategy_results = []
    
    for strategy in strategies:
        try:
            if strategy == "semantic":
                result = semantic_clustering_strategy(predictions, embedding_model)
            elif strategy == "shapley":
                result = shapley_value_strategy(predictions, embedding_model)
            elif strategy == "entropy":
                result = entropy_based_strategy(predictions, embedding_model)
            else:
                logger.warning(f"Unknown strategy: {strategy}")
                continue
            
            strategy_results.append(result)
        except Exception as e:
            logger.warning(f"Strategy {strategy} failed: {e}")
            continue
    
    if not strategy_results:
        # Fallback to simple majority
        if isinstance(predictions[0].prediction, str):
            vote_counts = Counter(str(p.prediction) for p in predictions)
            consensus_prediction = vote_counts.most_common(1)[0][0]
        else:
            consensus_prediction = sum(float(p.prediction) for p in predictions) / len(predictions)
        
        avg_confidence = sum(p.confidence for p in predictions) / len(predictions)
        return Prediction("robust_consensus", consensus_prediction, avg_confidence)
    
    # Combine strategy results using weighted average
    weights = [r.confidence for r in strategy_results]
    total_weight = sum(weights)
    
    if total_weight == 0:
        # Equal weighting
        weights = [1.0] * len(strategy_results)
        total_weight = len(strategy_results)
    
    weights = [w / total_weight for w in weights]
    
    if isinstance(strategy_results[0].prediction, str):
        vote_counts = Counter()
        for result, weight in zip(strategy_results, weights):
            vote_counts[str(result.prediction)] += weight
        
        consensus_prediction = vote_counts.most_common(1)[0][0]
    else:
        consensus_prediction = sum(
            float(r.prediction) * weight for r, weight in zip(strategy_results, weights)
        )
    
    weighted_confidence = sum(r.confidence * weight for r, weight in zip(strategy_results, weights))
    
    return Prediction(
        agent_id="robust_consensus",
        prediction=consensus_prediction,
        confidence=weighted_confidence
    ) 