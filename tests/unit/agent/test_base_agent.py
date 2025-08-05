"""Unit tests for the BaseAgent class."""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from flare_ai_kit.agent.base import (
    BaseAgent,
    AgentContext,
    AgentResponse,
    ConversationMessage,
    AgentError
)


class TestBaseAgent:
    """Test cases for BaseAgent abstract class."""
    
    class MockAgent(BaseAgent):
        """Mock agent implementation for testing."""
        
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.setup_called = False
            self.response_content = "Mock response"
            
        async def _setup(self):
            self.setup_called = True
            
        async def _generate_response(self, user_input, include_history=True, **kwargs):
            return AgentResponse(
                content=self.response_content,
                agent_id=self.agent_id,
                metadata={"mock": True}
            )
    
    def test_agent_initialization(self):
        """Test agent initialization with basic parameters."""
        agent = self.MockAgent(
            agent_id="test-agent",
            agent_name="Test Agent",
            system_prompt="You are a test agent",
            max_history_length=10
        )
        
        assert agent.agent_id == "test-agent"
        assert agent.agent_name == "Test Agent"
        assert agent.context.system_prompt == "You are a test agent"
        assert agent.context.max_history_length == 10
        assert not agent.is_initialized
        assert len(agent.context.conversation_history) == 0
        
    def test_agent_context_validation(self):
        """Test that AgentContext validates properly."""
        # Test valid context
        context = AgentContext(
            agent_id="test",
            agent_name="Test Agent"
        )
        assert context.agent_id == "test"
        assert context.agent_name == "Test Agent"
        assert isinstance(context.created_at, datetime)
        
        # Test context immutability for messages
        message = ConversationMessage(
            role="user",
            content="Hello"
        )
        assert message.role == "user"
        assert message.content == "Hello"
        assert isinstance(message.timestamp, datetime)
        
    @pytest.mark.asyncio
    async def test_agent_initialization_lifecycle(self):
        """Test agent initialization lifecycle."""
        agent = self.MockAgent("test-agent", "Test Agent")
        
        # Should not be initialized initially
        assert not agent.is_initialized
        assert not agent.setup_called
        
        # Initialize the agent
        await agent.initialize()
        
        # Should be initialized now
        assert agent.is_initialized
        assert agent.setup_called
        
        # Calling initialize again should not raise error
        await agent.initialize()
        
    @pytest.mark.asyncio
    async def test_process_input_without_initialization(self):
        """Test that processing input without initialization raises error."""
        agent = self.MockAgent("test-agent", "Test Agent")
        
        with pytest.raises(AgentError, match="Agent must be initialized"):
            await agent.process_input("Hello")
            
    @pytest.mark.asyncio
    async def test_process_input_success(self):
        """Test successful input processing."""
        agent = self.MockAgent("test-agent", "Test Agent")
        await agent.initialize()
        
        response = await agent.process_input("Hello, how are you?")
        
        assert isinstance(response, AgentResponse)
        assert response.content == "Mock response"
        assert response.agent_id == "test-agent"
        assert response.metadata["mock"] is True
        
        # Check conversation history
        history = agent.get_conversation_history()
        assert len(history) == 2  # User message + assistant response
        
        user_msg = history[0]
        assert user_msg.role == "user"
        assert user_msg.content == "Hello, how are you?"
        
        assistant_msg = history[1]
        assert assistant_msg.role == "assistant"
        assert assistant_msg.content == "Mock response"
        
    def test_conversation_history_management(self):
        """Test conversation history management."""
        agent = self.MockAgent("test-agent", "Test Agent", max_history_length=3)
        
        # Add messages manually
        for i in range(5):
            message = ConversationMessage(
                role="user" if i % 2 == 0 else "assistant",
                content=f"Message {i}"
            )
            agent._add_to_history(message)
            
        # Should only keep last 3 messages
        history = agent.get_conversation_history()
        assert len(history) == 3
        assert history[0].content == "Message 2"
        assert history[1].content == "Message 3"
        assert history[2].content == "Message 4"
        
    def test_conversation_history_filtering(self):
        """Test conversation history filtering by role and limit."""
        agent = self.MockAgent("test-agent", "Test Agent")
        
        # Add mixed messages
        messages = [
            ("user", "User 1"),
            ("assistant", "Assistant 1"),
            ("user", "User 2"),
            ("assistant", "Assistant 2"),
            ("system", "System 1")
        ]
        
        for role, content in messages:
            agent._add_to_history(ConversationMessage(role=role, content=content))
            
        # Test role filtering
        user_messages = agent.get_conversation_history(role_filter="user")
        assert len(user_messages) == 2
        assert all(msg.role == "user" for msg in user_messages)
        
        # Test limit
        limited_messages = agent.get_conversation_history(limit=2)
        assert len(limited_messages) == 2
        assert limited_messages[0].content == "Assistant 2"
        assert limited_messages[1].content == "System 1"
        
    def test_clear_history(self):
        """Test clearing conversation history."""
        agent = self.MockAgent("test-agent", "Test Agent")
        
        # Add some messages
        agent._add_to_history(ConversationMessage(role="user", content="Hello"))
        agent._add_to_history(ConversationMessage(role="assistant", content="Hi"))
        
        assert len(agent.get_conversation_history()) == 2
        
        # Clear history
        agent.clear_history()
        assert len(agent.get_conversation_history()) == 0
        
    def test_system_prompt_update(self):
        """Test updating system prompt."""
        agent = self.MockAgent("test-agent", "Test Agent", system_prompt="Original")
        
        assert agent.context.system_prompt == "Original"
        
        agent.set_system_prompt("Updated prompt")
        assert agent.context.system_prompt == "Updated prompt"
        
    def test_custom_data_management(self):
        """Test custom data management."""
        agent = self.MockAgent("test-agent", "Test Agent")
        
        # Add custom data
        agent.add_custom_data("key1", "value1")
        agent.add_custom_data("key2", {"nested": "data"})
        
        # Retrieve custom data
        assert agent.get_custom_data("key1") == "value1"
        assert agent.get_custom_data("key2") == {"nested": "data"}
        assert agent.get_custom_data("nonexistent") is None
        assert agent.get_custom_data("nonexistent", "default") == "default"
        
    def test_update_context(self):
        """Test context updating."""
        agent = self.MockAgent("test-agent", "Test Agent")
        original_time = agent.context.created_at
        
        # Update context
        agent.update_context(
            system_prompt="New prompt",
            max_history_length=100
        )
        
        assert agent.context.system_prompt == "New prompt"
        assert agent.context.max_history_length == 100
        assert agent.context.updated_at > original_time
        
    def test_build_conversation_context(self):
        """Test building conversation context for LLM."""
        agent = self.MockAgent("test-agent", "Test Agent", system_prompt="System prompt")
        
        # Add conversation history
        agent._add_to_history(ConversationMessage(role="user", content="Hello"))
        agent._add_to_history(ConversationMessage(role="assistant", content="Hi there"))
        agent._add_to_history(ConversationMessage(role="system", content="System message"))
        
        context = agent._build_conversation_context()
        
        # Should contain system prompt and conversation history
        assert "System: System prompt" in context
        assert "User: Hello" in context
        assert "Assistant: Hi there" in context
        assert "System: System message" in context
        
    def test_agent_representation(self):
        """Test agent string representation."""
        agent = self.MockAgent("test-agent", "Test Agent")
        
        repr_str = repr(agent)
        assert "MockAgent" in repr_str
        assert "test-agent" in repr_str
        assert "Test Agent" in repr_str


class TestConversationMessage:
    """Test cases for ConversationMessage model."""
    
    def test_message_creation(self):
        """Test creating conversation messages."""
        message = ConversationMessage(
            role="user",
            content="Hello world"
        )
        
        assert message.role == "user"
        assert message.content == "Hello world"
        assert isinstance(message.timestamp, datetime)
        assert message.timestamp.tzinfo == timezone.utc
        assert message.metadata == {}
        
    def test_message_with_metadata(self):
        """Test creating messages with metadata."""
        message = ConversationMessage(
            role="assistant",
            content="Response",
            metadata={"confidence": 0.95, "source": "test"}
        )
        
        assert message.metadata["confidence"] == 0.95
        assert message.metadata["source"] == "test"
        
    def test_message_immutability(self):
        """Test that messages are immutable."""
        message = ConversationMessage(role="user", content="Hello")
        
        # Should not be able to modify
        with pytest.raises(Exception):  # Pydantic will raise validation error
            message.role = "assistant"


class TestAgentResponse:
    """Test cases for AgentResponse model."""
    
    def test_response_creation(self):
        """Test creating agent responses."""
        response = AgentResponse(
            content="Hello there!",
            agent_id="test-agent"
        )
        
        assert response.content == "Hello there!"
        assert response.agent_id == "test-agent"
        assert isinstance(response.timestamp, datetime)
        assert response.metadata == {}
        assert response.usage_info is None
        
    def test_response_with_usage_info(self):
        """Test response with usage information."""
        usage_info = {
            "input_tokens": 10,
            "output_tokens": 5,
            "total_tokens": 15
        }
        
        response = AgentResponse(
            content="Response",
            agent_id="test-agent",
            usage_info=usage_info
        )
        
        assert response.usage_info == usage_info
        
    def test_response_immutability(self):
        """Test that responses are immutable."""
        response = AgentResponse(content="Hello", agent_id="test")
        
        # Should not be able to modify
        with pytest.raises(Exception):  # Pydantic will raise validation error
            response.content = "Modified"


class TestAgentError:
    """Test cases for AgentError exception."""
    
    def test_agent_error_creation(self):
        """Test creating agent errors."""
        error = AgentError("Something went wrong")
        assert str(error) == "Something went wrong"
        assert isinstance(error, Exception)
        
    def test_agent_error_inheritance(self):
        """Test that AgentError inherits from FlareAIKitError."""
        from flare_ai_kit.common.exceptions import FlareAIKitError
        
        error = AgentError("Test error")
        assert isinstance(error, FlareAIKitError)
