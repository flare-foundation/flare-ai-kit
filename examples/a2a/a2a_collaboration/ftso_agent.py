import locale
import os
from uuid import uuid4

from dotenv import load_dotenv
from pydantic import BaseModel
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.gemini import GeminiModel
from pydantic_ai.providers.google_gla import GoogleGLAProvider

from flare_ai_kit import FlareAIKit
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


class PriceRequest(BaseModel):
    """Model for price requests."""

    symbol: str
    base_currency: str | None = "USD"


class PriceResponse(BaseModel):
    """Model for price responses."""

    symbol: str
    price: float
    formated_price: str
    currency: str
    timestamp: str


class AgentDependencies(BaseModel):
    """Dependencies for the agent."""

    flare_kit: FlareAIKit

    model_config = {
        "arbitrary_types_allowed": True,
    }


model = GeminiModel(
    os.getenv("AGENT__GEMINI_MODEL", "gemini-2.5-flash"),
    provider=GoogleGLAProvider(api_key=os.getenv("AGENT__GEMINI_API_KEY")),
)

price_agent = Agent(
    model,
    deps_type=AgentDependencies,
    retries=2,
    system_prompt=(
        "You are a crypto price assistant. "
        "You help users get current prices for cryptocurrency pairs. "
        "When users ask for prices, "
        "identify the cryptocurrency symbols they want "
        "and call the appropriate tools. "
        "Common symbols include FLR, BTC, ETH, ADA, etc. "
        "Default to USD pairs unless specified otherwise. "
        "Do also display the formated price in "
        "parenthesis for easier readability. "
        "An example: The current price of BTC "
        "is 111070.88 USD ($111,070.88). "
        "Ensure you add the forward slash "
        "for the pair between the symbols."
    ),
)


def format_price(price: float, target_locale: str = "en_US.UTF-8") -> str:
    """Returns price formated in currency: defaults to USD."""
    locale.setlocale(locale.LC_ALL, target_locale)
    return locale.currency(price, grouping=True)


@price_agent.tool
async def get_crypto_price(
    ctx: RunContext[AgentDependencies], symbol: str
) -> PriceResponse:
    """Get the latest price for a cryptocurrency pair."""
    try:
        ftso = await ctx.deps.flare_kit.ftso

        price = await ftso.get_latest_price(symbol)

        return PriceResponse(
            symbol=symbol,
            price=price,
            formated_price=format_price(price),
            currency="USD",
            timestamp="now",
        )
    except Exception as e:
        msg = f"Could not get price for {symbol}: {e!s}"
        raise ValueError(msg) from e


@price_agent.tool
async def get_multiple_prices(
    ctx: RunContext[AgentDependencies], symbols: list[str]
) -> list[PriceResponse]:
    """Get prices for multiple cryptocurrency pairs."""
    try:
        # Use FlareAIKit to get the FTSO client
        ftso = await ctx.deps.flare_kit.ftso
        prices_data = await ftso.get_latest_prices(symbols)

        results: list[PriceResponse] = []
        for i, symbol in enumerate(symbols):
            price = prices_data[i]
            results.append(
                PriceResponse(
                    symbol=symbol,
                    price=price,
                    formated_price=format_price(price),
                    currency="USD",
                    timestamp="now",
                )
            )
    except Exception as e:
        msg = f"Could not get prices for {symbols}: {e!s}"
        raise ValueError(msg) from e
    else:
        return results


task_manager = TaskManager()


async def handle_send_message(request_body: SendMessageRequest) -> SendMessageResponse:
    """Message send handler."""
    try:
        user_message = ""
        for part in request_body.params.message.parts:
            if part.kind == "text":
                user_message += part.text

        kit = FlareAIKit(config=None)  # Use default settings
        deps = AgentDependencies(flare_kit=kit)

        result = await price_agent.run(user_message, deps=deps)

        response_text = str(result.output)

        return SendMessageResponse(
            result=Message(
                messageId=uuid4().hex,
                role="agent",
                parts=[TextPart(text=response_text)],
            )
        )
    except Exception as e:
        error_message = f"I apologize, but I encountered an error: {e!s}"
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
    port = 4500

    base_url = f"{protocol}://{host}:{port}"

    card = AgentCard(
        name="FTSO Agent",
        version="0.1.0",
        url=base_url,
        description="An agent that gets prices",
        provider=AgentProvider(
            organization="Flare Foundation", url="https://flare.network"
        ),
        capabilities=AgentCapabilities(streaming=False, pushNotifications=False),
        skills=[
            AgentSkill(
                id="list_prices",
                name="List Prices",
                tags=["BTC", "FLR"],
                description="List prices of crypto pairs",
                examples=["List prices for FLR/USD and BTC/USD"],
                inputModes=["text/plain"],
                outputModes=["text/plain"],
            )
        ],
    )

    a2a_server = A2AServer(card, host=host, port=port)
    a2a_server.service.add_handler(SendMessageRequest, handle_send_message)
    a2a_server.run()
