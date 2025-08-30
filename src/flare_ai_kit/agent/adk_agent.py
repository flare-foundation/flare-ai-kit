"""Google ADK agent implementation for Flare AI Kit."""

from google.adk.agents import Agent

# Import all tool modules to register tools
from flare_ai_kit.agent.settings import AgentSettings
from flare_ai_kit.agent.tool import TOOL_REGISTRY

# Import tool modules to ensure they are registered
from flare_ai_kit.agent import ecosystem_tools, social_tools, tee_tools, wallet_tools 

settings = AgentSettings()

agent = Agent(
    name="flare_ai_kit_agent",
    model=settings.gemini_model,
    tools=TOOL_REGISTRY,
    instruction="""
You are a Flare AI Kit agent that helps users interact with the Flare blockchain \
ecosystem.

You have access to tools for:
- Ecosystem: Get FTSO prices, check balances, interact with Flare blockchain
- TEE: Create and validate attestation tokens for trusted execution environments
- Wallet: Create wallets, sign transactions, manage permissions with Turnkey
- Social: Send messages to Telegram and post tweets to X

Always provide helpful, accurate information about Flare blockchain capabilities.
When using tools, explain what you're doing and interpret the results for the user.
""".strip(),
)
