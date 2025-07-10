import asyncio
from flare_ai_kit.a2a import A2AClient
from flare_ai_kit.a2a.schemas import (
    SendMessageRequest,
    MessageSendParams,
    Message,
    TextPart,
)

async def main():
    agent_card_url = "https://system-integration.telex.im/ping_pong_agent/.well-known/agent.json"
    agent_base_url = agent_card_url.split(".well-known")[0]
    client = A2AClient(db_path="tasks.db")

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