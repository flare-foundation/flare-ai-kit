import asyncio
import uuid
import httpx
from typing import Optional, List, Dict, Coroutine, Any
from flare_ai_kit.a2a.task_management import TaskManager
from flare_ai_kit.a2a.schemas import (
    SendMessageRequest,
    SendMessageResponse,
    Task,
    AgentCard,
    AgentSkill,
)


class A2AClient:
    def __init__(self, db_path: str = "."):
        """Initialize the A2A client with SQLite database for task tracking."""
        self.db_path = db_path
        self.task_manager = TaskManager(db_path)
        self.agent_cards: Dict[str, AgentCard] = {}
        self.available_skills: List[AgentSkill] = []
        self.skill_to_agents: Dict[str, List[str]] = {}  # skill name -> list of agent URLs
    
    async def send_message(
        self, agent_base_url: str, message: SendMessageRequest
    ) -> SendMessageResponse:
        """Send a message to the agent and manage task tracking."""
        message.params.message.messageId = self._generate_message_id()

        # Send the message to the agent
        response = httpx.post(agent_base_url, json=message.model_dump())

        if response.status_code == 200:
            send_msg_response = SendMessageResponse.model_validate_json(response.text)

            if isinstance(send_msg_response.result, Task):
                task = send_msg_response.result
                self.task_manager.upsert_task(task.id, task.status.state)

            return send_msg_response
        else:
            raise Exception(f"Error while sending message: {response.status_code}")

    def update_skill_knowledgebase(self):
        self.available_skills.clear()
        self.skill_to_agents.clear()

        for url, agent_card in self.agent_cards.items():
            for skill in agent_card.skills:
                self.available_skills.append(skill)
                if skill.name not in self.skill_to_agents:
                    self.skill_to_agents[skill.name] = []
                self.skill_to_agents[skill.name].append(url)

    async def discover(self, agent_base_urls: List[str]):
        """
        Accepts a list of agent *base* URLs and fetches their agent card 
        from '<base_url>/.well-known/agent.json'.
        Automatically handles missing or extra slashes.
        """
        async with httpx.AsyncClient() as client:
            tasks: List[Coroutine[Any, Any, httpx.Response]] = []

            normalized_urls: List[str] = []
            for base_url in agent_base_urls:
                normalized = base_url.rstrip("/") + "/.well-known/agent.json"
                normalized_urls.append(normalized)
                tasks.append(client.get(normalized))

            responses = await asyncio.gather(*tasks)

            for index, base_url in enumerate(agent_base_urls):
                full_url = normalized_urls[index]
                response = responses[index]

                if response.status_code != 200:
                    raise RuntimeError(
                        f"Failed to fetch agent card from {full_url}: HTTP {response.status_code}"
                    )

                try:
                    agent_card = AgentCard.model_validate_json(response.text)
                    self.agent_cards[base_url.rstrip("/")] = agent_card
                except Exception as e:
                    raise ValueError(f"Failed to parse agent card from {full_url}: {e}")

        self.update_skill_knowledgebase()

    def _generate_message_id(self) -> str:
        """Generate a unique message ID."""
        return uuid.uuid4().hex

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a task through TaskManager."""
        return self.task_manager.cancel_task(task_id)

    def get_task_status(self, task_id: str) -> Optional[str]:
        """Get the task status by task ID."""
        task = self.task_manager.get_task(task_id)
        if task:
            return task.status.state
        return None
