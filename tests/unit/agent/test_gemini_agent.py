"""Tests for Gemini agent implementation."""

from unittest.mock import MagicMock, patch

import pytest

from flare_ai_kit.agent.base import AgentInput
from flare_ai_kit.agent.gemini_agent import GeminiAgent, GeminiLLMAdapter


class TestGeminiLLMAdapter:
    """Test cases for GeminiLLMAdapter."""

    def test_initialization_with_api_key(self):
        """Test GeminiLLMAdapter initialization with API key."""
        with patch("google.genai.Client"):
            adapter = GeminiLLMAdapter(api_key="test_key")
            assert adapter.api_key == "test_key"
            assert adapter.model == "gemini-pro"

    def test_initialization_with_env_var(self):
        """Test GeminiLLMAdapter initialization with environment variable."""
        with patch.dict("os.environ", {"GOOGLE_API_KEY": "env_key"}):
            with patch("google.genai.Client"):
                adapter = GeminiLLMAdapter()
                assert adapter.api_key == "env_key"

    def test_initialization_without_api_key(self):
        """Test GeminiLLMAdapter initialization without API key raises error."""
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError, match="Google API key is required"):
                GeminiLLMAdapter()

    def test_generate_text(self):
        """Test text generation with GeminiLLMAdapter."""
        mock_response = MagicMock()
        mock_response.text = "Generated response"

        mock_models = MagicMock()
        mock_models.generate_content.return_value = mock_response

        mock_client = MagicMock()
        mock_client.models = mock_models

        with patch("google.genai.Client", return_value=mock_client):
            adapter = GeminiLLMAdapter(api_key="test_key")
            response = adapter.generate_text("test prompt")
            assert response == "Generated response"
            mock_models.generate_content.assert_called_once_with(
                model="gemini-pro", contents="test prompt"
            )


class TestGeminiAgent:
    """Test cases for GeminiAgent."""

    def test_initialization(self):
        """Test GeminiAgent initialization."""
        with patch("flare_ai_kit.agent.gemini_agent.GeminiLLMAdapter"):
            agent = GeminiAgent(api_key="test_key")
            assert agent.llm_adapter is not None

    def test_process_input(self):
        """Test processing input with GeminiAgent."""
        mock_adapter = MagicMock()
        mock_adapter.generate_text.return_value = "Test response"

        with patch(
            "flare_ai_kit.agent.gemini_agent.GeminiLLMAdapter",
            return_value=mock_adapter,
        ):
            agent = GeminiAgent(api_key="test_key")

            input_data = AgentInput(
                message="Hello, how are you?", context="Test context"
            )

            output = agent.process(input_data)

            assert output.response == "Test response"
            assert len(output.conversation_history) == 2
            assert output.conversation_history[0].role == "user"
            assert output.conversation_history[0].content == "Hello, how are you?"
            assert output.conversation_history[1].role == "assistant"
            assert output.conversation_history[1].content == "Test response"

            mock_adapter.generate_text.assert_called_once_with(
                prompt="Hello, how are you?", context="Test context"
            )
