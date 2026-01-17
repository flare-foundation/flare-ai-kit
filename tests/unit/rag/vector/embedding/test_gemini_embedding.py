from unittest.mock import MagicMock, patch

import pytest

from flare_ai_kit.common import EmbeddingsError
from flare_ai_kit.rag.vector.embedding.gemini_embedding import GeminiEmbedding


@pytest.fixture
def mock_client():
    """Mocked genai.Client with embed_content behavior."""
    client = MagicMock()
    client.models.embed_content = MagicMock()
    return client


@pytest.fixture
def gemini_embedding(mock_client):
    with patch(
        "flare_ai_kit.rag.vector.embedding.gemini_embedding.genai.Client",
        return_value=mock_client,
    ):
        return GeminiEmbedding(
            api_key="fake-key", model="models/embedding-001", output_dimensionality=128
        )


def test_init_sets_attributes(gemini_embedding):
    assert gemini_embedding.model == "models/embedding-001"
    assert gemini_embedding.output_dimensionality == 128
    assert hasattr(gemini_embedding.client, "models")


@pytest.mark.parametrize("empty_input", ["", []])
def test_empty_content_returns_empty_list(gemini_embedding, empty_input):
    assert gemini_embedding.embed_content(empty_input) == []


def test_successful_embedding_returns_values(gemini_embedding, mock_client):
    # Mock response with correct number of embeddings
    mock_response = MagicMock()
    mock_response.embeddings = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
    mock_client.models.embed_content.return_value = mock_response

    contents = ["text1", "text2"]
    result = gemini_embedding.embed_content(contents)

    assert result == [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
    mock_client.models.embed_content.assert_called_once()
    call_args = mock_client.models.embed_content.call_args[1]
    assert call_args["model"] == "models/embedding-001"
    assert call_args["contents"] == contents


def test_mismatch_raises_embeddings_error(gemini_embedding, mock_client):
    # Mock response with fewer embeddings than inputs
    mock_response = MagicMock()
    mock_response.embeddings = [[0.1, 0.2, 0.3]]
    mock_client.models.embed_content.return_value = mock_response

    with pytest.raises(EmbeddingsError) as exc:
        gemini_embedding.embed_content(["a", "b"])

    assert "Expected 2 embeddings" in str(exc.value)


def test_no_embeddings_raises_embeddings_error(gemini_embedding, mock_client):
    # Mock response without embeddings attribute
    mock_response = MagicMock()
    mock_response.embeddings = []
    mock_client.models.embed_content.return_value = mock_response

    with pytest.raises(EmbeddingsError) as exc:
        gemini_embedding.embed_content("hello")

    assert "Gemini API call succeeded but returned no embeddings" in str(exc.value)
