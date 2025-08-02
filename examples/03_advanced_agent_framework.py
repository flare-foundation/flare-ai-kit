"""Advanced example showing how to create custom agents extending the base framework."""

import asyncio
from typing import Dict, Any, List
from datetime import datetime

from flare_ai_kit.agent import BaseAgent, GeminiAgent, AgentResponse, AgentSettings
from flare_ai_kit.agent.base import ConversationMessage


class FlareBlockchainAgent(GeminiAgent):
    """Specialized agent for Flare blockchain queries and interactions.
    
    This agent extends GeminiAgent with blockchain-specific knowledge and capabilities.
    """
    
    def __init__(self, *args, **kwargs):
        # Set a blockchain-focused system prompt
        system_prompt = """You are a specialized AI assistant for the Flare blockchain ecosystem. 
        You have deep knowledge about:
        - Flare Network and its protocols (FTSO, FAssets, State Connector)
        - Blockchain technology and DeFi concepts
        - Smart contract development
        - Cross-chain interactions
        
        Always provide accurate, technical information and suggest practical solutions."""
        
        # Override system_prompt in kwargs if not provided
        kwargs.setdefault('system_prompt', system_prompt)
        
        super().__init__(*args, **kwargs)
        
        # Add blockchain-specific custom data
        self.add_custom_data("specialization", "flare_blockchain")
        self.add_custom_data("supported_networks", ["flare", "songbird", "coston", "coston2"])
        
    async def _setup(self):
        """Extended setup for blockchain agent."""
        await super()._setup()
        
        # Initialize blockchain-specific resources
        self.logger.info("Setting up blockchain-specific capabilities")
        
        # Add blockchain context to the agent
        blockchain_context = {
            "ftso_info": "Flare Time Series Oracle provides decentralized price feeds",
            "fassets_info": "FAssets enable bringing non-smart contract tokens to Flare",
            "state_connector_info": "State Connector enables trustless cross-chain data access"
        }
        
        for key, value in blockchain_context.items():
            self.add_custom_data(key, value)
    
    async def analyze_blockchain_data(self, data_type: str, query: str) -> AgentResponse:
        """Analyze blockchain data with specialized prompts.
        
        Args:
            data_type: Type of blockchain data (price, transaction, contract, etc.)
            query: Specific query about the data
            
        Returns:
            Specialized analysis response
        """
        specialized_prompt = f"""
        As a Flare blockchain expert, analyze the following {data_type} data:
        
        Query: {query}
        
        Please provide:
        1. Technical analysis
        2. Relevant Flare ecosystem context
        3. Practical implications
        4. Recommended actions if applicable
        """
        
        return await self.process_input(
            specialized_prompt,
            include_history=False,  # Don't include general conversation
            response_metadata={"analysis_type": data_type, "specialized": True}
        )
    
    async def explain_flare_concept(self, concept: str) -> AgentResponse:
        """Explain Flare-specific concepts in detail.
        
        Args:
            concept: Flare concept to explain (e.g., "FTSO", "FAssets", "State Connector")
            
        Returns:
            Detailed explanation response
        """
        explanation_prompt = f"""
        Please provide a comprehensive explanation of the Flare concept: {concept}
        
        Include:
        - What it is and how it works
        - Technical implementation details
        - Use cases and benefits
        - Code examples if applicable
        - Integration possibilities
        """
        
        return await self.process_input(
            explanation_prompt,
            response_metadata={"concept": concept, "explanation_type": "flare_concept"}
        )


class CodeReviewAgent(GeminiAgent):
    """Specialized agent for code review and analysis."""
    
    def __init__(self, *args, **kwargs):
        system_prompt = """You are an expert code reviewer with deep knowledge of:
        - Best practices across multiple programming languages
        - Security vulnerabilities and how to prevent them
        - Performance optimization techniques
        - Code maintainability and readability
        - Testing strategies
        
        Always provide constructive, actionable feedback with specific suggestions for improvement."""
        
        # Set defaults
        kwargs.setdefault('system_prompt', system_prompt)
        kwargs.setdefault('temperature', 0.3)  # Lower temperature for more consistent analysis
        
        super().__init__(*args, **kwargs)
        
        self.add_custom_data("specialization", "code_review")
        self.add_custom_data("review_criteria", [
            "correctness", "security", "performance", 
            "maintainability", "readability", "testing"
        ])
    
    async def review_code(
        self,
        code: str,
        language: str,
        context: str = "",
        focus_areas: List[str] | None = None
    ) -> AgentResponse:
        """Perform a comprehensive code review.
        
        Args:
            code: The code to review
            language: Programming language
            context: Additional context about the code's purpose
            focus_areas: Specific areas to focus on during review
            
        Returns:
            Detailed code review response
        """
        focus_areas = focus_areas or ["security", "performance", "maintainability"]
        
        review_prompt = f"""
        Please perform a comprehensive code review for the following {language} code:
        
        Context: {context}
        
        Focus areas: {', '.join(focus_areas)}
        
        Code:
        ```{language}
        {code}
        ```
        
        Please provide:
        1. Overall assessment
        2. Specific issues found (with line references if possible)
        3. Security concerns
        4. Performance considerations
        5. Suggestions for improvement
        6. Best practices recommendations
        """
        
        return await self.process_input(
            review_prompt,
            response_metadata={
                "review_type": "code_review",
                "language": language,
                "focus_areas": focus_areas
            }
        )
    
    async def suggest_tests(self, code: str, language: str) -> AgentResponse:
        """Suggest test cases for the given code.
        
        Args:
            code: The code to create tests for
            language: Programming language
            
        Returns:
            Test suggestions response
        """
        test_prompt = f"""
        Analyze the following {language} code and suggest comprehensive test cases:
        
        ```{language}
        {code}
        ```
        
        Please provide:
        1. Unit test cases (positive scenarios)
        2. Edge case tests
        3. Error handling tests
        4. Integration test suggestions
        5. Sample test code implementation
        """
        
        return await self.process_input(
            test_prompt,
            response_metadata={"review_type": "test_suggestions", "language": language}
        )


async def demonstrate_specialized_agents():
    """Demonstrate the usage of specialized agents."""
    
    settings = AgentSettings()
    
    print("🚀 Specialized Agents Demo")
    print("=" * 50)
    
    # Create specialized agents
    flare_agent = FlareBlockchainAgent(
        agent_id="flare-expert-001",
        agent_name="Flare Blockchain Expert",
        settings=settings
    )
    
    code_agent = CodeReviewAgent(
        agent_id="code-reviewer-001", 
        agent_name="Code Review Expert",
        settings=settings
    )
    
    try:
        # Initialize agents
        print("\n📋 Initializing specialized agents...")
        await flare_agent.initialize()
        await code_agent.initialize()
        print("✅ All agents initialized!")
        
        # Demonstrate Flare Blockchain Agent
        print("\n🔗 Flare Blockchain Agent Demo")
        print("-" * 30)
        
        # Explain a Flare concept
        ftso_explanation = await flare_agent.explain_flare_concept("FTSO")
        print(f"📚 FTSO Explanation:\n{ftso_explanation.content[:200]}...\n")
        
        # Analyze blockchain data
        price_analysis = await flare_agent.analyze_blockchain_data(
            "price",
            "Analyze the potential impact of FTSO price feeds on DeFi protocols"
        )
        print(f"📊 Price Analysis:\n{price_analysis.content[:200]}...\n")
        
        # Demonstrate Code Review Agent
        print("\n🔍 Code Review Agent Demo")
        print("-" * 30)
        
        sample_code = """
def transfer_tokens(from_address, to_address, amount):
    if amount > 0:
        balance = get_balance(from_address)
        if balance >= amount:
            update_balance(from_address, balance - amount)
            update_balance(to_address, get_balance(to_address) + amount)
            return True
    return False
"""
        
        # Perform code review
        review_result = await code_agent.review_code(
            code=sample_code,
            language="python",
            context="Simple token transfer function for a blockchain application",
            focus_areas=["security", "error_handling"]
        )
        print(f"🔍 Code Review:\n{review_result.content[:300]}...\n")
        
        # Suggest tests
        test_suggestions = await code_agent.suggest_tests(sample_code, "python")
        print(f"🧪 Test Suggestions:\n{test_suggestions.content[:300]}...\n")
        
        # Demonstrate agent interaction (agents talking to each other)
        print("\n🤝 Agent Collaboration Demo")
        print("-" * 30)
        
        # Flare agent provides blockchain context
        blockchain_context = await flare_agent.process_input(
            "Provide a brief overview of security considerations when building on Flare"
        )
        
        # Code agent uses that context for specialized review
        security_review = await code_agent.process_input(
            f"Based on this Flare security context: '{blockchain_context.content[:100]}...', "
            f"review this smart contract function for Flare-specific security issues: {sample_code}"
        )
        
        print(f"🔒 Flare-specific Security Review:\n{security_review.content[:300]}...\n")
        
        # Show agent statistics
        print("\n📊 Agent Statistics")
        print("-" * 20)
        
        for agent, name in [(flare_agent, "Flare Expert"), (code_agent, "Code Reviewer")]:
            history_count = len(agent.get_conversation_history())
            specialization = agent.get_custom_data("specialization")
            print(f"{name}:")
            print(f"  Messages: {history_count}")
            print(f"  Specialization: {specialization}")
            print(f"  Model: {agent.model_info['model_name']}")
            print(f"  Temperature: {agent.model_info['temperature']}")
            print()
        
    except Exception as e:
        print(f"❌ Error during demo: {e}")
        import traceback
        traceback.print_exc()


async def demonstrate_agent_persistence():
    """Demonstrate conversation history persistence and context management."""
    
    print("\n💾 Agent Persistence Demo")
    print("=" * 30)
    
    settings = AgentSettings()
    
    # Create agent with conversation history
    agent = GeminiAgent(
        agent_id="persistent-agent-001",
        agent_name="Persistent Agent",
        settings=settings,
        max_history_length=5  # Small history for demo
    )
    
    await agent.initialize()
    
    # Simulate a conversation
    conversation_topics = [
        "Hello, I'm working on a Python project",
        "It's a web scraper for blockchain data",
        "I need help with error handling",
        "How do I handle rate limiting?",
        "What about data validation?",
        "Should I use async/await?",
        "What testing framework do you recommend?"
    ]
    
    print("🗣️ Simulating conversation...")
    for i, topic in enumerate(conversation_topics, 1):
        response = await agent.process_input(topic)
        print(f"{i}. User: {topic}")
        print(f"   Agent: {response.content[:80]}...")
        
        # Show how history is managed
        if i % 3 == 0:
            history = agent.get_conversation_history()
            print(f"   📚 History length: {len(history)} (max: {agent.context.max_history_length})")
    
    # Show final conversation state
    print(f"\n📋 Final Conversation State:")
    print(f"   Total interactions: {len(conversation_topics)}")
    print(f"   Stored messages: {len(agent.get_conversation_history())}")
    print(f"   Agent remembers: {agent.context.max_history_length} most recent messages")
    
    # Demonstrate context extraction
    print("\n🧠 Context Analysis:")
    user_messages = agent.get_conversation_history(role_filter="user")
    assistant_messages = agent.get_conversation_history(role_filter="assistant")
    
    print(f"   User messages: {len(user_messages)}")
    print(f"   Assistant messages: {len(assistant_messages)}")
    
    # Show the agent can still reference recent context
    context_test = await agent.process_input("What was the main topic we were discussing?")
    print(f"   Context awareness test: {context_test.content[:100]}...")


if __name__ == "__main__":
    import os
    
    # Check if API key is set
    if not os.getenv("AGENT__GEMINI_API_KEY"):
        print("❌ Please set the AGENT__GEMINI_API_KEY environment variable")
        exit(1)
    
    async def main():
        await demonstrate_specialized_agents()
        await demonstrate_agent_persistence()
        
        print("\n✨ Advanced agent framework demo completed!")
    
    asyncio.run(main())
