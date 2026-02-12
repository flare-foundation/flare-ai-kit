"""Unit tests for GeminiPointwiseReranker."""

from unittest.mock import patch

import pytest

from flare_ai_kit.common import RerankerParseError, SemanticSearchResult
from flare_ai_kit.rag.vector.reranker import GeminiPointwiseReranker


@pytest.fixture
def mock_candidates() -> list[SemanticSearchResult]:
    """Create mock search candidates."""
    return [
        SemanticSearchResult(
            text=f"Passage {i} about topic",
            score=0.9 - i * 0.1,
            metadata={"file_name": f"doc{i}.txt"},
        )
        for i in range(10)
    ]


@pytest.fixture
def reranker() -> GeminiPointwiseReranker:
    """Create reranker with mocked client."""
    with patch("flare_ai_kit.rag.vector.reranker.gemini_reranker.genai"):
        return GeminiPointwiseReranker(
            api_key="test-api-key",
            model="gemini-2.0-flash",
            num_batches=4,
            timeout_seconds=5.0,
            score_threshold=5.0,
        )


class TestDistributeToBatches:
    """Tests for _distribute_to_batches method."""

    def test_round_robin_distribution(
        self,
        reranker: GeminiPointwiseReranker,
        mock_candidates: list[SemanticSearchResult],
    ) -> None:
        """Test that candidates are distributed round-robin across batches."""
        batches = reranker._distribute_to_batches(mock_candidates, 4)

        assert len(batches) == 4

        # Batch 0 should have indices 0, 4, 8
        assert [idx for idx, _ in batches[0]] == [0, 4, 8]
        # Batch 1 should have indices 1, 5, 9
        assert [idx for idx, _ in batches[1]] == [1, 5, 9]
        # Batch 2 should have indices 2, 6
        assert [idx for idx, _ in batches[2]] == [2, 6]
        # Batch 3 should have indices 3, 7
        assert [idx for idx, _ in batches[3]] == [3, 7]

    def test_single_batch(
        self,
        reranker: GeminiPointwiseReranker,
        mock_candidates: list[SemanticSearchResult],
    ) -> None:
        """Test distribution with single batch."""
        batches = reranker._distribute_to_batches(mock_candidates, 1)

        assert len(batches) == 1
        assert len(batches[0]) == 10
        assert [idx for idx, _ in batches[0]] == list(range(10))

    def test_more_batches_than_candidates(
        self, reranker: GeminiPointwiseReranker
    ) -> None:
        """Test when there are more batches than candidates."""
        candidates = [
            SemanticSearchResult(text="p1", score=0.9, metadata={}),
            SemanticSearchResult(text="p2", score=0.8, metadata={}),
        ]
        batches = reranker._distribute_to_batches(candidates, 4)

        assert len(batches) == 4
        # Only first 2 batches should have candidates
        assert len(batches[0]) == 1
        assert len(batches[1]) == 1
        assert len(batches[2]) == 0
        assert len(batches[3]) == 0


class TestParseScores:
    """Tests for _parse_scores method."""

    def test_valid_json(self, reranker: GeminiPointwiseReranker) -> None:
        """Test parsing valid JSON response."""
        response = '{"id0":8,"id1":10,"id2":3}'
        scores = reranker._parse_scores(response)

        assert scores == {0: 8.0, 1: 10.0, 2: 3.0}

    def test_json_with_whitespace(self, reranker: GeminiPointwiseReranker) -> None:
        """Test parsing JSON with whitespace."""
        response = '  { "id0": 8, "id1": 10 }  '
        scores = reranker._parse_scores(response)

        assert scores == {0: 8.0, 1: 10.0}

    def test_json_wrapped_in_text(self, reranker: GeminiPointwiseReranker) -> None:
        """Test extracting JSON from text response."""
        response = 'Here are the scores: {"id0":7,"id1":9} based on my analysis.'
        scores = reranker._parse_scores(response)

        assert scores == {0: 7.0, 1: 9.0}

    def test_empty_json(self, reranker: GeminiPointwiseReranker) -> None:
        """Test parsing empty JSON (no passages scored above threshold)."""
        response = "{}"
        scores = reranker._parse_scores(response)

        assert scores == {}

    def test_invalid_json(self, reranker: GeminiPointwiseReranker) -> None:
        """Test that invalid JSON raises RerankerParseError."""
        response = "not valid json"
        with pytest.raises(RerankerParseError):
            reranker._parse_scores(response)

    def test_invalid_key_format(self, reranker: GeminiPointwiseReranker) -> None:
        """Test that invalid keys are skipped."""
        response = '{"id0":8,"invalid_key":10,"id1":7}'
        scores = reranker._parse_scores(response)

        # Only valid id keys should be included
        assert scores == {0: 8.0, 1: 7.0}

    def test_score_out_of_range(self, reranker: GeminiPointwiseReranker) -> None:
        """Test that out-of-range scores are skipped."""
        response = '{"id0":8,"id1":15,"id2":-1}'
        scores = reranker._parse_scores(response)

        # Only valid scores (0-10) should be included
        assert scores == {0: 8.0}


class TestFallbackRerank:
    """Tests for _fallback_rerank method."""

    def test_returns_sorted_by_original_score(
        self,
        reranker: GeminiPointwiseReranker,
        mock_candidates: list[SemanticSearchResult],
    ) -> None:
        """Test that fallback returns candidates sorted by original score."""
        # Shuffle the order
        shuffled = mock_candidates[5:] + mock_candidates[:5]
        result = reranker._fallback_rerank(shuffled, top_k=5)

        assert len(result) == 5
        # Should be sorted by score descending
        for i in range(len(result) - 1):
            assert result[i].score >= result[i + 1].score

    def test_respects_top_k(
        self,
        reranker: GeminiPointwiseReranker,
        mock_candidates: list[SemanticSearchResult],
    ) -> None:
        """Test that fallback respects top_k limit."""
        result = reranker._fallback_rerank(mock_candidates, top_k=3)
        assert len(result) == 3

    def test_returns_all_when_top_k_none(
        self,
        reranker: GeminiPointwiseReranker,
        mock_candidates: list[SemanticSearchResult],
    ) -> None:
        """Test that fallback returns all candidates when top_k is None."""
        result = reranker._fallback_rerank(mock_candidates, top_k=None)
        assert len(result) == len(mock_candidates)


class TestRerank:
    """Tests for the main rerank method."""

    @pytest.mark.asyncio
    async def test_empty_candidates(self, reranker: GeminiPointwiseReranker) -> None:
        """Test rerank with empty candidates list."""
        result = await reranker.rerank("query", [], top_k=5)
        assert result == []

    @pytest.mark.asyncio
    async def test_rerank_filters_by_threshold(
        self,
        reranker: GeminiPointwiseReranker,
        mock_candidates: list[SemanticSearchResult],
    ) -> None:
        """Test that rerank filters results below score threshold."""

        # Mock the _score_batch to return mixed scores
        async def mock_score_batch(query, batch):
            return {
                idx: 8.0 if idx < 5 else 3.0  # First 5 pass threshold, rest don't
                for idx, _ in batch
            }

        with patch.object(reranker, "_score_batch", side_effect=mock_score_batch):
            result = await reranker.rerank("test query", mock_candidates, top_k=10)

        # Only candidates with score >= 5.0 should be included
        assert len(result) == 5
        for res in result:
            assert float(res.metadata.get("reranker_score", 0)) >= 5.0

    @pytest.mark.asyncio
    async def test_rerank_preserves_metadata(
        self, reranker: GeminiPointwiseReranker
    ) -> None:
        """Test that rerank preserves original metadata and adds new fields."""
        candidates = [
            SemanticSearchResult(
                text="Test passage",
                score=0.9,
                metadata={"file_name": "test.txt", "chunk_id": "1"},
            )
        ]

        async def mock_score_batch(query, batch):
            return {0: 8.0}

        with patch.object(reranker, "_score_batch", side_effect=mock_score_batch):
            result = await reranker.rerank("query", candidates, top_k=1)

        assert len(result) == 1
        assert result[0].metadata["file_name"] == "test.txt"
        assert result[0].metadata["chunk_id"] == "1"
        assert result[0].metadata["original_score"] == "0.9"
        assert result[0].metadata["reranker_score"] == "8.0"

    @pytest.mark.asyncio
    async def test_rerank_uses_fallback_on_timeout(
        self,
        reranker: GeminiPointwiseReranker,
        mock_candidates: list[SemanticSearchResult],
    ) -> None:
        """Test that rerank falls back to original scores on timeout."""

        # Make _score_batch raise TimeoutError
        async def mock_timeout(*args):
            raise TimeoutError

        with patch.object(reranker, "_score_batch", side_effect=mock_timeout):
            result = await reranker.rerank("query", mock_candidates, top_k=5)

        # Should return top-5 by original score
        assert len(result) == 5
        # First result should have highest original score
        assert result[0].score == mock_candidates[0].score

    @pytest.mark.asyncio
    async def test_score_batch_maps_local_ids_to_original_indices(
        self,
        reranker: GeminiPointwiseReranker,
    ) -> None:
        """Ensure batch-local ids map back to the original candidate indices."""
        batch = [
            (2, SemanticSearchResult(text="p2", score=0.9, metadata={})),
            (6, SemanticSearchResult(text="p6", score=0.8, metadata={})),
        ]

        with patch.object(reranker, "_call_gemini", return_value='{"id0":9,"id1":6}'):
            scores = await reranker._score_batch("query", batch)

        assert scores == {2: 9.0, 6: 6.0}

    @pytest.mark.asyncio
    async def test_rerank_runs_batches_in_parallel(
        self,
        reranker: GeminiPointwiseReranker,
        mock_candidates: list[SemanticSearchResult],
    ) -> None:
        """Catch accidental serial execution by asserting on wall-clock time."""
        reranker.num_batches = 4

        async def slow_score_batch(_query, batch):
            import asyncio

            await asyncio.sleep(0.2)
            return {idx: 8.0 for idx, _ in batch}

        import time

        with patch.object(reranker, "_score_batch", side_effect=slow_score_batch):
            start = time.perf_counter()
            await reranker.rerank("query", mock_candidates, top_k=10)
            elapsed = time.perf_counter() - start

        assert elapsed < 0.6


class TestSettings:
    """Tests for RerankerSettings."""

    def test_default_settings(self) -> None:
        """Test default reranker settings."""
        from flare_ai_kit.rag.vector.settings import RerankerSettings

        settings = RerankerSettings()

        assert settings.enabled is False
        assert settings.model == "gemini-3-flash-preview"
        assert settings.num_batches == 4
        assert settings.timeout_seconds == 5.0
        assert settings.score_threshold == 5.0
        assert settings.few_shot_examples is None

    def test_custom_settings(self) -> None:
        """Test custom reranker settings."""
        from flare_ai_kit.rag.vector.settings import RerankerSettings

        settings = RerankerSettings(
            enabled=True,
            model="gemini-2.0-flash",  # Override with older model
            num_batches=8,
            timeout_seconds=10.0,
            score_threshold=7.0,
        )

        assert settings.enabled is True
        assert settings.model == "gemini-2.0-flash"
        assert settings.num_batches == 8
        assert settings.timeout_seconds == 10.0
        assert settings.score_threshold == 7.0
