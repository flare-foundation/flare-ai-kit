"""Based ADK Agent using all tools."""

from google.adk.agents import Agent

from flare_ai_kit.agent.settings import AgentSettings
from flare_ai_kit.agent.tool import TOOL_REGISTRY

settings = AgentSettings()

agent = Agent(
    name="Flare ADK Agent",
    model=settings.gemini_model,  # unwrap SecretStr
    tools=TOOL_REGISTRY,
)
