#!/usr/bin/env python3
"""
Agent-to-Agent (A2A) Collaboration Script

This script demonstrates A2A collaboration between multiple AI agents.
It includes an orchestrator agent that coordinates with FTSO and price analysis agents.
Requires: a2a extras (fastapi)

Usage:
    python scripts/a2a_collaboration.py

Environment Variables:
    AGENT__GEMINI_API_KEY: Gemini API key for AI agents
    ECOSYSTEM__FLARE_RPC_URL: Flare network RPC URL for FTSO data
"""

import asyncio
import locale
import os
import sys
from pathlib import Path
from uuid import uuid4

# Add src to path for local development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dotenv import load_dotenv
from pydantic import BaseModel
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.gemini import GeminiModel

from flare_ai_kit import FlareAIKit

# Load environment variables
load_dotenv()


class PriceRequest(BaseModel):
    """Model for price requests."""

    symbol: str
    base_currency: str | None = "USD"


class AgentDependencies(BaseModel):
    """Dependencies for the agent."""

    historical_data: dict[str, dict[str, float]]
    model_config = {
        "arbitrary_types_allowed": True,
    }


# FTSO Agent
class FTSOAgent:
    """Agent that fetches cryptocurrency prices using FTSO."""

    def __init__(self):
        self.kit = FlareAIKit()
        self.agent_id = str(uuid4())
        self.name = "FTSO Price Agent"

        # Set up the AI agent
        self.ai_agent = Agent(
            model=GeminiModel(
                model_name="gemini-1.5-flash",
                api_key=os.getenv("AGENT__GEMINI_API_KEY"),
            ),
            deps_type=None,
            system_prompt=(
                "You are a cryptocurrency price fetching agent. "
                "You can fetch real-time prices from the Flare Time Series Oracle (FTSO). "
                "When asked for prices, use the available tools to get accurate data."
            ),
        )

        # Add price fetching tool
        @self.ai_agent.tool
        async def get_crypto_price(ctx: RunContext[None], symbol: str) -> str:
            """Fetch cryptocurrency price from FTSO."""
            try:
                ftso = await self.kit.ftso
                price = await ftso.get_latest_price(f"{symbol}/USD")
                return f"Current {symbol}/USD price: ${price}"
            except Exception as e:
                return f"Error fetching {symbol} price: {e!s}"

    async def handle_message(self, message: str) -> str:
        """Handle incoming messages and return responses."""
        try:
            result = await self.ai_agent.run(message)
            return result.data
        except Exception as e:
            return f"Error processing request: {e!s}"


# Price Analysis Agent
class PriceAnalysisAgent:
    """Agent that analyzes price data against historical trends."""

    def __init__(self):
        self.agent_id = str(uuid4())
        self.name = "Price Analysis Agent"

        # Mock historical data for demo
        self.historical_data = {
            "BTC": {"avg_30d": 45000, "high_30d": 50000, "low_30d": 40000},
            "ETH": {"avg_30d": 3000, "high_30d": 3500, "low_30d": 2500},
            "FLR": {"avg_30d": 0.025, "high_30d": 0.035, "low_30d": 0.020},
        }

        # Set up the AI agent
        self.ai_agent = Agent(
            model=GeminiModel(
                model_name="gemini-1.5-flash",
                api_key=os.getenv("AGENT__GEMINI_API_KEY"),
            ),
            deps_type=AgentDependencies,
            system_prompt=(
                "You are a cryptocurrency price analysis agent. "
                "You analyze current prices against historical data to provide insights. "
                "Use the historical data to determine if prices are high, low, or average."
            ),
        )

        # Add analysis tool
        @self.ai_agent.tool
        async def analyze_price(
            ctx: RunContext[AgentDependencies], symbol: str, current_price: float
        ) -> str:
            """Analyze current price against historical data."""
            historical = ctx.deps.historical_data.get(symbol.upper())
            if not historical:
                return f"No historical data available for {symbol}"

            avg_price = historical["avg_30d"]
            high_price = historical["high_30d"]
            low_price = historical["low_30d"]

            if current_price > avg_price * 1.1:
                trend = "significantly above average"
            elif current_price < avg_price * 0.9:
                trend = "significantly below average"
            else:
                trend = "near average"

            return (
                f"Price Analysis for {symbol}:\n"
                f"Current: ${current_price:,.2f}\n"
                f"30-day average: ${avg_price:,.2f}\n"
                f"30-day range: ${low_price:,.2f} - ${high_price:,.2f}\n"
                f"Assessment: Price is {trend}"
            )

    async def handle_message(self, message: str) -> str:
        """Handle incoming messages and return responses."""
        try:
            deps = AgentDependencies(historical_data=self.historical_data)
            result = await self.ai_agent.run(message, deps=deps)
            return result.data
        except Exception as e:
            return f"Error processing analysis: {e!s}"


# Orchestrator Agent
class OrchestratorAgent:
    """Agent that coordinates between FTSO and analysis agents."""

    def __init__(self, ftso_agent: FTSOAgent, analysis_agent: PriceAnalysisAgent):
        self.ftso_agent = ftso_agent
        self.analysis_agent = analysis_agent
        self.agent_id = str(uuid4())
        self.name = "Orchestrator Agent"

    async def handle_complex_query(self, query: str) -> str:
        """Handle complex queries by coordinating between agents."""
        print(f"🎯 Orchestrator processing: {query}")

        # Step 1: Get current price from FTSO agent
        print("📊 Fetching current price...")
        price_response = await self.ftso_agent.handle_message(query)
        print(f"💰 Price data: {price_response}")

        # Step 2: Extract price and symbol for analysis
        # This is a simplified extraction - in practice you'd use more sophisticated parsing
        if "BTC" in query.upper():
            symbol = "BTC"
        elif "ETH" in query.upper():
            symbol = "ETH"
        elif "FLR" in query.upper():
            symbol = "FLR"
        else:
            return f"Price fetched: {price_response}\nNote: Analysis requires BTC, ETH, or FLR"

        # Extract price value (simplified)
        try:
            import re

            price_match = re.search(r"\$([0-9,]+\.?[0-9]*)", price_response)
            if price_match:
                price_str = price_match.group(1).replace(",", "")
                current_price = float(price_str)

                # Step 3: Get analysis
                print("📈 Performing price analysis...")
                analysis_query = (
                    f"Analyze the current price of {symbol} at ${current_price}"
                )
                analysis_response = await self.analysis_agent.handle_message(
                    analysis_query
                )
                print(f"📊 Analysis: {analysis_response}")

                # Step 4: Combine results
                combined_response = (
                    f"🔍 Complete Market Analysis:\n\n"
                    f"Current Market Data:\n{price_response}\n\n"
                    f"Historical Analysis:\n{analysis_response}\n\n"
                    f"💡 This analysis combines real-time FTSO data with historical trends."
                )
                return combined_response
            return (
                f"Price data: {price_response}\nCould not extract price for analysis."
            )

        except Exception as e:
            return f"Price data: {price_response}\nAnalysis error: {e!s}"


async def run_collaboration_demo():
    """Run the A2A collaboration demo."""
    print("🚀 Starting A2A Collaboration Demo...")

    # Initialize agents
    print("🤖 Initializing agents...")
    ftso_agent = FTSOAgent()
    analysis_agent = PriceAnalysisAgent()
    orchestrator = OrchestratorAgent(ftso_agent, analysis_agent)

    # Demo queries
    queries = [
        "What is the current BTC price?",
        "Get me the latest ETH price and analyze it",
        "How is FLR performing compared to historical data?",
    ]

    print("\n" + "=" * 60)
    print("🎭 A2A COLLABORATION DEMONSTRATION")
    print("=" * 60)

    for i, query in enumerate(queries, 1):
        print(f"\n🔍 Query {i}: {query}")
        print("-" * 50)

        try:
            response = await orchestrator.handle_complex_query(query)
            print(f"✅ Response:\n{response}")
        except Exception as e:
            print(f"❌ Error: {e}")

        print("\n" + "=" * 60)

    print("🎉 A2A Collaboration Demo completed!")


async def main():
    """Main function."""
    try:
        await run_collaboration_demo()
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        raise


if __name__ == "__main__":
    # Set locale for number formatting
    try:
        locale.setlocale(locale.LC_ALL, "")
    except locale.Error:
        pass  # Use default locale if setting fails

    asyncio.run(main())
