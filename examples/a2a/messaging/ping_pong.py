import asyncio
from pathlib import Path

from flare_ai_kit.a2a import A2AClient
from flare_ai_kit.a2a.schemas import (
    Message,
    MessageSendParams,
    SendMessageRequest,
    TextPart,
)
from flare_ai_kit.a2a.settings import A2ASettings


async def main() -> None:
    """Entry function of the ping pong agent."""
    agent_card_url = (
        "https://system-integration.telex.im/ping_pong_agent/.well-known/agent.json"
    )
    agent_base_url = agent_card_url.split(".well-known")[0]
    settings = A2ASettings(sqlite_db_path=Path("tasks.db"))
    client = A2AClient(settings=settings)

    message = SendMessageRequest(
        params=MessageSendParams(
            message=Message(
                role="user",
                parts=[
                    TextPart(
                        text="ping",
                    )
                ],
                messageId="unique-message-id",
                taskId=None,
            )
        ),
    )

    response = await client.send_message(agent_base_url, message)
    print(response)


asyncio.run(main())
