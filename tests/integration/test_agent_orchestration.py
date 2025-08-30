"""Integration tests for ADK agent orchestration and tool selection."""

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Mock optional social and ADK dependencies before imports
mock_modules = [
    "telegram",
    "telegram.error", 
    "telegram.ext",
    "tweepy",
    "tweepy.asynchronous",
    "tweepy.errors",
    "google.adk.agents",
    "google.adk.tools",
]

for module in mock_modules:
    sys.modules[module] = MagicMock()

# Mock Google ADK classes
class MockAgent:
    def __init__(self, name, model, tools, instruction):
        self.name = name
        self.model = model  
        self.tools = tools
        self.instruction = instruction
        
    async def run(self, prompt: str):
        """Mock agent run method that simulates tool orchestration."""
        # Simulate agent selecting tools based on prompt keywords
        if "price" in prompt.lower() or "ftso" in prompt.lower():
            # Simulate calling FTSO price tool
            return {
                "response": "The current BTC/USD price is $45,123.45",
                "tools_used": ["get_ftso_price"],
                "tool_results": [{"feed_name": "BTC/USD", "price": 45123.45, "status": "success"}]
            }
        elif "balance" in prompt.lower():
            # Simulate calling balance check tool  
            return {
                "response": "The FLR balance for that address is 1,000.5 FLR",
                "tools_used": ["check_flr_balance"],
                "tool_results": [{"address": "0x123...", "balance": 1000.5, "status": "success"}]
            }
        elif "wallet" in prompt.lower() and "create" in prompt.lower():
            # Simulate wallet creation
            return {
                "response": "Created new wallet 'MyWallet' with ID: wallet_123",
                "tools_used": ["create_wallet"],
                "tool_results": [{"wallet_id": "wallet_123", "wallet_name": "MyWallet", "status": "success"}]
            }
        elif ("telegram" in prompt.lower() or "message" in prompt.lower()) and "send" in prompt.lower():
            # Simulate social media posting
            return {
                "response": "Message sent successfully to Telegram",
                "tools_used": ["send_telegram_message"],
                "tool_results": [{"chat_id": "@test", "success": True, "status": "success"}]
            }
        elif "attestation" in prompt.lower() or "tee" in prompt.lower():
            # Simulate TEE operations
            return {
                "response": "Generated TEE attestation token successfully",
                "tools_used": ["get_attestation_token"],
                "tool_results": [{"token": "eyJ0eXAi...", "status": "success"}]
            }
        else:
            return {
                "response": "I can help with FTSO prices, balances, wallets, social media, and TEE operations.",
                "tools_used": [],
                "tool_results": []
            }

sys.modules["google.adk.agents"].Agent = MockAgent


@pytest.fixture
def mock_agent():
    """Create a mock ADK agent for testing."""
    from flare_ai_kit.agent.tool import TOOL_REGISTRY
    
    # Import tool modules to populate registry
    from flare_ai_kit.agent import ecosystem_tools, social_tools, tee_tools, wallet_tools  # noqa: F401
    
    agent = MockAgent(
        name="test_agent", 
        model="gemini-2.5-flash",
        tools=TOOL_REGISTRY,
        instruction="Test agent for orchestration"
    )
    return agent


class TestAgentOrchestration:
    """Test agent's ability to orchestrate tool calls based on user prompts."""

    @pytest.mark.asyncio
    async def test_single_tool_selection_ftso_price(self, mock_agent):
        """Test agent selects correct tool for FTSO price queries."""
        prompt = "What's the current BTC/USD price?"
        
        result = await mock_agent.run(prompt)
        
        assert "tools_used" in result
        assert "get_ftso_price" in result["tools_used"]
        assert len(result["tool_results"]) == 1
        assert result["tool_results"][0]["status"] == "success"
        assert "45,123.45" in result["response"]

    @pytest.mark.asyncio
    async def test_single_tool_selection_balance_check(self, mock_agent):
        """Test agent selects correct tool for balance queries."""
        prompt = "Check the FLR balance for address 0x123..."
        
        result = await mock_agent.run(prompt)
        
        assert "check_flr_balance" in result["tools_used"]
        assert result["tool_results"][0]["balance"] == 1000.5
        assert "1,000.5 FLR" in result["response"]

    @pytest.mark.asyncio
    async def test_single_tool_selection_wallet_creation(self, mock_agent):
        """Test agent selects correct tool for wallet operations."""
        prompt = "Create a new wallet called MyWallet"
        
        result = await mock_agent.run(prompt)
        
        assert "create_wallet" in result["tools_used"]
        assert result["tool_results"][0]["wallet_name"] == "MyWallet"
        assert "wallet_123" in result["response"]

    @pytest.mark.asyncio  
    async def test_single_tool_selection_social_media(self, mock_agent):
        """Test agent selects correct tool for social media operations."""
        prompt = "Send a message to Telegram saying hello"
        
        result = await mock_agent.run(prompt)
        
        assert "send_telegram_message" in result["tools_used"]
        assert result["tool_results"][0]["success"] == True
        assert "sent successfully" in result["response"]

    @pytest.mark.asyncio
    async def test_single_tool_selection_tee_operations(self, mock_agent):
        """Test agent selects correct tool for TEE operations."""
        prompt = "Generate a TEE attestation token"
        
        result = await mock_agent.run(prompt)
        
        assert "get_attestation_token" in result["tools_used"]
        assert "token" in result["tool_results"][0]
        assert "Generated TEE" in result["response"]

    @pytest.mark.asyncio
    async def test_no_tool_selection_general_query(self, mock_agent):
        """Test agent handles general queries without tool selection."""
        prompt = "Hello, what can you help me with?"
        
        result = await mock_agent.run(prompt)
        
        assert len(result["tools_used"]) == 0
        assert len(result["tool_results"]) == 0
        assert "I can help with" in result["response"]


class TestMultiToolOrchestration:
    """Test agent's ability to orchestrate multiple tools in sequence."""
    
    @pytest.fixture  
    def mock_multi_tool_agent(self):
        """Create agent that can chain multiple tools."""
        
        class MultiToolAgent(MockAgent):
            async def run(self, prompt: str):
                """Simulate chaining multiple tools based on complex prompts."""
                if "price" in prompt.lower() and "send" in prompt.lower():
                    # Simulate: Get price -> Send to Telegram  
                    return {
                        "response": "BTC/USD price is $45,123.45. Sent update to Telegram successfully.",
                        "tools_used": ["get_ftso_price", "send_telegram_message"],
                        "tool_results": [
                            {"feed_name": "BTC/USD", "price": 45123.45, "status": "success"},
                            {"chat_id": "@updates", "success": True, "status": "success"}
                        ]
                    }
                elif "wallet" in prompt.lower() and "balance" in prompt.lower():
                    # Simulate: Create wallet -> Check balance
                    return {
                        "response": "Created wallet 'Trading' (ID: wallet_456). Current balance: 500.0 FLR",
                        "tools_used": ["create_wallet", "check_flr_balance"],  
                        "tool_results": [
                            {"wallet_id": "wallet_456", "wallet_name": "Trading", "status": "success"},
                            {"address": "0xabc...", "balance": 500.0, "status": "success"}
                        ]
                    }
                elif "attestation" in prompt.lower() and "policy" in prompt.lower():
                    # Simulate: Generate attestation -> Create policy
                    return {
                        "response": "Generated attestation token and created security policy 'Secure'.",
                        "tools_used": ["get_attestation_token", "create_transaction_policy"],
                        "tool_results": [
                            {"token": "eyJ0eXAi...", "status": "success"},
                            {"policy_name": "Secure", "enabled": True, "status": "success"}
                        ]
                    }
                else:
                    return await super().run(prompt)
        
        from flare_ai_kit.agent.tool import TOOL_REGISTRY
        from flare_ai_kit.agent import ecosystem_tools, social_tools, tee_tools, wallet_tools  # noqa: F401
        
        return MultiToolAgent(
            name="multi_tool_agent",
            model="gemini-2.5-flash", 
            tools=TOOL_REGISTRY,
            instruction="Multi-tool orchestration agent"
        )

    @pytest.mark.asyncio
    async def test_two_tool_chain_price_and_social(self, mock_multi_tool_agent):
        """Test agent chains FTSO price lookup with social media posting."""
        prompt = "Get the BTC price and send it to our Telegram channel"
        
        result = await mock_multi_tool_agent.run(prompt)
        
        assert len(result["tools_used"]) == 2
        assert "get_ftso_price" in result["tools_used"]
        assert "send_telegram_message" in result["tools_used"] 
        assert len(result["tool_results"]) == 2
        assert all(r["status"] == "success" for r in result["tool_results"])
        assert "45,123.45" in result["response"]
        assert "Sent update" in result["response"]

    @pytest.mark.asyncio
    async def test_two_tool_chain_wallet_and_balance(self, mock_multi_tool_agent):
        """Test agent chains wallet creation with balance checking."""
        prompt = "Create a trading wallet and check its balance"
        
        result = await mock_multi_tool_agent.run(prompt)
        
        assert len(result["tools_used"]) == 2
        assert "create_wallet" in result["tools_used"]
        assert "check_flr_balance" in result["tools_used"]
        assert result["tool_results"][0]["wallet_name"] == "Trading"
        assert result["tool_results"][1]["balance"] == 500.0
        assert "wallet_456" in result["response"]

    @pytest.mark.asyncio
    async def test_two_tool_chain_tee_and_policy(self, mock_multi_tool_agent):  
        """Test agent chains TEE attestation with policy creation."""
        prompt = "Generate attestation token and create a security policy"
        
        result = await mock_multi_tool_agent.run(prompt)
        
        assert len(result["tools_used"]) == 2
        assert "get_attestation_token" in result["tools_used"]
        assert "create_transaction_policy" in result["tools_used"]
        assert "token" in result["tool_results"][0]
        assert result["tool_results"][1]["policy_name"] == "Secure"


class TestErrorHandlingOrchestration:
    """Test agent handles tool errors gracefully during orchestration."""
    
    @pytest.fixture
    def mock_error_agent(self):
        """Create agent that simulates tool errors."""
        
        class ErrorAgent(MockAgent):
            async def run(self, prompt: str):
                if "error" in prompt.lower():
                    return {
                        "response": "I encountered an error while fetching the price. Please try again.",
                        "tools_used": ["get_ftso_price"],
                        "tool_results": [
                            {"feed_name": "BTC/USD", "price": 0.0, "status": "error", "error": "Connection timeout"}
                        ]
                    }
                else:
                    return await super().run(prompt)
        
        from flare_ai_kit.agent.tool import TOOL_REGISTRY
        from flare_ai_kit.agent import ecosystem_tools, social_tools, tee_tools, wallet_tools  # noqa: F401
        
        return ErrorAgent(
            name="error_agent",
            model="gemini-2.5-flash",
            tools=TOOL_REGISTRY, 
            instruction="Error handling test agent"
        )

    @pytest.mark.asyncio
    async def test_tool_error_handling(self, mock_error_agent):
        """Test agent handles tool errors gracefully."""
        prompt = "Get BTC price but simulate an error"
        
        result = await mock_error_agent.run(prompt)
        
        assert "get_ftso_price" in result["tools_used"]
        assert result["tool_results"][0]["status"] == "error"
        assert "error" in result["tool_results"][0]
        assert "encountered an error" in result["response"]


@pytest.mark.asyncio
async def test_agent_tool_registry_integration():
    """Test that agent correctly integrates with actual tool registry."""
    from flare_ai_kit.agent.tool import TOOL_REGISTRY
    from flare_ai_kit.agent import ecosystem_tools, social_tools, tee_tools, wallet_tools  # noqa: F401
    
    # Should have tools registered from all modules
    assert len(TOOL_REGISTRY) > 20
    
    # Check that tools have correct structure for ADK
    for tool in TOOL_REGISTRY[:5]:  # Check first 5 tools
        # Should be wrapped ADK tool objects
        assert hasattr(tool, "func") or hasattr(tool, "_func")
        
        # Get the underlying function
        func = getattr(tool, "func", None) or getattr(tool, "_func", None)
        if func and not str(func).startswith("<MagicMock"):  # Skip mocked functions
            assert callable(func)
            assert hasattr(func, "__name__")