"""Unit tests for the GeminiAgent class."""

from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest

from flare_ai_kit.agent.base import AgentError, AgentResponse
from flare_ai_kit.agent.gemini_agent import GeminiAgent


class TestGeminiAgent:
    """Test cases for GeminiAgent class."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings for testing."""
        with patch("flare_ai_kit.agent.settings.AgentSettings") as mock:
            settings = MagicMock()
            settings.gemini_api_key.get_secret_value.return_value = "test-api-key"
            settings.gemini_model = "gemini-2.5-flash"
            mock.return_value = settings
            return settings

    @pytest.fixture
    def gemini_agent(self, mock_settings):
        """Create a GeminiAgent instance for testing."""
        return GeminiAgent(
            agent_id="gemini-test",
            agent_name="Gemini Test Agent",
            system_prompt="You are a helpful assistant",
            settings=mock_settings,
        )

    def test_gemini_agent_initialization(self, mock_settings):
        """Test GeminiAgent initialization."""
        agent = GeminiAgent(
            agent_id="test-agent",
            agent_name="Test Agent",
            system_prompt="Test prompt",
            model_name="gemini-2.5-pro",
            temperature=0.5,
            max_tokens=1000,
            settings=mock_settings,
        )

        assert agent.agent_id == "test-agent"
        assert agent.agent_name == "Test Agent"
        assert agent.context.system_prompt == "Test prompt"
        assert agent.model_name == "gemini-2.5-pro"
        assert agent.temperature == 0.5
        assert agent.max_tokens == 1000
        assert agent.settings == mock_settings
        assert not agent.is_initialized

    def test_gemini_agent_default_settings(self):
        """Test GeminiAgent with default settings."""
        with patch(
            "flare_ai_kit.agent.gemini_agent.AgentSettings"
        ) as mock_settings_class:
            mock_settings = MagicMock()
            mock_settings.gemini_api_key.get_secret_value.return_value = "test-key"
            mock_settings.gemini_model = "gemini-2.5-flash"
            mock_settings_class.return_value = mock_settings

            agent = GeminiAgent("test", "Test")

            assert agent.settings == mock_settings
            assert agent.model_name == "gemini-2.5-flash"
            assert agent.temperature == 0.7  # default

    @pytest.mark.asyncio
    async def test_gemini_setup_success(self, gemini_agent):
        """Test successful Gemini agent setup."""
        with (
            patch("flare_ai_kit.agent.gemini_agent.genai.Client") as mock_client_class,
            patch("flare_ai_kit.agent.gemini_agent.GeminiModel") as mock_model_class,
            patch("flare_ai_kit.agent.gemini_agent.PydanticAgent") as mock_agent_class,
        ):
            mock_client = MagicMock()
            mock_model = MagicMock()
            mock_pydantic_agent = MagicMock()

            mock_client_class.return_value = mock_client
            mock_model_class.return_value = mock_model
            mock_agent_class.return_value = mock_pydantic_agent

            await gemini_agent.initialize()

            assert gemini_agent.is_initialized
            assert gemini_agent._gemini_client == mock_client
            assert gemini_agent._pydantic_agent == mock_pydantic_agent

            # Verify client was created with correct API key
            mock_client_class.assert_called_once_with(api_key="test-api-key")

            # Verify model was created with correct parameters
            mock_model_class.assert_called_once_with(model_name="gemini-2.5-flash")

            # Verify PydanticAgent was created
            mock_agent_class.assert_called_once_with(
                model=mock_model, system_prompt="You are a helpful assistant"
            )

    @pytest.mark.asyncio
    async def test_gemini_setup_failure(self, gemini_agent):
        """Test Gemini agent setup failure."""
        with patch("flare_ai_kit.agent.gemini_agent.genai.Client") as mock_client_class:
            mock_client_class.side_effect = Exception("API connection failed")

            with pytest.raises(AgentError, match="Failed to setup Gemini agent"):
                await gemini_agent.initialize()

            assert not gemini_agent.is_initialized

    @pytest.mark.asyncio
    async def test_generate_response_without_history(self, gemini_agent):
        """Test generating response without conversation history."""
        # Setup mocks
        mock_result = MagicMock()
        mock_result.data = "Hello! How can I help you?"
        mock_result.usage = None  # Simplified - no usage info for this test

        mock_pydantic_agent = AsyncMock()
        mock_pydantic_agent.run.return_value = mock_result

        gemini_agent._pydantic_agent = mock_pydantic_agent
        gemini_agent._initialized = True

        response = await gemini_agent._generate_response("Hello", include_history=False)

        assert isinstance(response, AgentResponse)
        assert response.content == "Hello! How can I help you?"
        assert response.agent_id == "gemini-test"
        # Since we set usage to None, usage_info should also be None
        assert response.usage_info is None

    @pytest.mark.asyncio
    async def test_generate_response_with_usage_info(self, gemini_agent):
        """Test generating response with usage information."""

        # Create a simple object instead of MagicMock for usage
        class MockUsage:
            def __init__(self):
                self.input_tokens = 10
                self.output_tokens = 8
                self.total_tokens = 18

        mock_result = MagicMock()
        mock_result.data = "Hello! How can I help you?"
        mock_result.usage = MockUsage()

        mock_pydantic_agent = AsyncMock()
        mock_pydantic_agent.run.return_value = mock_result

        gemini_agent._pydantic_agent = mock_pydantic_agent
        gemini_agent._initialized = True

        response = await gemini_agent._generate_response("Hello", include_history=False)

        assert isinstance(response, AgentResponse)
        assert response.content == "Hello! How can I help you?"
        assert response.agent_id == "gemini-test"
        assert response.usage_info is not None
        assert response.usage_info["input_tokens"] == 10
        assert response.usage_info["output_tokens"] == 8
        assert response.usage_info["total_tokens"] == 18
        assert response.metadata["model_name"] == "gemini-2.5-flash"

        # Verify the agent was called with just the user input
        mock_pydantic_agent.run.assert_called_once_with("Hello")

    @pytest.mark.asyncio
    async def test_generate_response_with_history(self, gemini_agent):
        """Test generating response with conversation history."""
        # Add some conversation history
        from flare_ai_kit.agent.base import ConversationMessage

        gemini_agent._add_to_history(ConversationMessage(role="user", content="Hi"))
        gemini_agent._add_to_history(
            ConversationMessage(role="assistant", content="Hello!")
        )

        mock_result = MagicMock()
        mock_result.data = "How can I help you?"

        mock_pydantic_agent = AsyncMock()
        mock_pydantic_agent.run.return_value = mock_result

        gemini_agent._pydantic_agent = mock_pydantic_agent
        gemini_agent._initialized = True

        response = await gemini_agent._generate_response(
            "What's the weather?", include_history=True
        )

        # Verify the agent was called with history context
        call_args = mock_pydantic_agent.run.call_args[0][0]
        assert "Previous conversation:" in call_args
        assert "User: Hi" in call_args
        assert "Assistant: Hello!" in call_args
        assert "User: What's the weather?" in call_args

    @pytest.mark.asyncio
    async def test_generate_response_not_initialized(self, gemini_agent):
        """Test generating response when agent not initialized."""
        with pytest.raises(AgentError, match="Agent not properly initialized"):
            await gemini_agent._generate_response("Hello")

    @pytest.mark.asyncio
    async def test_generate_response_failure(self, gemini_agent):
        """Test response generation failure."""
        mock_pydantic_agent = AsyncMock()
        mock_pydantic_agent.run.side_effect = Exception("Generation failed")

        gemini_agent._pydantic_agent = mock_pydantic_agent
        gemini_agent._initialized = True

        with pytest.raises(AgentError, match="Failed to generate response"):
            await gemini_agent._generate_response("Hello")

    @pytest.mark.asyncio
    async def test_generate_embedding(self, gemini_agent):
        """Test generating embeddings."""
        # Since we're using mock embeddings, we just need to ensure
        # the client is initialized and the method works
        mock_client = AsyncMock()
        gemini_agent._gemini_client = mock_client
        gemini_agent._initialized = True

        embeddings = await gemini_agent.generate_embedding("Hello world")

        # Check that we get a list of floats with the expected dimension
        assert isinstance(embeddings, list)
        assert len(embeddings) == 768  # Expected dimension
        assert all(isinstance(x, float) for x in embeddings)

        # Test deterministic behavior - same input should give same output
        embeddings2 = await gemini_agent.generate_embedding("Hello world")
        assert embeddings == embeddings2

    @pytest.mark.asyncio
    async def test_generate_embedding_not_initialized(self, gemini_agent):
        """Test generating embedding when not initialized."""
        with pytest.raises(AgentError, match="Agent not properly initialized"):
            await gemini_agent.generate_embedding("Hello")

    @pytest.mark.asyncio
    async def test_stream_response(self, gemini_agent):
        """Test streaming response generation."""
        # Mock the regular response generation since our streaming
        # implementation uses that and then chunks the result
        mock_result = MagicMock()
        mock_result.data = "Hello there, this is a test response!"

        mock_pydantic_agent = AsyncMock()
        mock_pydantic_agent.run.return_value = mock_result

        gemini_agent._pydantic_agent = mock_pydantic_agent
        gemini_agent._initialized = True

        chunks = []
        async for chunk in gemini_agent.stream_response("Hello"):
            chunks.append(chunk)

        # Verify we got chunks and they combine to the original response
        assert len(chunks) > 0
        combined_response = "".join(chunks)
        assert combined_response == "Hello there, this is a test response!"

        # Verify the underlying agent was called
        mock_pydantic_agent.run.assert_called_once()

    @pytest.mark.asyncio
    async def test_stream_response_not_initialized(self, gemini_agent):
        """Test streaming when not initialized."""
        with pytest.raises(AgentError, match="Agent not properly initialized"):
            async for chunk in gemini_agent.stream_response("Hello"):
                pass

    def test_update_model_parameters(self, gemini_agent):
        """Test updating model parameters."""
        gemini_agent.update_model_parameters(
            temperature=0.9, max_tokens=2000, top_p=0.95
        )

        assert gemini_agent.temperature == 0.9
        assert gemini_agent.max_tokens == 2000
        assert gemini_agent.get_custom_data("model_top_p") == 0.95

    @pytest.mark.asyncio
    async def test_test_connection_success(self, gemini_agent):
        """Test successful connection test."""
        mock_result = MagicMock()
        mock_result.data = "Connection successful"

        mock_pydantic_agent = AsyncMock()
        mock_pydantic_agent.run.return_value = mock_result

        gemini_agent._pydantic_agent = mock_pydantic_agent
        gemini_agent._gemini_client = MagicMock()
        gemini_agent._initialized = True

        result = await gemini_agent.test_connection()

        assert result["status"] == "success"
        assert result["model_name"] == "gemini-2.5-flash"
        assert result["response"] == "Connection successful"
        assert "test_prompt" in result

    @pytest.mark.asyncio
    async def test_test_connection_failure(self, gemini_agent):
        """Test connection test failure."""
        mock_pydantic_agent = AsyncMock()
        mock_pydantic_agent.run.side_effect = Exception("Connection failed")

        gemini_agent._pydantic_agent = mock_pydantic_agent
        gemini_agent._gemini_client = MagicMock()
        gemini_agent._initialized = True

        result = await gemini_agent.test_connection()

        assert result["status"] == "failed"
        assert "Connection failed" in result["error"]
        assert result["model_name"] == "gemini-2.5-flash"

    @pytest.mark.asyncio
    async def test_test_connection_not_initialized(self, gemini_agent):
        """Test connection test when not initialized."""
        with pytest.raises(AgentError, match="Agent not properly initialized"):
            await gemini_agent.test_connection()

    def test_model_info_property(self, gemini_agent):
        """Test model info property."""
        gemini_agent.temperature = 0.8
        gemini_agent.max_tokens = 1500

        info = gemini_agent.model_info

        assert info["model_name"] == "gemini-2.5-flash"
        assert info["temperature"] == 0.8
        assert info["max_tokens"] == 1500
        assert info["provider"] == "google_gemini"

    @pytest.mark.asyncio
    async def test_full_agent_workflow(self, gemini_agent):
        """Test complete agent workflow from initialization to response."""
        # Mock the dependencies
        with (
            patch("flare_ai_kit.agent.gemini_agent.genai.Client") as mock_client_class,
            patch("flare_ai_kit.agent.gemini_agent.GeminiModel") as mock_model_class,
            patch("flare_ai_kit.agent.gemini_agent.PydanticAgent") as mock_agent_class,
        ):
            # Setup mocks
            mock_client = MagicMock()
            mock_model = MagicMock()
            mock_result = MagicMock()
            mock_result.data = "Hello! How can I help you today?"

            mock_pydantic_agent = AsyncMock()
            mock_pydantic_agent.run.return_value = mock_result

            mock_client_class.return_value = mock_client
            mock_model_class.return_value = mock_model
            mock_agent_class.return_value = mock_pydantic_agent

            # Initialize and process input
            await gemini_agent.initialize()
            response = await gemini_agent.process_input("Hello there!")

            # Verify the complete workflow
            assert gemini_agent.is_initialized
            assert isinstance(response, AgentResponse)
            assert response.content == "Hello! How can I help you today?"
            assert len(gemini_agent.get_conversation_history()) == 2  # User + Assistant
