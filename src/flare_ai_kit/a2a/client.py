"""A2A client for handling send messages to A2A servers."""

import asyncio
import uuid
from typing import TYPE_CHECKING, Any

import httpx
from pydantic import ValidationError

from flare_ai_kit.a2a.schemas import (
    AgentCard,
    AgentSkill,
    SendMessageRequest,
    SendMessageResponse,
    Task,
)
from flare_ai_kit.a2a.task_management import TaskManager
from flare_ai_kit.common import A2AClientError

from .settings import A2ASettings

if TYPE_CHECKING:
    from collections.abc import Coroutine


class A2AClient:
    """
    A2AClient responsible for interfacing with A2A servers.

    Contains methods for:
    1. sending message.
    2. discovering A2A servers via their agent card.
    3. performing task management,
    """

    def __init__(self, settings: A2ASettings) -> None:
        """Initialize the A2A client with SQLite database for task tracking."""
        self.sqlite_db_path = settings.sqlite_db_path
        self.client_timeout = settings.client_timeout
        self.task_manager = TaskManager(self.sqlite_db_path)
        self.agent_cards: dict[str, AgentCard] = {}
        self.available_skills: list[AgentSkill] = []
        self.skill_to_agents: dict[
            str, list[str]
        ] = {}  # skill name -> list of agent URLs
        self.http_client = httpx.AsyncClient(timeout=self.client_timeout)

    async def send_message(
        self,
        agent_base_url: str,
        message: SendMessageRequest,
        *,
        timeout_seconds: float = 30.0,
    ) -> SendMessageResponse:
        """Send a message to the agent and manage task tracking."""
        message.params.message.message_id = self._generate_message_id()

        response = await self.http_client.post(
            agent_base_url, json=message.model_dump(), timeout=timeout_seconds
        )

        if response.status_code == httpx.codes.OK.value:
            send_msg_response = SendMessageResponse.model_validate_json(response.text)

            if isinstance(send_msg_response.result, Task):
                task = send_msg_response.result
                self.task_manager.upsert_task(task.id, task.status.state)

            return send_msg_response
        error_message = f"Error: {response.status_code}"
        raise A2AClientError(error_message)

    def update_skill_knowledge_base(self) -> None:
        """Update the available skills and skill_to_agent index."""
        self.available_skills.clear()
        self.skill_to_agents.clear()

        for url, agent_card in self.agent_cards.items():
            for skill in agent_card.skills:
                self.available_skills.append(skill)
                if skill.name not in self.skill_to_agents:
                    self.skill_to_agents[skill.name] = []
                self.skill_to_agents[skill.name].append(url)

    async def discover(self, agent_base_urls: list[str]) -> None:
        """
        Accepts a list of agent *base* URLs and fetches their agent card.

        This combines the base url and a well-known route.
        For example: '<base_url>/.well-known/agent.json'.
        It automatically handles missing or extra slashes.
        """
        tasks: list[Coroutine[Any, Any, httpx.Response]] = []

        normalized_urls: list[str] = []
        for base_url in agent_base_urls:
            normalized = base_url.rstrip("/") + "/.well-known/agent.json"
            normalized_urls.append(normalized)
            tasks.append(self.http_client.get(normalized))

        responses = await asyncio.gather(*tasks)

        for index, base_url in enumerate(agent_base_urls):
            full_url = normalized_urls[index]
            response = responses[index]

            if response.status_code != httpx.codes.OK.value:
                error_msg = f"""
                Failed to fetch agent card from {full_url}:\
                HTTP {response.status_code}
                """
                raise RuntimeError(error_msg)

            try:
                agent_card = AgentCard.model_validate_json(response.text)
                self.agent_cards[base_url.rstrip("/")] = agent_card
            except (ValidationError, ValueError) as e:
                error_msg = f"Failed to parse agent card from {full_url}: {e}"
                raise ValueError(error_msg) from e

        self.update_skill_knowledge_base()

    def _generate_message_id(self) -> str:
        """Generate a unique message ID."""
        return uuid.uuid4().hex

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a task through TaskManager."""
        return self.task_manager.cancel_task(task_id)

    def get_task_status(self, task_id: str) -> str | None:
        """Get the task status by task ID."""
        task = self.task_manager.get_task(task_id)
        if task:
            return task.status.state
        return None
