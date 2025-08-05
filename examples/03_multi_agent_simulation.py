#!/usr/bin/env python3
"""
Multi-Agent Communication Simulation

This example demonstrates how multiple agents can communicate with each other,
share context, and collaborate on complex tasks using the Flare AI Kit agent framework.

We'll simulate a scenario where multiple specialized agents work together:
1. Research Agent - Gathers and analyzes information
2. Planning Agent - Creates strategies and plans
3. Execution Agent - Implements solutions
4. Review Agent - Evaluates and provides feedback
"""

import asyncio
import logging
import os
from typing import List, Dict, Any, Optional
from datetime import datetime

# Configure logging for better visibility
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Add the src directory to path for imports
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from flare_ai_kit.agent.gemini_agent import GeminiAgent
from flare_ai_kit.agent.base import ConversationMessage, AgentContext
from flare_ai_kit.agent.settings import AgentSettings


class MultiAgentOrchestrator:
    """Orchestrates communication between multiple agents."""
    
    def __init__(self, settings: AgentSettings):
        """Initialize the multi-agent orchestrator.
        
        Args:
            settings: Shared settings for all agents
        """
        self.settings = settings
        self.agents: Dict[str, GeminiAgent] = {}
        self.shared_context: Dict[str, Any] = {
            "conversation_log": [],
            "shared_data": {},
            "task_status": {}
        }
        
    async def create_agent(
        self,
        agent_id: str,
        agent_name: str,
        role_description: str,
        specialized_prompt: str = ""
    ) -> GeminiAgent:
        """Create and initialize a new agent.
        
        Args:
            agent_id: Unique identifier for the agent
            agent_name: Human-readable name
            role_description: Description of the agent's role
            specialized_prompt: Specialized system prompt for this agent
            
        Returns:
            Initialized GeminiAgent
        """
        system_prompt = f"""
You are {agent_name}, a specialized AI agent with the following role:
{role_description}

Your capabilities:
- Analyze information relevant to your specialization
- Communicate clearly with other agents
- Share findings and insights
- Collaborate effectively on multi-step tasks
- Maintain context across conversations

When communicating with other agents:
- Be concise but thorough
- Share relevant data and insights
- Ask clarifying questions when needed
- Build upon previous agent contributions
- Indicate when you need information from specific agents

{specialized_prompt}
"""
        
        agent = GeminiAgent(
            agent_id=agent_id,
            agent_name=agent_name,
            system_prompt=system_prompt,
            settings=self.settings,
            temperature=0.7
        )
        
        await agent.initialize()
        self.agents[agent_id] = agent
        
        print(f"✅ Created agent: {agent_name} (ID: {agent_id})")
        return agent
        
    async def send_message_between_agents(
        self,
        from_agent_id: str,
        to_agent_id: str,
        message: str,
        context_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """Send a message from one agent to another.
        
        Args:
            from_agent_id: ID of the sending agent
            to_agent_id: ID of the receiving agent
            message: The message content
            context_data: Additional context data to share
            
        Returns:
            The response from the receiving agent
        """
        if from_agent_id not in self.agents or to_agent_id not in self.agents:
            raise ValueError("Invalid agent IDs")
            
        from_agent = self.agents[from_agent_id]
        to_agent = self.agents[to_agent_id]
        
        # Add context about who is sending the message
        contextual_message = f"""
MESSAGE FROM: {from_agent.agent_name} (Agent ID: {from_agent_id})

{message}

--- Shared Context ---
Task Status: {self.shared_context.get('task_status', 'No active tasks')}
Shared Data: {self.shared_context.get('shared_data', 'No shared data')}
"""
        
        # Add any additional context data
        if context_data:
            contextual_message += f"\nAdditional Context: {context_data}"
            
        # Generate response from the receiving agent
        response = await to_agent.process_input(
            user_input=contextual_message,
            include_history=True
        )
        
        # Log the communication
        communication_log = {
            "timestamp": datetime.now().isoformat(),
            "from_agent": from_agent.agent_name,
            "to_agent": to_agent.agent_name,
            "message": message,
            "response": response.content,
            "context_data": context_data
        }
        
        self.shared_context["conversation_log"].append(communication_log)
        
        print(f"📨 {from_agent.agent_name} → {to_agent.agent_name}")
        print(f"   Message: {message}{'...' if len(message) > 100 else ''}")
        print(f"   Response: {response.content}{'...' if len(response.content) > 100 else ''}")
        print()
        
        return response.content
        
    async def broadcast_message(
        self,
        from_agent_id: str,
        message: str,
        context_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, str]:
        """Broadcast a message from one agent to all other agents.
        
        Args:
            from_agent_id: ID of the sending agent
            message: The message content
            context_data: Additional context data to share
            
        Returns:
            Dictionary mapping agent IDs to their responses
        """
        responses = {}
        
        for agent_id in self.agents:
            if agent_id != from_agent_id:
                response = await self.send_message_between_agents(
                    from_agent_id, agent_id, message, context_data
                )
                responses[agent_id] = response
                
        return responses
        
    async def update_shared_context(self, key: str, value: Any) -> None:
        """Update the shared context accessible to all agents.
        
        Args:
            key: Context key
            value: Context value
        """
        self.shared_context["shared_data"][key] = value
        
    def get_conversation_summary(self) -> str:
        """Get a summary of all agent communications."""
        if not self.shared_context["conversation_log"]:
            return "No communications recorded."
            
        summary = "🤖 Multi-Agent Conversation Summary\n"
        summary += "=" * 50 + "\n\n"
        
        for i, log in enumerate(self.shared_context["conversation_log"], 1):
            summary += f"{i}. {log['from_agent']} → {log['to_agent']}\n"
            summary += f"   Time: {log['timestamp']}\n"
            summary += f"   Message: {log['message'][:150]}{'...' if len(log['message']) > 150 else ''}\n"
            summary += f"   Response: {log['response'][:150]}{'...' if len(log['response']) > 150 else ''}\n\n"
            
        return summary


async def run_research_collaboration_scenario():
    """Run a scenario where agents collaborate on a research task."""
    
    print("🚀 Starting Multi-Agent Research Collaboration Scenario")
    print("=" * 60)
    
    # Initialize settings
    settings = AgentSettings()
    
    # Create orchestrator
    orchestrator = MultiAgentOrchestrator(settings)
    
    # Create specialized agents
    await orchestrator.create_agent(
        agent_id="research_agent",
        agent_name="Dr. Research",
        role_description="Information gathering and analysis specialist",
        specialized_prompt="""
You excel at:
- Gathering comprehensive information on topics
- Analyzing data and identifying key insights
- Providing structured research summaries
- Identifying knowledge gaps that need further investigation
"""
    )
    
    await orchestrator.create_agent(
        agent_id="planning_agent",
        agent_name="Strategic Planner",
        role_description="Strategy and planning specialist",
        specialized_prompt="""
You excel at:
- Creating detailed action plans
- Breaking down complex tasks into manageable steps
- Identifying dependencies and prerequisites
- Optimizing workflows and processes
"""
    )
    
    await orchestrator.create_agent(
        agent_id="execution_agent",
        agent_name="Implementation Expert",
        role_description="Solution implementation and execution specialist",
        specialized_prompt="""
You excel at:
- Implementing planned solutions
- Providing practical implementation details
- Identifying potential obstacles and solutions
- Creating actionable deliverables
"""
    )
    
    await orchestrator.create_agent(
        agent_id="review_agent",
        agent_name="Quality Reviewer",
        role_description="Quality assurance and review specialist",
        specialized_prompt="""
You excel at:
- Evaluating the quality of work and solutions
- Identifying improvements and optimizations
- Providing constructive feedback
- Ensuring deliverables meet requirements
"""
    )
    
    print()
    
    # Scenario: Research and develop a plan for implementing AI agents in a financial services company
    research_task = """
We need to research and develop a comprehensive plan for implementing AI agents 
in a financial services company. The agents should help with customer service, 
fraud detection, and investment recommendations. We need to understand the 
requirements, create an implementation plan, and ensure quality standards.
"""
    
    print("📋 TASK:")
    print(research_task)
    print()
    
    # Step 1: Research Agent gathers information
    print("🔍 Phase 1: Information Gathering")
    research_response = await orchestrator.agents["research_agent"].process_input(
        user_input=f"Please conduct comprehensive research on: {research_task}",
        include_history=False
    )
    
    print(f"Research findings: {research_response.content}...")
    print()
    
    # Step 2: Research Agent shares findings with Planning Agent
    print("📋 Phase 2: Strategic Planning")
    planning_response = await orchestrator.send_message_between_agents(
        from_agent_id="research_agent",
        to_agent_id="planning_agent",
        message=f"I've completed my research on AI implementation in financial services. Here are my key findings: {research_response.content}. Please create a detailed implementation plan based on this research."
    )
    
    # Step 3: Planning Agent shares plan with Execution Agent
    print("⚙️ Phase 3: Implementation Planning")
    execution_response = await orchestrator.send_message_between_agents(
        from_agent_id="planning_agent",
        to_agent_id="execution_agent",
        message=f"Here's the strategic plan I've developed: {planning_response}. Please provide detailed implementation steps and identify any technical requirements or potential challenges."
    )
    
    # Step 4: Review Agent evaluates the complete solution
    print("✅ Phase 4: Quality Review")
    
    # Compile all previous work for review
    complete_solution = f"""
RESEARCH FINDINGS:
{research_response.content}

STRATEGIC PLAN:
{planning_response}

IMPLEMENTATION DETAILS:
{execution_response}
"""
    
    review_response = await orchestrator.send_message_between_agents(
        from_agent_id="execution_agent",
        to_agent_id="review_agent",
        message=f"Please review our complete solution: {complete_solution}. Provide feedback on quality, completeness, and any areas for improvement."
    )
    
    # Step 5: Final collaboration - Address review feedback
    print("🔄 Phase 5: Iterative Improvement")
    
    # Let the team collaborate on addressing the review feedback
    improvement_responses = await orchestrator.broadcast_message(
        from_agent_id="review_agent",
        message=f"Here's my review and feedback: {review_response}. Each of you should consider how to address these points and improve your contribution.",
        context_data={"phase": "improvement", "review_complete": True}
    )
    
    print("💬 Improvement suggestions from all agents:")
    for agent_id, response in improvement_responses.items():
        agent_name = orchestrator.agents[agent_id].agent_name
        print(f"{agent_name}: {response}")
    print()
    
    # Display conversation summary
    print("📊 CONVERSATION SUMMARY")
    print("=" * 40)
    print(orchestrator.get_conversation_summary())
    
    return orchestrator


async def run_creative_collaboration_scenario():
    """Run a scenario where agents collaborate on a creative task."""
    
    print("🎨 Starting Multi-Agent Creative Collaboration Scenario")
    print("=" * 60)
    
    settings = AgentSettings()
    orchestrator = MultiAgentOrchestrator(settings)
    
    # Create creative agents
    await orchestrator.create_agent(
        agent_id="ideation_agent",
        agent_name="Creative Ideator",
        role_description="Creative concept generation specialist",
        specialized_prompt="You excel at generating innovative ideas, thinking outside the box, and inspiring creative solutions."
    )
    
    await orchestrator.create_agent(
        agent_id="design_agent", 
        agent_name="Design Architect",
        role_description="Design and user experience specialist",
        specialized_prompt="You excel at creating user-centered designs, visual concepts, and ensuring excellent user experiences."
    )
    
    await orchestrator.create_agent(
        agent_id="technical_agent",
        agent_name="Technical Advisor",
        role_description="Technical feasibility and implementation specialist", 
        specialized_prompt="You excel at evaluating technical feasibility, suggesting technical solutions, and ensuring implementability."
    )
    
    # Creative task: Design a mobile app for sustainable living
    creative_task = "Design an innovative mobile app that helps people live more sustainably in their daily lives."
    
    print(f"🎯 CREATIVE TASK: {creative_task}")
    print()
    
    # Round-robin creative collaboration
    print("💡 Phase 1: Ideation")
    ideas = await orchestrator.agents["ideation_agent"].process_input(
        user_input=f"Generate creative concepts for: {creative_task}",
        include_history=False
    )
    
    print("🎨 Phase 2: Design Concepts")
    design = await orchestrator.send_message_between_agents(
        from_agent_id="ideation_agent",
        to_agent_id="design_agent",
        message=f"Here are my creative concepts: {ideas.content}. Please develop these into concrete design concepts with user experience considerations."
    )
    
    print("⚙️ Phase 3: Technical Evaluation")
    technical = await orchestrator.send_message_between_agents(
        from_agent_id="design_agent", 
        to_agent_id="technical_agent",
        message=f"Here's the design concept: {design}. Please evaluate technical feasibility and suggest implementation approaches."
    )
    
    print("🔄 Phase 4: Iterative Refinement")
    refinement = await orchestrator.send_message_between_agents(
        from_agent_id="technical_agent",
        to_agent_id="ideation_agent", 
        message=f"Based on technical constraints: {technical}. How can we refine the original concepts to be both innovative and technically feasible?"
    )
    
    print("\n📊 Creative Collaboration Results:")
    print(f"Ideas: {ideas.content}...")
    print(f"Design: {design}...")
    print(f"Technical: {technical}...")
    print(f"Refinement: {refinement}...")
    
    return orchestrator


async def run_streaming_demo():
    """Demonstrate streaming communication between agents."""
    
    print("🌊 Starting Multi-Agent Streaming Demo")
    print("=" * 50)
    
    settings = AgentSettings()
    orchestrator = MultiAgentOrchestrator(settings)
    
    # Create agents for streaming demo
    await orchestrator.create_agent(
        agent_id="storyteller",
        agent_name="Story Weaver",
        role_description="Interactive storytelling specialist",
        specialized_prompt="You create engaging, interactive stories that respond to audience input and collaboration."
    )
    
    await orchestrator.create_agent(
        agent_id="character_agent",
        agent_name="Character Builder", 
        role_description="Character development specialist",
        specialized_prompt="You excel at creating compelling characters with rich backgrounds, motivations, and personalities."
    )
    
    print("📖 Collaborative Storytelling with Streaming")
    print()
    
    # Start a story
    story_prompt = "Start an adventure story about a team of explorers discovering a mysterious ancient technology."
    
    print("🎭 Story Weaver begins the tale...")
    story_agent = orchestrator.agents["storyteller"]
    
    # Demonstrate streaming response
    print("📡 Streaming story opening:")
    story_chunks: list[str] = []
    async for chunk in story_agent.stream_response(story_prompt):
        print(chunk, end='', flush=True)
        story_chunks.append(str(chunk))
    
    story_opening = ''.join(story_chunks)
    print("\n")
    
    # Character agent responds with character development
    print("👥 Character Builder adds character details...")
    character_response = await orchestrator.send_message_between_agents(
        from_agent_id="storyteller",
        to_agent_id="character_agent",
        message=f"Here's the story opening: {story_opening}. Please develop the main characters mentioned and add personality details."
    )
    
    print(f"Character development: {character_response[:200]}...")
    
    return orchestrator


async def main():
    """Run all multi-agent simulation scenarios."""
    
    print("🤖 FLARE AI KIT - MULTI-AGENT COMMUNICATION SIMULATION")
    print("=" * 70)
    print()
    
    try:
        # Check if API key is available
        settings = AgentSettings()
        if not settings.gemini_api_key.get_secret_value():
            print("❌ Error: GEMINI_API_KEY environment variable not set")
            print("Please set your Gemini API key:")
            print("export GEMINI_API_KEY='your-api-key-here'")
            return
            
        # Run scenarios
        print("🎯 Running Research Collaboration Scenario...")
        research_orchestrator = await run_research_collaboration_scenario()
        
        print("\n" + "="*70 + "\n")
        
        print("🎨 Running Creative Collaboration Scenario...")
        creative_orchestrator = await run_creative_collaboration_scenario()
        
        print("\n" + "="*70 + "\n")
        
        print("🌊 Running Streaming Communication Demo...")
        streaming_orchestrator = await run_streaming_demo()
        
        print("\n" + "="*70)
        print("✅ All multi-agent scenarios completed successfully!")
        print()
        print("Key Features Demonstrated:")
        print("- Agent-to-agent communication")
        print("- Shared context and state management")
        print("- Specialized agent roles and capabilities")
        print("- Collaborative problem-solving workflows")
        print("- Streaming responses in multi-agent scenarios")
        print("- Broadcasting and iterative improvement")
        
    except Exception as e:
        print(f"❌ Error running simulation: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
