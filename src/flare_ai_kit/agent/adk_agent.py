"""Based ADK Agent using all tools."""

import os

from google.adk.agents import Agent

from flare_ai_kit.agent.pdf_tools import read_pdf_text_tool
from flare_ai_kit.agent.settings import AgentSettings
from flare_ai_kit.agent.tool import TOOL_REGISTRY

settings = AgentSettings()

if settings.gemini_api_key:
    os.environ["GOOGLE_API_KEY"] = settings.gemini_api_key.get_secret_value()


agent = Agent(
    name="flare_ecosystem_agent",
    model=settings.gemini_model,  # unwrap SecretStr
    tools=TOOL_REGISTRY,
)

settings = AgentSettings()

pdf_agent = Agent(
    name="flare_pdf_agent",
    model=settings.gemini_model,
    tools=[read_pdf_text_tool],
    instruction=(
        "You are a PDF extraction agent. "
        "Independently read PDFs using tools and return ONLY JSON matching this schema:\n"
        "{\n"
        '  "template_name": string,\n'
        '  "fields": [ {"field_name": string, "value": string|null}, ... ]\n'
        "}\n"
        "- Always call read_pdf_text with the provided file path.\n"
        "- Use ONLY the template JSON (field order and names) provided by the user to decide what to extract.\n"
        "- If a field is not found, set its value to null.\n"
        "- Do not include prose or explanations. Reply with a single JSON object only."
    ),
)
