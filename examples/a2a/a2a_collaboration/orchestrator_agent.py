import asyncio
import os
from pathlib import Path
from uuid import uuid4

import structlog
from dotenv import load_dotenv
from pydantic import BaseModel
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.gemini import GeminiModel
from pydantic_ai.providers.google_gla import GoogleGLAProvider

from flare_ai_kit.a2a import A2AClient
from flare_ai_kit.a2a.schemas import (
    Message,
    MessageSendParams,
    SendMessageRequest,
    TextPart,
)
from flare_ai_kit.a2a.settings import A2ASettings

load_dotenv()

logger = structlog.get_logger(__name__)


class OrchestratorDeps(BaseModel):
    """Dependencies required by the Orchestrator agent."""

    client: A2AClient

    model_config = {
        "arbitrary_types_allowed": True,
    }


model = GeminiModel(
    os.getenv("AGENT__GEMINI_MODEL", "gemini-2.5-flash"),
    provider=GoogleGLAProvider(api_key=os.getenv("AGENT__GEMINI_API_KEY")),
)

orchestrator_agent = Agent(
    model=model,
    deps_type=OrchestratorDeps,
    system_prompt=(
        "You are an orchestration agent. "
        "Your job is to break down user queries into smaller subtasks "
        "and assign each to the most suitable skill. "
        "You can run these tasks either in parallel (if independent) "
        "or sequentially (if later tasks need earlier results). "
        "Use route_workflow for flexible sequencing of tasks "
        "and route_tasks if all tasks are independent. "
        "Use list_skills if you need to see the available skills first."
    ),
)


class SubTask(BaseModel):
    """Input schema for orchestrator sub task."""

    query: str
    skill_name: str


class WorkflowSubTask(BaseModel):
    """Input schema for orchestrator workflow."""

    query: str
    skill_name: str
    use_previous_result: bool | None = False


@orchestrator_agent.tool
async def list_skills(ctx: RunContext[OrchestratorDeps]) -> str:
    """Returns a list of available skills and their descriptions."""
    return "\n".join(
        f"{skill.name}: {skill.description}"
        for skill in ctx.deps.client.available_skills
    )


@orchestrator_agent.tool
async def route_tasks(
    ctx: RunContext[OrchestratorDeps], subtasks: list[SubTask]
) -> str:
    """
    Routes independent subtasks to the appropriate agents.

    Return their combined responses.
    """
    client = ctx.deps.client
    results: list[str] = []

    for subtask in subtasks:
        agent_urls = client.skill_to_agents.get(subtask.skill_name)
        if not agent_urls:
            results.append(f"[No agent found for skill '{subtask.skill_name}']")
            continue

        agent_url = agent_urls[0]
        message = SendMessageRequest(
            params=MessageSendParams(
                message=Message(
                    messageId=uuid4().hex,
                    role="user",
                    parts=[TextPart(text=subtask.query)],
                )
            )
        )

        try:
            response = await client.send_message(
                agent_url, message, timeout_seconds=30.0
            )
            if isinstance(response.result, Message):
                text = "".join(
                    part.text
                    for part in response.result.parts
                    if isinstance(part, TextPart)
                )
                results.append(f"Result from {subtask.skill_name}:\n{text}")
            else:
                results.append(f"[No result from agent at {agent_url}]")

        except Exception as e:
            results.append(f"[Error from agent at {agent_url}]: {e!s}")

    return (
        "\n---\n".join(results) if results else "No results received from any agents."
    )


@orchestrator_agent.tool
async def route_workflow(
    ctx: RunContext[OrchestratorDeps], subtasks: list[WorkflowSubTask]
) -> str:
    """
    Executes a workflow of subtasks.

    Optionally passing previous results to the next subtask.
    """
    client = ctx.deps.client
    previous_result = ""
    results: list[str] = []

    for subtask in subtasks:
        input_query = subtask.query
        if subtask.use_previous_result and previous_result:
            input_query = f"{input_query}\n\nPrevious result:\n{previous_result}"

        agent_urls = client.skill_to_agents.get(subtask.skill_name)
        if not agent_urls:
            results.append(f"[No agent found for skill '{subtask.skill_name}']")
            continue

        agent_url = agent_urls[0]
        message = SendMessageRequest(
            params=MessageSendParams(
                message=Message(
                    messageId=uuid4().hex,
                    role="user",
                    parts=[TextPart(text=input_query)],
                )
            )
        )

        try:
            response = await client.send_message(agent_url, message)
            if isinstance(response.result, Message):
                previous_result = "".join(
                    part.text
                    for part in response.result.parts
                    if isinstance(part, TextPart)
                )
                results.append(f"Result from {subtask.skill_name}:\n{previous_result}")
            else:
                results.append(f"[No result from agent at {agent_url}]")

        except Exception as e:
            results.append(f"[Error from agent at {agent_url}]: {e!s}")

    return "\n---\n".join(results) if results else "No results received in workflow."


if __name__ == "__main__":

    async def main() -> None:
        """Async entrypoint for orchestrator agent."""
        settings = A2ASettings(sqlite_db_path=Path("orchestrator-agent.db"))
        client = A2AClient(settings=settings)

        await client.discover(
            [
                "http://localhost:4500",
                "http://localhost:4501",
            ]
        )

        deps = OrchestratorDeps(client=client)
        result = await orchestrator_agent.run(
            "Get me the current BTC price, and then use that to analyze BTC trends.",
            deps=deps,
        )

        logger.info(result.output)

    asyncio.run(main())
