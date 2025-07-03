"""Tournament-based elimination strategy with LLM arbitration."""

import asyncio
import random
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
import logging

from flare_ai_kit.common import Prediction

logger = logging.getLogger(__name__)


@dataclass
class TournamentMatch:
    """Represents a match between two predictions in the tournament."""
    prediction_a: Prediction
    prediction_b: Prediction
    winner: Optional[Prediction] = None
    arbitration_reasoning: Optional[str] = None
    confidence_boost: float = 0.0


@dataclass
class TournamentRound:
    """Represents a round in the tournament."""
    round_number: int
    matches: List[TournamentMatch]
    winners: List[Prediction]


class TournamentEliminationAggregator:
    """
    Tournament-based aggregation where predictions compete in elimination rounds.
    Uses LLM-based arbitration to determine winners in each match.
    """
    
    def __init__(self, 
                 meta_agent_model: str = "gpt-4",
                 enable_chain_of_thought: bool = True,
                 consistency_penalty: float = 0.1,
                 confidence_boost_factor: float = 0.05):
        """
        Initialize the tournament aggregator.
        
        Args:
            meta_agent_model: The model to use for arbitration
            enable_chain_of_thought: Whether to use chain-of-thought reasoning
            consistency_penalty: Penalty for inconsistent reasoning
            confidence_boost_factor: How much to boost confidence for tournament winners
        """
        self.meta_agent_model = meta_agent_model
        self.enable_chain_of_thought = enable_chain_of_thought
        self.consistency_penalty = consistency_penalty
        self.confidence_boost_factor = confidence_boost_factor
        
        # Tournament history
        self.tournament_history: List[Dict[str, Any]] = []
        self.agent_win_rates: Dict[str, List[bool]] = {}
        
        # Arbitration prompts
        self.base_arbitration_prompt = """
You are an expert arbitrator evaluating two AI responses. Your task is to determine which response is better based on accuracy, relevance, clarity, and overall quality.

Response A (from {agent_a}):
{prediction_a}
Confidence: {confidence_a}

Response B (from {agent_b}):
{prediction_b}
Confidence: {confidence_b}

Original Question/Task: {original_task}

Please analyze both responses and determine which is better. Consider:
1. Factual accuracy
2. Relevance to the question
3. Clarity and coherence
4. Completeness of the answer
5. Logical reasoning

{chain_of_thought_instruction}

Respond with your decision in the following format:
WINNER: A or B
REASONING: [Your detailed explanation]
CONFIDENCE_ADJUSTMENT: [Number between -0.2 and 0.2 to adjust winner's confidence]
"""
        
        self.chain_of_thought_instruction = """
Think step by step:
1. First, evaluate Response A on each criterion
2. Then, evaluate Response B on each criterion  
3. Compare them directly
4. Make your final decision
""" if enable_chain_of_thought else "Provide your analysis and decision."
    
    async def _arbitrate_match(self, match: TournamentMatch, original_task: str) -> TournamentMatch:
        """
        Use a meta-agent to arbitrate between two predictions.
        
        Args:
            match: The tournament match to arbitrate
            original_task: The original task/question
            
        Returns:
            Updated match with winner determined
        """
        prompt = self.base_arbitration_prompt.format(
            agent_a=match.prediction_a.agent_id,
            prediction_a=match.prediction_a.prediction,
            confidence_a=match.prediction_a.confidence,
            agent_b=match.prediction_b.agent_id,
            prediction_b=match.prediction_b.prediction,
            confidence_b=match.prediction_b.confidence,
            original_task=original_task,
            chain_of_thought_instruction=self.chain_of_thought_instruction
        )
        
        try:
            # Here you would call your actual LLM API
            # For now, we'll simulate the arbitration based on confidence and some logic
            arbitration_result = await self._simulate_arbitration(match, prompt)
            
            winner_choice = arbitration_result.get("winner", "A")
            reasoning = arbitration_result.get("reasoning", "No reasoning provided")
            confidence_adjustment = arbitration_result.get("confidence_adjustment", 0.0)
            
            if winner_choice == "A":
                winner = match.prediction_a
            else:
                winner = match.prediction_b
            
            # Apply confidence adjustment
            adjusted_confidence = max(0.0, min(1.0, winner.confidence + confidence_adjustment))
            
            # Create new prediction with adjusted confidence
            adjusted_winner = Prediction(
                agent_id=winner.agent_id,
                prediction=winner.prediction,
                confidence=adjusted_confidence
            )
            
            match.winner = adjusted_winner
            match.arbitration_reasoning = reasoning
            match.confidence_boost = confidence_adjustment
            
            # Track win/loss for agents
            winner_agent = match.prediction_a.agent_id if winner_choice == "A" else match.prediction_b.agent_id
            loser_agent = match.prediction_b.agent_id if winner_choice == "A" else match.prediction_a.agent_id
            
            if winner_agent not in self.agent_win_rates:
                self.agent_win_rates[winner_agent] = []
            if loser_agent not in self.agent_win_rates:
                self.agent_win_rates[loser_agent] = []
                
            self.agent_win_rates[winner_agent].append(True)
            self.agent_win_rates[loser_agent].append(False)
            
            # Keep only recent history
            for agent in self.agent_win_rates:
                if len(self.agent_win_rates[agent]) > 100:
                    self.agent_win_rates[agent] = self.agent_win_rates[agent][-100:]
            
        except Exception as e:
            logger.error(f"Arbitration failed: {e}")
            # Fallback to confidence-based decision
            if match.prediction_a.confidence >= match.prediction_b.confidence:
                match.winner = match.prediction_a
            else:
                match.winner = match.prediction_b
            match.arbitration_reasoning = f"Fallback decision due to arbitration error: {e}"
        
        return match
    
    async def _simulate_arbitration(self, match: TournamentMatch, prompt: str) -> Dict[str, Any]:
        """
        Simulate LLM arbitration (replace with actual LLM call).
        
        Args:
            match: The match to arbitrate
            prompt: The arbitration prompt
            
        Returns:
            Dictionary with winner, reasoning, and confidence adjustment
        """
        # This is a simulation - replace with actual LLM API call
        pred_a = match.prediction_a
        pred_b = match.prediction_b
        
        # Simple heuristic: prefer higher confidence, but add some randomness
        # and consider prediction length/complexity
        
        score_a = pred_a.confidence * 0.7
        score_b = pred_b.confidence * 0.7
        
        # Length bonus (longer might be more detailed)
        len_a = len(str(pred_a.prediction))
        len_b = len(str(pred_b.prediction))
        
        if len_a > len_b:
            score_a += 0.1
        elif len_b > len_a:
            score_b += 0.1
        
        # Add some randomness to simulate LLM uncertainty
        score_a += random.uniform(-0.1, 0.1)
        score_b += random.uniform(-0.1, 0.1)
        
        if score_a >= score_b:
            winner = "A"
            confidence_adj = random.uniform(0.0, 0.1)
            reasoning = f"Response A selected for higher confidence ({pred_a.confidence:.2f}) and overall quality."
        else:
            winner = "B" 
            confidence_adj = random.uniform(0.0, 0.1)
            reasoning = f"Response B selected for higher confidence ({pred_b.confidence:.2f}) and overall quality."
        
        # Simulate some processing time
        await asyncio.sleep(0.1)
        
        return {
            "winner": winner,
            "reasoning": reasoning,
            "confidence_adjustment": confidence_adj
        }
    
    def _create_tournament_bracket(self, predictions: List[Prediction]) -> List[TournamentRound]:
        """
        Create tournament bracket from predictions.
        
        Args:
            predictions: List of predictions to organize into bracket
            
        Returns:
            List of tournament rounds
        """
        if len(predictions) <= 1:
            return []
        
        rounds: List[TournamentRound] = []
        current_predictions = predictions.copy()
        round_number = 1
        
        while len(current_predictions) > 1:
            matches: List[TournamentMatch] = []
            next_round_predictions: List[Prediction] = []
            
            # Pair up predictions for matches
            if len(current_predictions) % 2 == 1:
                # If odd number, highest confidence gets a bye
                bye_prediction = max(current_predictions, key=lambda p: p.confidence)
                current_predictions.remove(bye_prediction)
                next_round_predictions.append(bye_prediction)
            
            # Create matches
            random.shuffle(current_predictions)  # Randomize matchups
            for i in range(0, len(current_predictions), 2):
                if i + 1 < len(current_predictions):
                    match = TournamentMatch(
                        prediction_a=current_predictions[i],
                        prediction_b=current_predictions[i + 1]
                    )
                    matches.append(match)
            
            rounds.append(TournamentRound(
                round_number=round_number,
                matches=matches,
                winners=[]  # Will be filled after arbitration
            ))
            
            current_predictions = next_round_predictions
            round_number += 1
        
        return rounds
    
    def _detect_inconsistencies(self, tournament_rounds: List[TournamentRound]) -> Dict[str, float]:
        """
        Detect inconsistencies in arbitration reasoning across the tournament.
        
        Args:
            tournament_rounds: List of completed tournament rounds
            
        Returns:
            Dictionary mapping agents to consistency scores
        """
        agent_reasonings: Dict[str, List[str]] = {}
        
        # Collect all reasoning for each agent
        for round_data in tournament_rounds:
            for match in round_data.matches:
                if match.winner and match.arbitration_reasoning:
                    agent_id = match.winner.agent_id
                    if agent_id not in agent_reasonings:
                        agent_reasonings[agent_id] = []
                    agent_reasonings[agent_id].append(match.arbitration_reasoning)
        
        # Calculate consistency scores (simplified)
        consistency_scores: Dict[str, float] = {}
        for agent_id, reasonings in agent_reasonings.items():
            if len(reasonings) > 1:
                # Simple consistency: check for repeated key phrases
                key_phrases: List[str] = []
                for reasoning in reasonings:
                    words = reasoning.lower().split()
                    key_phrases.extend([w for w in words if len(w) > 5])  # Longer words
                
                unique_phrases = set(key_phrases)
                total_phrases = len(key_phrases)
                
                # Higher repetition = higher consistency
                consistency = 1.0 - (len(unique_phrases) / max(total_phrases, 1))
                consistency_scores[agent_id] = consistency
            else:
                consistency_scores[agent_id] = 1.0  # Single reasoning is consistent
        
        return consistency_scores
    
    async def aggregate(self, predictions: List[Prediction], original_task: str = "") -> Prediction:
        """
        Aggregate predictions using tournament elimination.
        
        Args:
            predictions: List of predictions to aggregate
            original_task: The original task/question for context
            
        Returns:
            Tournament winner prediction
        """
        if not predictions:
            raise ValueError("No predictions to aggregate")
        
        if len(predictions) == 1:
            return predictions[0]
        
        # Create tournament bracket
        tournament_rounds = self._create_tournament_bracket(predictions)
        
        # Run tournament rounds
        for round_data in tournament_rounds:
            # Arbitrate all matches in this round
            arbitration_tasks = [
                self._arbitrate_match(match, original_task) 
                for match in round_data.matches
            ]
            
            # Wait for all arbitrations to complete
            completed_matches = await asyncio.gather(*arbitration_tasks)
            
            # Collect winners for next round
            winners = [match.winner for match in completed_matches if match.winner]
            round_data.winners = winners
            
            # Update predictions for next round
            if round_data.round_number < len(tournament_rounds):
                # Find next round and update its inputs
                next_round_idx = round_data.round_number  # 0-indexed
                if next_round_idx < len(tournament_rounds):
                    # This is handled by the bracket creation, but we track winners
                    pass
        
        # Get the final winner
        final_winner: Optional[Prediction] = None
        if tournament_rounds:
            final_round = tournament_rounds[-1]
            if final_round.winners:
                final_winner = final_round.winners[0]
            else:
                # Fallback to the winner of the last match
                last_match = final_round.matches[-1] if final_round.matches else None
                final_winner = last_match.winner if last_match else predictions[0]
        else:
            final_winner = predictions[0]
        
        # Ensure we have a final winner
        if final_winner is None:
            final_winner = predictions[0]
        
        # Apply consistency penalties
        consistency_scores = self._detect_inconsistencies(tournament_rounds)
        
        if final_winner.agent_id in consistency_scores:
            consistency_penalty = (1.0 - consistency_scores[final_winner.agent_id]) * self.consistency_penalty
            adjusted_confidence = max(0.0, final_winner.confidence - consistency_penalty)
        else:
            adjusted_confidence = final_winner.confidence
        
        # Apply tournament winner boost
        final_confidence = min(1.0, adjusted_confidence + self.confidence_boost_factor)
        
        final_result = Prediction(
            agent_id=f"tournament_winner_{final_winner.agent_id}",
            prediction=final_winner.prediction,
            confidence=final_confidence
        )
        
        # Store tournament history
        tournament_record = {
            "timestamp": asyncio.get_event_loop().time(),
            "n_participants": len(predictions),
            "n_rounds": len(tournament_rounds),
            "final_winner": final_winner.agent_id,
            "consistency_scores": consistency_scores,
            "total_matches": sum(len(round_data.matches) for round_data in tournament_rounds)
        }
        
        self.tournament_history.append(tournament_record)
        
        # Keep only recent history
        if len(self.tournament_history) > 50:
            self.tournament_history = self.tournament_history[-50:]
        
        return final_result
    
    def get_agent_tournament_stats(self, agent_id: str) -> Dict[str, Any]:
        """Get tournament statistics for a specific agent."""
        if agent_id not in self.agent_win_rates:
            return {"status": "No tournament data for agent"}
        
        wins = self.agent_win_rates[agent_id]
        win_rate = sum(wins) / len(wins) if wins else 0.0
        
        # Recent performance trend
        recent_wins = wins[-10:] if len(wins) >= 10 else wins
        recent_win_rate = sum(recent_wins) / len(recent_wins) if recent_wins else 0.0
        
        return {
            "total_matches": len(wins),
            "overall_win_rate": win_rate,
            "recent_win_rate": recent_win_rate,
            "trend": recent_win_rate - win_rate,
            "wins": sum(wins),
            "losses": len(wins) - sum(wins)
        }


def tournament_elimination_strategy(predictions: List[Prediction]) -> Prediction:
    """Wrapper function for tournament elimination aggregation strategy."""
    aggregator = TournamentEliminationAggregator()
    # Since this is a sync wrapper but aggregate is async, we need to handle it
    import asyncio
    
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If we're already in an async context, create a new task
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, aggregator.aggregate(predictions))
                return future.result()
        else:
            return asyncio.run(aggregator.aggregate(predictions))
    except RuntimeError:
        # Fallback for environments where asyncio.run doesn't work
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(aggregator.aggregate(predictions))
        finally:
            loop.close()