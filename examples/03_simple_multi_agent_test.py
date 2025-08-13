#!/usr/bin/env python3
"""
Simple Multi-Agent Communication Test

A minimal example to test basic agent-to-agent communication using the Flare AI Kit.
"""

import asyncio
import os
import sys

# Add the src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from flare_ai_kit.agent.gemini_agent import GeminiAgent
from flare_ai_kit.agent.settings import AgentSettings


async def simple_multi_agent_test():
    """Test basic communication between two agents."""
    print("🤖 Simple Multi-Agent Communication Test")
    print("=" * 50)

    # Create settings
    settings = AgentSettings()

    # Create two agents with different personalities
    agent1 = GeminiAgent(
        agent_id="alice",
        agent_name="Alice",
        system_prompt="You are Alice, a curious and analytical AI assistant. You ask thoughtful questions and provide detailed analysis.",
        settings=settings,
        temperature=0.7,
    )

    agent2 = GeminiAgent(
        agent_id="bob",
        agent_name="Bob",
        system_prompt="You are Bob, a creative and enthusiastic AI assistant. You think outside the box and propose innovative solutions.",
        settings=settings,
        temperature=0.8,
    )

    # Initialize both agents
    await agent1.initialize()
    await agent2.initialize()

    print("✅ Agents initialized successfully")
    print()

    # Test basic communication
    print("💬 Testing basic communication:")
    print("-" * 30)

    # Alice starts the conversation
    alice_message = "Hello Bob! I'm working on understanding how AI agents can collaborate effectively. What are your thoughts on the key factors that make agent collaboration successful?"

    print(f"🤖 Alice: {alice_message}")
    print()

    # Bob responds
    bob_response = await agent2.process_input(
        user_input=f"Alice (another AI agent) says: {alice_message}",
        include_history=False,
    )

    print(f"🤖 Bob: {bob_response.content}")
    print()

    # Alice responds to Bob
    alice_followup = await agent1.process_input(
        user_input=f"Bob (another AI agent) responded: {bob_response.content}. Please provide your analytical perspective on Bob's points.",
        include_history=True,  # Include history for context
    )

    print(f"🤖 Alice (follow-up): {alice_followup.content}")
    print()

    # Test streaming between agents
    print("🌊 Testing streaming communication:")
    print("-" * 35)

    stream_prompt = f"Alice wants to collaborate on a creative project: {alice_followup.content}. Please respond with enthusiasm and creative ideas."

    print("🤖 Bob (streaming): ", end="")
    async for chunk in agent2.stream_response(stream_prompt):
        print(chunk, end="", flush=True)
    print("\n")

    # Test embeddings
    print("🧠 Testing embedding generation:")
    print("-" * 35)

    test_text = "Multi-agent collaboration in AI systems"
    alice_embedding = await agent1.generate_embedding(test_text)
    bob_embedding = await agent2.generate_embedding(test_text)

    print(f"Alice's embedding dimension: {len(alice_embedding)}")
    print(f"Bob's embedding dimension: {len(bob_embedding)}")
    print(f"Alice's first 5 values: {alice_embedding[:5]}")
    print(f"Bob's first 5 values: {bob_embedding[:5]}")

    # Test if embeddings are deterministic
    alice_embedding2 = await agent1.generate_embedding(test_text)
    print(
        f"Alice's embeddings are deterministic: {alice_embedding == alice_embedding2}"
    )

    print()
    print("✅ All tests completed successfully!")

    return {
        "alice_agent": agent1,
        "bob_agent": agent2,
        "conversation": [
            {"speaker": "Alice", "message": alice_message},
            {"speaker": "Bob", "message": bob_response.content},
            {"speaker": "Alice", "message": alice_followup.content},
        ],
    }


async def test_conversation_history():
    """Test conversation history management."""
    print("\n📚 Testing Conversation History Management")
    print("=" * 50)

    settings = AgentSettings()

    agent = GeminiAgent(
        agent_id="memory_test",
        agent_name="Memory Tester",
        system_prompt="You are a helpful assistant. Remember what users tell you and reference previous parts of the conversation when appropriate.",
        settings=settings,
        max_history_length=10,
    )

    await agent.initialize()

    # Build up a conversation
    messages = [
        "Hello, my name is Sarah and I'm a software engineer.",
        "I'm working on a Python project involving AI agents.",
        "Can you help me understand how conversation history works?",
        "What did I tell you my name was?",
        "What's my profession according to our conversation?",
    ]

    for i, message in enumerate(messages, 1):
        print(f"👤 User (message {i}): {message}")

        response = await agent.process_input(user_input=message, include_history=True)

        print(f"🤖 Agent: {response.content}")
        print(f"📜 History length: {len(agent.context.conversation_history)}")
        print()

    print("✅ Conversation history test completed!")


async def main():
    """Run all simple multi-agent tests."""
    try:
        # Test basic communication
        result = await simple_multi_agent_test()

        # Test conversation history
        await test_conversation_history()

        print("\n🎉 All multi-agent communication tests passed!")

    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
