"""Example demonstrating the Gemini Agent usage."""

import asyncio
import os
from flare_ai_kit.agent import GeminiAgent, AgentSettings


async def main():
    """Demonstrate basic agent usage."""
    
    # Setup settings (make sure to set AGENT__GEMINI_API_KEY environment variable)
    settings = AgentSettings()
    
    # Create a Gemini agent
    agent = GeminiAgent(
        agent_id="example-agent-001",
        agent_name="Example Assistant",
        system_prompt="You are a helpful AI assistant that provides clear and concise answers.",
        max_history_length=20,
        temperature=0.7,
        settings=settings
    )
    
    try:
        # Initialize the agent
        print("Initializing agent...")
        await agent.initialize()
        print(f"✅ Agent '{agent.agent_name}' initialized successfully!")
        
        # Test connection
        print("\nTesting connection...")
        connection_result = await agent.test_connection()
        if connection_result["status"] == "success":
            print("✅ Connection test passed!")
        else:
            print(f"❌ Connection test failed: {connection_result['error']}")
            return
        
        # Print agent info
        print(f"\n📋 Agent Info:")
        print(f"   ID: {agent.agent_id}")
        print(f"   Name: {agent.agent_name}")
        print(f"   Model: {agent.model_info['model_name']}")
        print(f"   Temperature: {agent.model_info['temperature']}")
        
        # Example conversation
        print("\n💬 Starting conversation...")
        
        # First interaction
        print("\nUser: Hello! What can you help me with?")
        response1 = await agent.process_input("Hello! What can you help me with?")
        print(f"Assistant: {response1.content}")
        
        if response1.usage_info:
            print(f"   (Tokens used: {response1.usage_info.get('total_tokens', 'N/A')})")
        
        # Second interaction (with conversation history)
        print("\nUser: Can you help me write a Python function?")
        response2 = await agent.process_input("Can you help me write a Python function?")
        print(f"Assistant: {response2.content}")
        
        # Third interaction
        print("\nUser: I need a function that calculates the factorial of a number.")
        response3 = await agent.process_input("I need a function that calculates the factorial of a number.")
        print(f"Assistant: {response3.content}")
        
        # Show conversation history
        print(f"\n📚 Conversation History ({len(agent.get_conversation_history())} messages):")
        for i, msg in enumerate(agent.get_conversation_history(), 1):
            role_emoji = "👤" if msg.role == "user" else "🤖"
            print(f"   {i}. {role_emoji} {msg.role.title()}: {msg.content[:50]}...")
        
        # Demonstrate custom data
        agent.add_custom_data("session_start", "2024-01-01")
        agent.add_custom_data("user_preferences", {"language": "Python", "style": "functional"})
        
        print(f"\n🔧 Custom Data:")
        print(f"   Session Start: {agent.get_custom_data('session_start')}")
        print(f"   User Preferences: {agent.get_custom_data('user_preferences')}")
        
        # Demonstrate embedding generation
        print("\n🔗 Generating embeddings for a sample text...")
        try:
            embeddings = await agent.generate_embedding("This is a sample text for embedding generation.")
            print(f"   Embedding dimension: {len(embeddings)}")
            print(f"   First 5 values: {embeddings[:5]}")
        except Exception as e:
            print(f"   ⚠️ Embedding generation failed: {e}")
        
        # Demonstrate streaming (commented out as it requires async iteration)
        print("\n🌊 Streaming response example:")
        print("User: Tell me a short story about AI.")
        print("Assistant: ", end="", flush=True)
        
        try:
            full_response = ""
            async for chunk in agent.stream_response("Tell me a short story about AI."):
                if hasattr(chunk, 'data'):
                    chunk_text = chunk.data
                else:
                    chunk_text = str(chunk)
                print(chunk_text, end="", flush=True)
                full_response += chunk_text
            print()  # New line after streaming
            
            # Add the streamed response to history manually
            from flare_ai_kit.agent.base import ConversationMessage
            agent._add_to_history(ConversationMessage(role="user", content="Tell me a short story about AI."))
            agent._add_to_history(ConversationMessage(role="assistant", content=full_response))
            
        except Exception as e:
            print(f"\n   ⚠️ Streaming failed: {e}")
        
        # Update system prompt
        print("\n🔄 Updating system prompt...")
        agent.set_system_prompt("You are now a creative writing assistant specializing in science fiction.")
        print("   System prompt updated!")
        
        # Test with new system prompt
        print("\nUser: Write a haiku about space exploration.")
        response4 = await agent.process_input("Write a haiku about space exploration.")
        print(f"Assistant: {response4.content}")
        
        # Update model parameters
        print("\n⚙️ Updating model parameters...")
        agent.update_model_parameters(temperature=0.9, max_tokens=150)
        print(f"   Temperature: {agent.temperature}")
        print(f"   Max tokens: {agent.max_tokens}")
        
        # Final interaction with updated parameters
        print("\nUser: Be more creative now!")
        response5 = await agent.process_input("Be more creative now!")
        print(f"Assistant: {response5.content}")
        
        print(f"\n✨ Final conversation history: {len(agent.get_conversation_history())} messages")
        
    except Exception as e:
        print(f"❌ Error during agent usage: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Check if API key is set
    if not os.getenv("AGENT__GEMINI_API_KEY"):
        print("❌ Please set the AGENT__GEMINI_API_KEY environment variable")
        print("   You can get an API key from: https://aistudio.google.com/app/apikey")
        print("\n   Example:")
        print("   export AGENT__GEMINI_API_KEY='your-api-key-here'")
        exit(1)
    
    print("🚀 Flare AI Kit - Gemini Agent Example")
    print("=" * 50)
    
    asyncio.run(main())
