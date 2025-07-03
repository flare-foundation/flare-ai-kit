"""Advanced aggregation strategies for consensus predictions."""

import numpy as np
from collections import defaultdict
from itertools import combinations
from typing import Dict, List, Set, Any, cast
from sklearn.cluster import DBSCAN, KMeans
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer
import logging

from flare_ai_kit.common import Prediction

logger = logging.getLogger(__name__)


class ShapleyValueAggregator:
    """
    Shapley value-inspired aggregation that quantifies each agent's marginal utility
    based on repeated exclusion tests.
    """
    
    def __init__(self, embedding_model: str = "all-MiniLM-L6-v2"):
        """
        Initialize the Shapley Value Aggregator.
        
        Args:
            embedding_model: The sentence transformer model to use for embeddings
        """
        self.embedding_model = SentenceTransformer(embedding_model)
        self.agent_contributions: Dict[str, float] = defaultdict(float)
        self.historical_performance: Dict[str, List[float]] = defaultdict(list)
    
    def _calculate_subset_quality(self, subset_predictions: List[Prediction]) -> float:
        """
        Calculate the quality of a subset of predictions.
        Uses embedding similarity and confidence as quality metrics.
        
        Args:
            subset_predictions: List of predictions in the subset
            
        Returns:
            Quality score for the subset
        """
        if not subset_predictions:
            return 0.0
        
        # Get embeddings for all predictions
        texts = [str(pred.prediction) for pred in subset_predictions]
        embeddings = self.embedding_model.encode(texts)
        
        # Calculate average confidence
        avg_confidence = np.mean([pred.confidence for pred in subset_predictions])
        
        # Calculate internal consistency (average pairwise cosine similarity)
        if len(embeddings) > 1:
            similarity_matrix = cosine_similarity(embeddings)
            # Get upper triangle excluding diagonal
            upper_triangle = similarity_matrix[np.triu_indices_from(similarity_matrix, k=1)]
            consistency = float(np.mean(upper_triangle))
        else:
            consistency = 1.0
        
        # Quality combines confidence and consistency
        quality = 0.6 * avg_confidence + 0.4 * consistency
        return quality
    
    def _calculate_shapley_values(self, predictions: List[Prediction]) -> Dict[str, float]:
        """
        Calculate Shapley values for each agent based on their marginal contributions.
        
        Args:
            predictions: List of all predictions
            
        Returns:
            Dictionary mapping agent_id to Shapley value
        """
        agents = [pred.agent_id for pred in predictions]
        n_agents = len(agents)
        shapley_values = {agent: 0.0 for agent in agents}
        
        # For computational efficiency, we'll use a sampling approach for large n
        if n_agents <= 10:
            # Exact calculation for small sets
            for agent_idx, agent in enumerate(agents):
                for subset_size in range(n_agents):
                    # Get all subsets of given size not containing the agent
                    other_agents = [a for i, a in enumerate(agents) if i != agent_idx]
                    
                    if subset_size == 0:
                        subsets = [()]
                    else:
                        subsets = list(combinations(other_agents, min(subset_size, len(other_agents))))
                    
                    for subset in subsets:
                        # Calculate marginal contribution
                        subset_preds = [pred for pred in predictions if pred.agent_id in subset]
                        subset_with_agent_preds = [pred for pred in predictions 
                                                 if pred.agent_id in subset or pred.agent_id == agent]
                        
                        quality_without = self._calculate_subset_quality(subset_preds)
                        quality_with = self._calculate_subset_quality(subset_with_agent_preds)
                        
                        marginal_contribution = quality_with - quality_without
                        
                        # Weight by combinatorial factor
                        weight = 1.0 / (n_agents * len(subsets)) if len(subsets) > 0 else 0
                        shapley_values[agent] += weight * marginal_contribution
        else:
            # Sampling approach for larger sets
            n_samples = min(1000, 2 ** n_agents)  # Limit sampling
            
            for agent_idx, agent in enumerate(agents):
                contributions: List[float] = []
                
                for _ in range(n_samples // n_agents):
                    # Random subset not containing the agent
                    other_agents = [a for i, a in enumerate(agents) if i != agent_idx]
                    subset_size = np.random.randint(0, len(other_agents) + 1)
                    subset = np.random.choice(other_agents, subset_size, replace=False)
                    
                    subset_preds = [pred for pred in predictions if pred.agent_id in subset]
                    subset_with_agent_preds = [pred for pred in predictions 
                                             if pred.agent_id in subset or pred.agent_id == agent]
                    
                    quality_without = self._calculate_subset_quality(subset_preds)
                    quality_with = self._calculate_subset_quality(subset_with_agent_preds)
                    
                    contributions.append(quality_with - quality_without)
                
                shapley_values[agent] = float(np.mean(contributions))
        
        return shapley_values
    
    def aggregate(self, predictions: List[Prediction]) -> Prediction:
        """
        Aggregate predictions using Shapley value-inspired weighting.
        
        Args:
            predictions: List of predictions to aggregate
            
        Returns:
            Aggregated prediction
        """
        if not predictions:
            raise ValueError("No predictions to aggregate")
        
        if len(predictions) == 1:
            return predictions[0]
        
        # Calculate Shapley values
        shapley_values = self._calculate_shapley_values(predictions)
        
        # Update historical performance
        for agent_id, value in shapley_values.items():
            self.historical_performance[agent_id].append(value)
            # Keep only recent history (last 100 values)
            if len(self.historical_performance[agent_id]) > 100:
                self.historical_performance[agent_id] = self.historical_performance[agent_id][-100:]
        
        # Calculate dynamic weights based on recent performance
        weights: Dict[str, float] = {}
        for agent_id in shapley_values:
            recent_performance = self.historical_performance[agent_id]
            if len(recent_performance) > 0:
                # Weight based on recent average performance
                avg_recent = float(np.mean(recent_performance[-10:]))  # Last 10 interactions
                weights[agent_id] = max(0.01, avg_recent)  # Minimum weight of 0.01
            else:
                weights[agent_id] = 1.0
        
        # Normalize weights
        total_weight = sum(weights.values())
        if total_weight > 0:
            weights = {k: v / total_weight for k, v in weights.items()}
        else:
            weights = {k: 1.0 / len(predictions) for k in weights}
        
        # Aggregate predictions
        try:
            # Try numerical aggregation first
            weighted_sum = sum(float(pred.prediction) * weights[pred.agent_id] for pred in predictions)
            aggregated_prediction = str(weighted_sum)
        except (ValueError, TypeError):
            # Fall back to weighted text selection
            best_agent = max(weights.items(), key=lambda x: x[1])[0]
            aggregated_prediction = next(pred.prediction for pred in predictions if pred.agent_id == best_agent)
        
        # Calculate aggregated confidence
        aggregated_confidence = sum(pred.confidence * weights[pred.agent_id] for pred in predictions)
        
        return Prediction(
            agent_id="shapley_aggregator",
            prediction=aggregated_prediction,
            confidence=aggregated_confidence
        )


class SemanticClusteringAggregator:
    """
    Semantic clustering aggregation that groups similar responses and filters outliers.
    """
    
    def __init__(self, 
                 embedding_model: str = "all-MiniLM-L6-v2",
                 similarity_threshold: float = 0.7,
                 min_cluster_size: int = 2,
                 clustering_method: str = "dbscan"):
        """
        Initialize the Semantic Clustering Aggregator.
        
        Args:
            embedding_model: The sentence transformer model to use
            similarity_threshold: Minimum cosine similarity for clustering
            min_cluster_size: Minimum size for a cluster to be considered
            clustering_method: "dbscan" or "kmeans"
        """
        self.embedding_model = SentenceTransformer(embedding_model)
        self.similarity_threshold = similarity_threshold
        self.min_cluster_size = min_cluster_size
        self.clustering_method = clustering_method
        self.cluster_history: List[Dict[str, Any]] = []
    
    def _detect_outliers(self, predictions: List[Prediction], embeddings: np.ndarray) -> Set[int]:
        """
        Detect outlier predictions based on embedding similarity.
        
        Args:
            predictions: List of predictions
            embeddings: Embeddings for the predictions
            
        Returns:
            Set of indices of outlier predictions
        """
        if len(predictions) <= 2:
            return set()
        
        # Calculate pairwise similarities
        similarity_matrix = cosine_similarity(embeddings)
        
        outliers: Set[int] = set()
        for i, pred in enumerate(predictions):
            # Calculate average similarity to all other predictions
            similarities = similarity_matrix[i]
            avg_similarity = float(np.mean([sim for j, sim in enumerate(similarities) if j != i]))
            
            # Mark as outlier if below threshold
            if avg_similarity < self.similarity_threshold:
                outliers.add(i)
                logger.info(f"Detected outlier: {pred.agent_id} with avg similarity {avg_similarity:.3f}")
        
        return outliers
    
    def _cluster_predictions(self, predictions: List[Prediction], embeddings: np.ndarray) -> List[List[int]]:
        """
        Cluster predictions based on semantic similarity.
        
        Args:
            predictions: List of predictions
            embeddings: Embeddings for the predictions
            
        Returns:
            List of clusters, where each cluster is a list of prediction indices
        """
        if len(predictions) <= 1:
            return [[0]] if len(predictions) == 1 else []
        
        if self.clustering_method == "dbscan":
            # DBSCAN clustering
            # Convert similarity threshold to distance threshold
            eps = 1 - self.similarity_threshold
            clusterer = DBSCAN(eps=eps, min_samples=self.min_cluster_size, metric='cosine')
            cluster_labels = clusterer.fit_predict(embeddings)
            
        elif self.clustering_method == "kmeans":
            # K-means clustering with dynamic k
            max_k = min(len(predictions), 5)  # Maximum 5 clusters
            best_k = 2
            best_score = -1
            
            for k in range(2, max_k + 1):
                clusterer = KMeans(n_clusters=k, random_state=42)
                cluster_labels = clusterer.fit_predict(embeddings)
                
                # Calculate silhouette-like score using cosine similarity
                score = 0.0
                for i, label in enumerate(cluster_labels):
                    same_cluster = [j for j, l in enumerate(cluster_labels) if l == label and j != i]
                    diff_cluster = [j for j, l in enumerate(cluster_labels) if l != label]
                    
                    if same_cluster:
                        intra_sim = float(np.mean([cosine_similarity([embeddings[i]], [embeddings[j]])[0][0] 
                                           for j in same_cluster]))
                    else:
                        intra_sim = 0.0
                    
                    if diff_cluster:
                        inter_sim = float(np.mean([cosine_similarity([embeddings[i]], [embeddings[j]])[0][0] 
                                           for j in diff_cluster]))
                    else:
                        inter_sim = 0.0
                    
                    score += intra_sim - inter_sim
                
                if score > best_score:
                    best_score = score
                    best_k = k
            
            # Rerun with best k
            clusterer = KMeans(n_clusters=best_k, random_state=42)
            cluster_labels = clusterer.fit_predict(embeddings)
        else:
            # Default to DBSCAN
            eps = 1 - self.similarity_threshold
            clusterer = DBSCAN(eps=eps, min_samples=self.min_cluster_size, metric='cosine')
            cluster_labels = clusterer.fit_predict(embeddings)
        
        # Group predictions by cluster
        clusters = defaultdict(list)
        for i, label in enumerate(cluster_labels):
            if label != -1:  # -1 indicates noise in DBSCAN
                clusters[label].append(i)
        
        # Filter clusters by minimum size
        valid_clusters = [cluster for cluster in clusters.values() 
                         if len(cluster) >= self.min_cluster_size]
        
        return valid_clusters
    
    def _select_cluster_representative(self, predictions: List[Prediction], 
                                    cluster_indices: List[int], 
                                    embeddings: np.ndarray) -> Prediction:
        """
        Select the best representative from a cluster.
        
        Args:
            predictions: All predictions
            cluster_indices: Indices of predictions in the cluster
            embeddings: Embeddings for all predictions
            
        Returns:
            Representative prediction for the cluster
        """
        cluster_embeddings = embeddings[cluster_indices]
        
        # Method 1: Highest confidence
        best_confidence_idx = max(cluster_indices, key=lambda i: predictions[i].confidence)
        
        # Method 2: Cluster centroid (closest to average)
        if len(cluster_embeddings) > 1:
            centroid = np.mean(cluster_embeddings, axis=0)
            similarities_to_centroid = cosine_similarity([centroid], cluster_embeddings)[0]
            best_centroid_idx = cluster_indices[np.argmax(similarities_to_centroid)]
        else:
            best_centroid_idx = cluster_indices[0]
        
        # Combine both methods: prefer high confidence near centroid
        if best_confidence_idx == best_centroid_idx:
            return predictions[best_confidence_idx]
        else:
            conf_pred = predictions[best_confidence_idx]
            cent_pred = predictions[best_centroid_idx]
            
            # Choose based on weighted score
            conf_score = conf_pred.confidence * 0.6
            cent_score = cent_pred.confidence * 0.4 + 0.2  # Bonus for being central
            
            return conf_pred if conf_score > cent_score else cent_pred
    
    def aggregate(self, predictions: List[Prediction]) -> Prediction:
        """
        Aggregate predictions using semantic clustering.
        
        Args:
            predictions: List of predictions to aggregate
            
        Returns:
            Aggregated prediction
        """
        if not predictions:
            raise ValueError("No predictions to aggregate")
        
        if len(predictions) == 1:
            return predictions[0]
        
        # Get embeddings
        texts = [str(pred.prediction) for pred in predictions]
        embeddings = self.embedding_model.encode(texts)
        
        # Detect and remove outliers
        outliers = self._detect_outliers(predictions, embeddings)
        
        # Filter out outliers
        filtered_predictions = [pred for i, pred in enumerate(predictions) if i not in outliers]
        filtered_embeddings = np.array([emb for i, emb in enumerate(embeddings) if i not in outliers])
        
        if len(filtered_predictions) == 0:
            # If all are outliers, return the highest confidence one
            return max(predictions, key=lambda p: p.confidence)
        
        if len(filtered_predictions) == 1:
            return filtered_predictions[0]
        
        # Cluster the filtered predictions
        clusters = self._cluster_predictions(filtered_predictions, filtered_embeddings)
        
        if not clusters:
            # No valid clusters, return highest confidence
            return max(filtered_predictions, key=lambda p: p.confidence)
        
        # Find the dominant cluster (largest)
        dominant_cluster = max(clusters, key=len)
        
        # Select representative from dominant cluster
        representative = self._select_cluster_representative(
            filtered_predictions, dominant_cluster, filtered_embeddings
        )
        
        # Store cluster information for analysis
        cluster_info = {
            "n_original": len(predictions),
            "n_filtered": len(filtered_predictions),
            "n_clusters": len(clusters),
            "dominant_cluster_size": len(dominant_cluster),
            "outliers_removed": len(outliers)
        }
        self.cluster_history.append(cluster_info)
        
        # Keep only recent history
        if len(self.cluster_history) > 100:
            self.cluster_history = self.cluster_history[-100:]
        
        return Prediction(
            agent_id="semantic_clustering_aggregator",
            prediction=representative.prediction,
            confidence=representative.confidence * (1 + 0.1 * len(dominant_cluster))  # Boost confidence for larger clusters
        )


def shapley_value_strategy(predictions: List[Prediction]) -> Prediction:
    """Wrapper function for Shapley value aggregation strategy."""
    aggregator = ShapleyValueAggregator()
    return aggregator.aggregate(predictions)


def semantic_clustering_strategy(predictions: List[Prediction]) -> Prediction:
    """Wrapper function for semantic clustering aggregation strategy."""
    aggregator = SemanticClusteringAggregator()
    return aggregator.aggregate(predictions)


def semantic_clustering_strict_strategy(predictions: List[Prediction]) -> Prediction:
    """Wrapper function for strict semantic clustering (higher threshold)."""
    aggregator = SemanticClusteringAggregator(similarity_threshold=0.85, min_cluster_size=3)
    return aggregator.aggregate(predictions)