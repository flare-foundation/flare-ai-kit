import os
from uuid import uuid4

from dotenv import load_dotenv
from pydantic import BaseModel
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.gemini import GeminiModel
from pydantic_ai.providers.google_gla import GoogleGLAProvider

from flare_ai_kit.a2a import A2AServer
from flare_ai_kit.a2a.schemas import (
    AgentCapabilities,
    AgentCard,
    AgentProvider,
    AgentSkill,
    Message,
    SendMessageRequest,
    SendMessageResponse,
    TextPart,
)
from flare_ai_kit.a2a.task_management import TaskManager

load_dotenv()


class AgentDependencies(BaseModel):
    """Dependencies for the agent."""

    historical_data: dict[str, dict[str, float]]

    model_config = {
        "arbitrary_types_allowed": True,
    }


# Historical price data
historical_prices = {
    "BTC": {
        "current": 111358.0,
        "24h_ago": 108602.0,
        "7d_ago": 107472.0,
        "30d_ago": 109454.0,
    },
    "ETH": {"current": 2810.94, "24h_ago": 2608.6, "7d_ago": 2584.6, "30d_ago": 2358.6},
    "FLR": {
        "current": 0.01630,
        "24h_ago": 0.01607,
        "7d_ago": 0.01725,
        "30d_ago": 0.0184,
    },
}

model = GeminiModel(
    os.getenv("AGENT__GEMINI_MODEL", "gemini-2.5-flash"),
    provider=GoogleGLAProvider(api_key=os.getenv("AGENT__GEMINI_API_KEY")),
)

analysis_agent = Agent(
    model,
    deps_type=AgentDependencies,
    retries=2,
    system_prompt=(
        "You are a cryptocurrency price analysis assistant. "
        "When a user provides a token symbol and price, "
        "use the analyze_price tool to check if the price is up or down "
        "from 24h, 7d, and 30d ago. "
        "Respond with a single sentence stating the changes. Be concise and direct."
    ),
)


def calculate_change_percentage(current: float, previous: float) -> float:
    """Calculate percentage change between two prices."""
    if previous == 0:
        return 0.0
    return ((current - previous) / previous) * 100


@analysis_agent.tool
async def analyze_price(
    ctx: RunContext[AgentDependencies], symbol: str, current_price: float
) -> str:
    """Analyze a cryptocurrency price against historical data."""
    # Normalize symbol (remove common suffixes)
    clean_symbol = (
        symbol.upper().replace("/USD", "").replace("/USDT", "").replace("-USD", "")
    )

    historical = ctx.deps.historical_data.get(clean_symbol)

    if not historical:
        return f"No historical data available for {symbol}"

    # Calculate changes
    change_24h = calculate_change_percentage(
        current_price, historical.get("24h_ago", current_price)
    )
    change_7d = calculate_change_percentage(
        current_price, historical.get("7d_ago", current_price)
    )
    change_30d = calculate_change_percentage(
        current_price, historical.get("30d_ago", current_price)
    )

    # Format changes with + or - signs
    def format_change(change: float) -> str:
        if change > 0:
            return f"+{change:.2f}%"
        return f"{change:.2f}%"

    return f"""
        {symbol} at ${current_price:.4f} is {format_change(change_24h)}\
        from 24h ago, {format_change(change_7d)}\
        from 7d ago, and {format_change(change_30d)}\
        from 30d ago.
    """


task_manager = TaskManager()


async def handle_send_message(request_body: SendMessageRequest) -> SendMessageResponse:
    """Message send handler."""
    try:
        user_message = ""
        for part in request_body.params.message.parts:
            if part.kind == "text":
                user_message += part.text

        deps = AgentDependencies(historical_data=historical_prices)
        result = await analysis_agent.run(user_message, deps=deps)

        return SendMessageResponse(
            result=Message(
                messageId=uuid4().hex,
                role="agent",
                parts=[TextPart(text=str(result.output))],
            )
        )
    except Exception as e:
        error_message = f"Error analyzing price: {e!s}"
        return SendMessageResponse(
            result=Message(
                messageId=uuid4().hex,
                role="agent",
                parts=[TextPart(text=error_message)],
            )
        )


if __name__ == "__main__":
    protocol = "http"
    host = "localhost"
    port = 4501

    base_url = f"{protocol}://{host}:{port}"

    card = AgentCard(
        name="Price Analysis Agent",
        version="0.1.0",
        url=base_url,
        description="""
        A simple agent that analyzes cryptocurrency prices against historical data
        """,
        provider=AgentProvider(
            organization="Flare Foundation", url="https://flare.network"
        ),
        capabilities=AgentCapabilities(streaming=False, pushNotifications=False),
        skills=[
            AgentSkill(
                id="price_analysis",
                name="Price Analysis",
                tags=["price", "analysis", "crypto"],
                description="""
                    Analyze current cryptocurrency prices against historical data
                """,
                examples=["Analyze BTC at $111000", "Check FLR price at $0.016"],
                inputModes=["text/plain"],
                outputModes=["text/plain"],
            )
        ],
    )

    a2a_server = A2AServer(card, host=host, port=port)
    a2a_server.service.add_handler(SendMessageRequest, handle_send_message)
    a2a_server.run()
