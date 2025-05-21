"""Unit tests for Gemini agent implementation."""

import os
from unittest.mock import MagicMock, patch

from flare_ai_kit.agent.base import AgentInput
from flare_ai_kit.agent.gemini_agent import GeminiAgent, GeminiLLMAdapter


def test_gemini_adapter_initialization():
    """Test GeminiLLMAdapter initialization."""
    with patch.dict(os.environ, {"GOOGLE_GENAI_API_KEY": "test_key"}):
        adapter = GeminiLLMAdapter()
        assert adapter.api_key == "test_key"
        assert adapter.model == "gemini-pro"


def test_gemini_adapter_initialization_with_key():
    """Test GeminiLLMAdapter initialization with explicit API key."""
    adapter = GeminiLLMAdapter(api_key="explicit_key")
    assert adapter.api_key == "explicit_key"


def test_gemini_adapter_initialization_without_key():
    """Test GeminiLLMAdapter initialization without API key."""
    import pytest

    with (
        patch.dict(os.environ, {}, clear=True),
        pytest.raises(ValueError, match="Google Gemini API key not provided"),
    ):
        GeminiLLMAdapter()


def test_gemini_adapter_generate_text():
    """Test text generation with GeminiLLMAdapter."""
    mock_response = MagicMock()
    mock_response.text = "Generated response"
    mock_model = MagicMock()
    mock_model.generate_content.return_value = mock_response
    with patch("google.generativeai.GenerativeModel", return_value=mock_model):
        adapter = GeminiLLMAdapter(api_key="test_key")
        response = adapter.generate_text("test prompt")
        assert response == "Generated response"
        mock_model.generate_content.assert_called_once_with("test prompt")


def test_gemini_agent_initialization():
    """Test GeminiAgent initialization."""
    agent = GeminiAgent(llm_adapter=GeminiLLMAdapter(api_key="test_key"))
    assert agent.context is None


def test_gemini_agent_process_input():
    """Test GeminiAgent input processing."""
    mock_adapter = MagicMock(spec=GeminiLLMAdapter)
    mock_adapter.generate_text.return_value = "Generated response"
    agent = GeminiAgent(llm_adapter=mock_adapter)
    agent_input = AgentInput(message="test message")
    output = agent.process_input(agent_input)
    assert output.response == "Generated response"
    assert output.context is None
    mock_adapter.generate_text.assert_called_once_with(
        prompt="test message", context=None
    )


def test_gemini_agent_context_update():
    """Test GeminiAgent context update."""
    agent = GeminiAgent(llm_adapter=GeminiLLMAdapter(api_key="test_key"))
    context = {"key": "value"}
    agent.update_context(context)
    assert agent.context == context
