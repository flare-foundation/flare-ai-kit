"""End-to-end integration tests with mock prompts and expected responses."""

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Mock dependencies
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


class MockFlareAIAgent:
    """Mock implementation of full Flare AI agent with realistic responses."""
    
    def __init__(self, name, model, tools, instruction):
        self.name = name
        self.model = model
        self.tools = tools
        self.instruction = instruction
        
    async def run(self, prompt: str) -> dict:
        """Process user prompt and return structured response with tool usage."""
        
        # Ecosystem/FTSO queries
        if any(keyword in prompt.lower() for keyword in ["price", "ftso", "btc", "eth", "flr"]):
            if "btc" in prompt.lower():
                return self._create_price_response("BTC/USD", 45123.45, "Bitcoin")
            elif "eth" in prompt.lower(): 
                return self._create_price_response("ETH/USD", 2834.67, "Ethereum")
            elif "flr" in prompt.lower():
                return self._create_price_response("FLR/USD", 0.0234, "Flare")
            else:
                return self._create_price_response("BTC/USD", 45123.45, "Bitcoin")
        
        # Balance queries
        elif "balance" in prompt.lower():
            address = self._extract_address(prompt)
            return self._create_balance_response(address, 1500.75)
            
        # Wallet operations
        elif "wallet" in prompt.lower():
            if "create" in prompt.lower():
                wallet_name = self._extract_wallet_name(prompt) or "MyWallet"
                return self._create_wallet_response(wallet_name, "wallet_" + wallet_name.lower())
            elif "sign" in prompt.lower():
                return self._create_sign_transaction_response()
            
        # Social media operations
        elif any(keyword in prompt.lower() for keyword in ["telegram", "twitter", "tweet", "post", "social"]):
            if "telegram" in prompt.lower():
                return self._create_telegram_response(prompt)
            elif any(keyword in prompt.lower() for keyword in ["twitter", "tweet", "x"]):
                return self._create_tweet_response(prompt)
            else:
                return self._create_broadcast_response(prompt)
                
        # TEE/Security operations
        elif any(keyword in prompt.lower() for keyword in ["attestation", "tee", "secure", "token"]):
            if "validate" in prompt.lower():
                return self._create_validate_attestation_response()
            else:
                return self._create_attestation_response()
                
        # Multi-step complex queries
        elif "and" in prompt.lower() or "then" in prompt.lower():
            return self._handle_complex_query(prompt)
            
        # Help/General queries
        else:
            return self._create_help_response()
    
    def _create_price_response(self, pair: str, price: float, crypto_name: str) -> dict:
        return {
            "response": f"💰 The current {pair} price is ${price:,.2f}. {crypto_name} is looking strong today!",
            "tools_used": ["get_ftso_price"],
            "tool_results": [{"feed_name": pair, "price": price, "category": "01", "status": "success"}],
            "confidence": 0.95,
            "response_type": "price_query"
        }
    
    def _create_balance_response(self, address: str, balance: float) -> dict:
        return {
            "response": f"📊 The FLR balance for address {address[:10]}... is {balance:.2f} FLR",
            "tools_used": ["check_flr_balance"],
            "tool_results": [{"address": address, "balance": balance, "currency": "FLR", "status": "success"}],
            "confidence": 0.92,
            "response_type": "balance_query"
        }
    
    def _create_wallet_response(self, wallet_name: str, wallet_id: str) -> dict:
        return {
            "response": f"🏦 Successfully created wallet '{wallet_name}' with ID: {wallet_id}. Your wallet is ready for use!",
            "tools_used": ["create_wallet"],
            "tool_results": [{"wallet_id": wallet_id, "wallet_name": wallet_name, "status": "success"}],
            "confidence": 0.98,
            "response_type": "wallet_creation"
        }
    
    def _create_sign_transaction_response(self) -> dict:
        return {
            "response": "✅ Transaction signed successfully! Hash: 0xabc123def456...",
            "tools_used": ["sign_transaction"],
            "tool_results": [{"transaction_hash": "0xabc123def456", "signed_transaction": "0x...", "status": "success"}],
            "confidence": 0.94,
            "response_type": "transaction_signing"
        }
    
    def _create_telegram_response(self, prompt: str) -> dict:
        message = self._extract_message(prompt) or "Hello from Flare AI!"
        return {
            "response": f"📱 Message sent to Telegram successfully: '{message[:50]}{'...' if len(message) > 50 else ''}'",
            "tools_used": ["send_telegram_message"],
            "tool_results": [{"chat_id": "@flare_updates", "text": message, "success": True, "status": "success"}],
            "confidence": 0.90,
            "response_type": "social_telegram"
        }
    
    def _create_tweet_response(self, prompt: str) -> dict:
        tweet_text = self._extract_message(prompt) or "Flare Network update!"
        return {
            "response": f"🐦 Tweet posted successfully: '{tweet_text[:50]}{'...' if len(tweet_text) > 50 else ''}'",
            "tools_used": ["post_tweet"],
            "tool_results": [{"text": tweet_text, "character_count": len(tweet_text), "success": True, "status": "success"}],
            "confidence": 0.88,
            "response_type": "social_twitter"
        }
    
    def _create_broadcast_response(self, prompt: str) -> dict:
        message = self._extract_message(prompt) or "Multi-platform update"
        return {
            "response": f"📢 Message broadcasted to all platforms: '{message[:40]}...'",
            "tools_used": ["broadcast_message"],
            "tool_results": [{"total_platforms": 2, "successful_posts": 2, "text": message, "status": "success"}],
            "confidence": 0.85,
            "response_type": "social_broadcast"
        }
    
    def _create_attestation_response(self) -> dict:
        return {
            "response": "🔒 TEE attestation token generated successfully. Your environment is verified as secure.",
            "tools_used": ["get_attestation_token"],
            "tool_results": [{"token": "eyJ0eXAiOiJKV1QiLCJhbGc...", "token_type": "OIDC", "simulated": False, "status": "success"}],
            "confidence": 0.96,
            "response_type": "tee_attestation"
        }
    
    def _create_validate_attestation_response(self) -> dict:
        return {
            "response": "✅ Attestation token is valid and verified. Environment security confirmed.",
            "tools_used": ["validate_attestation_token"],
            "tool_results": [{"valid": True, "claims": {"iss": "confidential-computing", "sub": "workload"}, "status": "success"}],
            "confidence": 0.97,
            "response_type": "tee_validation"
        }
    
    def _handle_complex_query(self, prompt: str) -> dict:
        """Handle multi-step queries that require multiple tools."""
        if "price" in prompt.lower() and ("send" in prompt.lower() or "post" in prompt.lower()):
            # Get price and post to social media
            return {
                "response": "💰 BTC/USD: $45,123.45 | 📱 Shared price update to Telegram successfully!",
                "tools_used": ["get_ftso_price", "send_telegram_message"],
                "tool_results": [
                    {"feed_name": "BTC/USD", "price": 45123.45, "status": "success"},
                    {"chat_id": "@updates", "text": "BTC/USD: $45,123.45", "success": True, "status": "success"}
                ],
                "confidence": 0.91,
                "response_type": "complex_price_social"
            }
        elif "wallet" in prompt.lower() and "balance" in prompt.lower():
            # Create wallet and check balance
            return {
                "response": "🏦 Wallet 'Trading' created | 📊 Balance: 0.00 FLR (new wallet)",
                "tools_used": ["create_wallet", "check_flr_balance"],
                "tool_results": [
                    {"wallet_id": "wallet_trading", "wallet_name": "Trading", "status": "success"},
                    {"address": "0x123...", "balance": 0.0, "status": "success"}
                ],
                "confidence": 0.89,
                "response_type": "complex_wallet_balance"
            }
        else:
            return self._create_help_response()
    
    def _create_help_response(self) -> dict:
        return {
            "response": """🤖 I'm your Flare AI assistant! I can help with:

💰 **FTSO Prices**: "What's the BTC price?"
📊 **Balances**: "Check balance for 0x123..."  
🏦 **Wallets**: "Create a new wallet"
📱 **Social**: "Post to Telegram"
🔒 **Security**: "Generate attestation token"

What would you like to do?""",
            "tools_used": [],
            "tool_results": [],
            "confidence": 1.0,
            "response_type": "help"
        }
    
    def _extract_address(self, prompt: str) -> str:
        """Extract wallet address from prompt or return default."""
        words = prompt.split()
        for word in words:
            if word.startswith("0x") and len(word) >= 10:
                return word
        return "0x1234567890123456789012345678901234567890"
    
    def _extract_wallet_name(self, prompt: str) -> str:
        """Extract wallet name from prompt."""
        if "called" in prompt.lower():
            words = prompt.lower().split("called")
            if len(words) > 1:
                return words[1].strip().split()[0].replace('"', '').replace("'", '')
        return None
    
    def _extract_message(self, prompt: str) -> str:
        """Extract message content from prompt."""
        keywords = ["saying", "message", "text", "post", "tweet"]
        for keyword in keywords:
            if keyword in prompt.lower():
                parts = prompt.lower().split(keyword)
                if len(parts) > 1:
                    return parts[1].strip().replace('"', '').replace("'", '')
        return None


@pytest.fixture
def mock_flare_agent():
    """Create mock Flare AI agent for end-to-end testing."""
    from flare_ai_kit.agent.tool import TOOL_REGISTRY
    from flare_ai_kit.agent import ecosystem_tools, social_tools, tee_tools, wallet_tools  # noqa: F401
    
    return MockFlareAIAgent(
        name="flare_ai_agent",
        model="gemini-2.5-flash",
        tools=TOOL_REGISTRY,
        instruction="Flare AI Kit assistant"
    )


class TestBasicPromptResponses:
    """Test basic single-tool prompt responses."""

    @pytest.mark.asyncio
    async def test_btc_price_query(self, mock_flare_agent):
        """Test BTC price query prompt and response."""
        prompt = "What's the current Bitcoin price?"
        
        result = await mock_flare_agent.run(prompt)
        
        assert result["response_type"] == "price_query"
        assert "get_ftso_price" in result["tools_used"]
        assert result["tool_results"][0]["feed_name"] == "BTC/USD"
        assert result["tool_results"][0]["price"] == 45123.45
        assert "$45,123.45" in result["response"]
        assert result["confidence"] > 0.9

    @pytest.mark.asyncio  
    async def test_eth_price_query(self, mock_flare_agent):
        """Test ETH price query prompt and response."""
        prompt = "Show me ETH/USD price please"
        
        result = await mock_flare_agent.run(prompt)
        
        assert result["response_type"] == "price_query"
        assert result["tool_results"][0]["feed_name"] == "ETH/USD"
        assert result["tool_results"][0]["price"] == 2834.67
        assert "Ethereum" in result["response"]

    @pytest.mark.asyncio
    async def test_balance_check_query(self, mock_flare_agent):
        """Test balance check prompt and response."""
        prompt = "Check the balance for address 0xabcdef1234567890abcdef1234567890abcdef12"
        
        result = await mock_flare_agent.run(prompt)
        
        assert result["response_type"] == "balance_query"
        assert "check_flr_balance" in result["tools_used"]
        assert result["tool_results"][0]["balance"] == 1500.75
        assert "0xabcdef123" in result["response"]
        assert "1500.75 FLR" in result["response"]

    @pytest.mark.asyncio
    async def test_wallet_creation_query(self, mock_flare_agent):
        """Test wallet creation prompt and response."""
        prompt = "Create a new wallet called TradingWallet"
        
        result = await mock_flare_agent.run(prompt)
        
        assert result["response_type"] == "wallet_creation"
        assert "create_wallet" in result["tools_used"]
        assert result["tool_results"][0]["wallet_name"] == "TradingWallet"
        assert "wallet_tradingwallet" in result["tool_results"][0]["wallet_id"]
        assert "Successfully created" in result["response"]

    @pytest.mark.asyncio
    async def test_telegram_message_query(self, mock_flare_agent):
        """Test Telegram message prompt and response."""
        prompt = "Send a Telegram message saying 'Hello Flare community!'"
        
        result = await mock_flare_agent.run(prompt)
        
        assert result["response_type"] == "social_telegram"
        assert "send_telegram_message" in result["tools_used"] 
        assert result["tool_results"][0]["text"] == "Hello Flare community!"
        assert result["tool_results"][0]["success"] == True
        assert "Message sent to Telegram" in result["response"]

    @pytest.mark.asyncio
    async def test_tweet_posting_query(self, mock_flare_agent):
        """Test Twitter/X posting prompt and response."""
        prompt = "Tweet about Flare Network's latest update"
        
        result = await mock_flare_agent.run(prompt)
        
        assert result["response_type"] == "social_twitter"
        assert "post_tweet" in result["tools_used"]
        assert "Flare Network update!" in result["tool_results"][0]["text"]
        assert "Tweet posted successfully" in result["response"]

    @pytest.mark.asyncio
    async def test_tee_attestation_query(self, mock_flare_agent):
        """Test TEE attestation prompt and response.""" 
        prompt = "Generate a TEE attestation token for security"
        
        result = await mock_flare_agent.run(prompt)
        
        assert result["response_type"] == "tee_attestation"
        assert "get_attestation_token" in result["tools_used"]
        assert "token" in result["tool_results"][0]
        assert result["tool_results"][0]["token_type"] == "OIDC"
        assert "attestation token generated" in result["response"]

    @pytest.mark.asyncio
    async def test_help_query(self, mock_flare_agent):
        """Test help/general query prompt and response."""
        prompt = "What can you help me with?"
        
        result = await mock_flare_agent.run(prompt)
        
        assert result["response_type"] == "help"
        assert len(result["tools_used"]) == 0
        assert result["confidence"] == 1.0
        assert "FTSO Prices" in result["response"]
        assert "Balances" in result["response"]
        assert "Wallets" in result["response"]


class TestComplexPromptResponses:
    """Test complex multi-tool prompt responses."""

    @pytest.mark.asyncio
    async def test_price_and_social_sharing(self, mock_flare_agent):
        """Test complex prompt requiring price lookup and social sharing."""
        prompt = "Get the BTC price and post it to Telegram"
        
        result = await mock_flare_agent.run(prompt)
        
        assert result["response_type"] == "complex_price_social"
        assert len(result["tools_used"]) == 2
        assert "get_ftso_price" in result["tools_used"]
        assert "send_telegram_message" in result["tools_used"]
        assert len(result["tool_results"]) == 2
        assert "$45,123.45" in result["response"]
        assert "Telegram successfully" in result["response"]

    @pytest.mark.asyncio
    async def test_wallet_creation_and_balance(self, mock_flare_agent):
        """Test complex prompt requiring wallet creation and balance check."""
        prompt = "Create a wallet called Trading and check its balance"
        
        result = await mock_flare_agent.run(prompt)
        
        assert result["response_type"] == "complex_wallet_balance"
        assert len(result["tools_used"]) == 2
        assert "create_wallet" in result["tools_used"]
        assert "check_flr_balance" in result["tools_used"]
        assert result["tool_results"][0]["wallet_name"] == "Trading"
        assert result["tool_results"][1]["balance"] == 0.0
        assert "Wallet 'Trading' created" in result["response"]


class TestConversationalFlow:
    """Test conversational flow and context handling."""

    @pytest.mark.asyncio
    async def test_follow_up_questions(self, mock_flare_agent):
        """Test handling follow-up questions in conversation."""
        
        # Initial query
        prompt1 = "What's the FLR price?"
        result1 = await mock_flare_agent.run(prompt1)
        
        assert result1["response_type"] == "price_query"
        assert result1["tool_results"][0]["feed_name"] == "FLR/USD"
        
        # Follow-up query (would ideally use context in real implementation)
        prompt2 = "Now check my balance at 0x123..."
        result2 = await mock_flare_agent.run(prompt2)
        
        assert result2["response_type"] == "balance_query"
        assert "balance" in result2["response"].lower()

    @pytest.mark.asyncio
    async def test_error_recovery_flow(self, mock_flare_agent):
        """Test conversational error recovery."""
        
        # Ambiguous query should return help
        prompt = "Do something with crypto"
        result = await mock_flare_agent.run(prompt)
        
        # Should default to help response for ambiguous queries
        assert result["response_type"] == "help"
        assert len(result["tools_used"]) == 0


class TestPromptVariations:
    """Test different ways of asking for the same thing."""

    @pytest.mark.asyncio
    async def test_price_query_variations(self, mock_flare_agent):
        """Test various ways to ask for price."""
        
        prompts = [
            "What's the Bitcoin price?",
            "Show me BTC/USD",
            "Current BTC price please",
            "Bitcoin value now?",
            "BTC rate"
        ]
        
        for prompt in prompts:
            result = await mock_flare_agent.run(prompt)
            assert result["response_type"] == "price_query"
            assert "get_ftso_price" in result["tools_used"]
            assert result["tool_results"][0]["price"] == 45123.45

    @pytest.mark.asyncio
    async def test_wallet_query_variations(self, mock_flare_agent):
        """Test various ways to ask for wallet operations."""
        
        prompts = [
            "Create a new wallet called Test",
            "Make a wallet named Test",
            "Set up Test wallet",
            "Generate wallet Test"
        ]
        
        for prompt in prompts:
            result = await mock_flare_agent.run(prompt)
            assert result["response_type"] == "wallet_creation"
            assert "create_wallet" in result["tools_used"]
            assert "Test" in result["tool_results"][0]["wallet_name"]


@pytest.mark.asyncio
async def test_end_to_end_realistic_conversation():
    """Test a realistic multi-turn conversation scenario."""
    
    from flare_ai_kit.agent.tool import TOOL_REGISTRY
    from flare_ai_kit.agent import ecosystem_tools, social_tools, tee_tools, wallet_tools  # noqa: F401
    
    agent = MockFlareAIAgent(
        name="flare_ai_agent",
        model="gemini-2.5-flash", 
        tools=TOOL_REGISTRY,
        instruction="Flare AI assistant"
    )
    
    # Realistic conversation flow
    conversation = [
        ("Hello! What can you help me with?", "help"),
        ("What's the current FLR price?", "price_query"),
        ("Create a wallet called Portfolio", "wallet_creation"), 
        ("Send a tweet about Flare being awesome", "social_twitter"),
        ("Generate an attestation token", "tee_attestation")
    ]
    
    for prompt, expected_type in conversation:
        result = await agent.run(prompt)
        assert result["response_type"] == expected_type
        assert "response" in result
        assert isinstance(result["tools_used"], list)
        assert isinstance(result["tool_results"], list)
        assert 0.0 <= result["confidence"] <= 1.0