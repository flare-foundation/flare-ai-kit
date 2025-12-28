"""LLM-based pointwise reranker using Gemini API."""

import asyncio
import json
import re
from typing import Any, Final, cast, override

import structlog
from google import genai  # pyright: ignore[reportMissingTypeStubs]
from google.genai import types  # pyright: ignore[reportMissingTypeStubs]

from flare_ai_kit.common import RerankerError, RerankerParseError, SemanticSearchResult

from .base import BaseReranker
from .prompts import build_system_prompt, build_user_prompt

logger = structlog.get_logger(__name__)

MIN_SCORE: Final[float] = 0.0
MAX_SCORE: Final[float] = 10.0


class GeminiPointwiseReranker(BaseReranker):
    """
    LLM-based pointwise reranker using Google's Gemini API.

    This reranker scores each passage on a 1-10 scale based on relevance
    to the query. It uses parallel batch processing with round-robin
    distribution for improved latency and accuracy.
    """

    def __init__(  # noqa: PLR0913
        self,
        api_key: str,
        model: str = "gemini-3-flash-preview",
        num_batches: int = 4,
        timeout_seconds: float = 5.0,
        score_threshold: float = 5.0,
        few_shot_examples: str | None = None,
    ) -> None:
        """
        Initialize the Gemini pointwise reranker.

        Args:
            api_key: Google API key for accessing Gemini models.
            model: Gemini model identifier (e.g., "gemini-2.0-flash").
            num_batches: Number of parallel batches for scoring.
            timeout_seconds: Timeout per batch in seconds.
            score_threshold: Minimum score (0-10) to include a passage.
            few_shot_examples: Optional custom few-shot examples for calibration.

        """
        self.model = model
        self.num_batches = num_batches
        self.timeout_seconds = timeout_seconds
        self.score_threshold = score_threshold
        self.few_shot_examples = few_shot_examples
        self.client = genai.Client(api_key=api_key)
        self._system_prompt = build_system_prompt(few_shot_examples)

    @override
    async def rerank(
        self,
        query: str,
        candidates: list[SemanticSearchResult],
        top_k: int | None = None,
    ) -> list[SemanticSearchResult]:
        """
        Rerank candidate passages using parallel batched LLM scoring.

        Args:
            query: The user query to score passages against.
            candidates: List of SemanticSearchResult from initial retrieval.
            top_k: Optional limit on number of results to return.

        Returns:
            Reranked list of SemanticSearchResult sorted by relevance score.

        """
        if not candidates:
            return []

        logger.debug(
            "Starting rerank",
            num_candidates=len(candidates),
            num_batches=self.num_batches,
            top_k=top_k,
        )

        batches = self._distribute_to_batches(candidates, self.num_batches)

        tasks = [self._score_batch(query, batch) for batch in batches if batch]

        try:
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=self.timeout_seconds * 2,
            )
        except TimeoutError:
            logger.warning(
                "Reranker timeout, using fallback",
                timeout_seconds=self.timeout_seconds,
            )
            return self._fallback_rerank(candidates, top_k)

        all_scores: dict[int, float] = {}
        for result in results:
            if isinstance(result, dict):
                all_scores.update(result)
            elif isinstance(result, Exception):
                logger.warning("Batch failed", error=str(result))

        if not all_scores:
            logger.warning("No scores obtained from LLM, using fallback")
            return self._fallback_rerank(candidates, top_k)

        reranked: list[SemanticSearchResult] = []
        for idx, candidate in enumerate(candidates):
            score = all_scores.get(idx)
            if score is not None and score >= self.score_threshold:
                updated_metadata = dict(candidate.metadata)
                updated_metadata["original_score"] = str(candidate.score)
                updated_metadata["reranker_score"] = str(score)

                reranked.append(
                    SemanticSearchResult(
                        text=candidate.text,
                        score=score / 10.0,
                        metadata=updated_metadata,
                    )
                )

        reranked.sort(key=lambda x: x.score, reverse=True)

        logger.debug(
            "Rerank complete",
            input_count=len(candidates),
            output_count=len(reranked),
            filtered_count=len(candidates) - len(reranked),
        )

        return reranked[:top_k] if top_k else reranked

    def _distribute_to_batches(
        self,
        candidates: list[SemanticSearchResult],
        num_batches: int,
    ) -> list[list[tuple[int, SemanticSearchResult]]]:
        """
        Distribute candidates to batches using round-robin assignment.

        This ensures each batch sees a mix of high/medium/low similarity
        passages, reducing positional bias from vector search ordering.

        Args:
            candidates: List of candidate passages.
            num_batches: Number of batches to distribute to.

        Returns:
            List of batches, each containing (original_index, candidate) tuples.

        """
        batches: list[list[tuple[int, SemanticSearchResult]]] = [
            [] for _ in range(num_batches)
        ]
        for idx, candidate in enumerate(candidates):
            batch_idx = idx % num_batches
            batches[batch_idx].append((idx, candidate))
        return batches

    async def _score_batch(
        self,
        query: str,
        batch: list[tuple[int, SemanticSearchResult]],
    ) -> dict[int, float]:
        """
        Score a single batch of passages via LLM.

        Args:
            query: The user query.
            batch: List of (original_index, candidate) tuples.

        Returns:
            Dictionary mapping original indices to scores.

        Raises:
            RerankerError: If the LLM call fails.

        """
        # Prompt IDs are batch-local (id0..idN); map back to original indices below.
        passages = [
            (local_idx, candidate.text)
            for local_idx, (_, candidate) in enumerate(batch)
        ]
        user_prompt = build_user_prompt(query, passages)

        local_to_original = {i: orig_idx for i, (orig_idx, _) in enumerate(batch)}

        try:
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    self._call_gemini,
                    user_prompt,
                ),
                timeout=self.timeout_seconds,
            )

            local_scores = self._parse_scores(response)
            return {
                local_to_original[local_idx]: score
                for local_idx, score in local_scores.items()
            }

        except TimeoutError:
            logger.warning("Batch scoring timeout", batch_size=len(batch))
            raise
        except RerankerParseError:
            raise
        except Exception as e:
            logger.warning("Batch scoring failed", error=str(e))
            msg = f"Failed to score batch: {e}"
            raise RerankerError(msg) from e

    def _call_gemini(self, user_prompt: str) -> str:
        """
        Make synchronous Gemini API call.

        Args:
            user_prompt: The user prompt with query and passages.

        Returns:
            The LLM response text.

        """
        response = self.client.models.generate_content(  # pyright: ignore[reportUnknownMemberType]
            model=self.model,
            contents=[
                types.Content(
                    role="user",
                    parts=[types.Part(text=user_prompt)],
                ),
            ],
            config=types.GenerateContentConfig(
                system_instruction=self._system_prompt,
                temperature=0.0,  # Deterministic scoring
                max_output_tokens=1024,
            ),
        )

        if response.text:
            return response.text
        msg = "Gemini API returned empty response"
        raise RerankerError(msg)

    def _parse_scores(self, response: str) -> dict[int, float]:
        """
        Parse JSON scores from LLM response.

        Expected format: {"id0":8,"id1":10,"id3":7}

        Args:
            response: Raw LLM response text.

        Returns:
            Dictionary mapping local indices to scores.

        Raises:
            RerankerParseError: If response cannot be parsed.

        """
        response = response.strip()

        json_match = re.search(r"\{[^{}]*\}", response)
        if json_match:
            response = json_match.group()

        try:
            raw_data: Any = json.loads(response)
        except json.JSONDecodeError as e:
            logger.warning("Failed to parse JSON response", response=response[:200])
            msg = f"Invalid JSON in response: {e}"
            raise RerankerParseError(msg) from e

        if not isinstance(raw_data, dict):
            msg = f"Expected dict, got {type(raw_data).__name__}"
            raise RerankerParseError(msg)

        # Parse id keys and validate scores
        data = cast("dict[str, Any]", raw_data)
        scores: dict[int, float] = {}
        for key, value in data.items():
            # Extract index from "idN" format
            if not key.startswith("id"):
                logger.warning("Invalid key format", key=key)
                continue

            try:
                idx = int(key[2:])
            except ValueError:
                logger.warning("Cannot parse index from key", key=key)
                continue

            # Validate score
            if not isinstance(value, int | float):
                logger.warning("Invalid score type", key=key, value=value)
                continue

            score = float(value)
            if not MIN_SCORE <= score <= MAX_SCORE:
                logger.warning("Score out of range", key=key, score=score)
                continue

            scores[idx] = score

        return scores

    def _fallback_rerank(
        self,
        candidates: list[SemanticSearchResult],
        top_k: int | None = None,
    ) -> list[SemanticSearchResult]:
        """
        Fallback: return candidates sorted by original embedding score.

        Args:
            candidates: List of candidate passages.
            top_k: Optional limit on number of results.

        Returns:
            Candidates sorted by original score (highest first).

        """
        logger.info(
            "Using fallback reranking (original scores)",
            num_candidates=len(candidates),
        )
        sorted_candidates = sorted(candidates, key=lambda x: x.score, reverse=True)
        return sorted_candidates[:top_k] if top_k else sorted_candidates
