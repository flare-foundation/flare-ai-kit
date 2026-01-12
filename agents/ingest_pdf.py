"""
PDF ingestion agent.
"""

from __future__ import annotations

import json
import os
import re
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, mock_open, patch

import structlog
import uvicorn

# Import from local data directory
from data.create_sample_invoice import create_invoice_and_build_template
from fastapi import FastAPI, HTTPException, Request
from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from pydantic import BaseModel

from flare_ai_kit import FlareAIKit
from flare_ai_kit.agent.pdf_tools import read_pdf_text_tool
from flare_ai_kit.config import AppSettings
from flare_ai_kit.ingestion.settings import (
    IngestionSettings,
    OnchainContractSettings,
    PDFIngestionSettings,
    PDFTemplateSettings,
)

if TYPE_CHECKING:
    from pathlib import Path

logger = structlog.get_logger(__name__)

# --- TEE Configuration ---
EXTENSION_PORT = 8889
MOCK_TX_HASH = "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"

SYSTEM_INSTRUCTION = (
    "You are a PDF extraction agent. Independently read PDFs using tools and return ONLY JSON "
    "matching the user provided template schema. \n"
    "- Always call read_pdf_text first.\n"
    "- If a field is not found, set value to null.\n"
    "- Reply with a single JSON object only (no markdown, no prose)."
)


# --- Global State  ---
class AppState:
    def __init__(self) -> None:
        self.status = "initialized"
        self.last_result: dict[str, Any] | None = None
        self.transaction_hash: str | None = None


app_state = AppState()
app = FastAPI()


# --- Helper Functions ---


def build_prompt(
    pdf: Path, template: PDFTemplateSettings, max_pages: int | None
) -> str:
    """Constructs the analysis prompt."""
    return (
        f"PDF_PATH: {pdf}\nMAX_PAGES: {max_pages or 'ALL'}\n"
        f"TEMPLATE_SCHEMA:\n```json\n{json.dumps(template.model_dump())}\n```\n"
        "Extract fields based on the schema above from the PDF."
    )


def extract_json(text: str) -> dict[str, Any]:
    """Robustly extracts JSON from raw LLM response text."""
    try:
        return json.loads(text)
    except json.JSONDecodeError as err:
        if match := re.search(
            r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL | re.IGNORECASE
        ):
            return json.loads(match.group(1))
        if match := re.search(r"\{.*\}", text, re.DOTALL):
            return json.loads(match.group(0))
        msg = f"Could not extract valid JSON from response: {text[:100]}..."
        raise ValueError(msg) from err


async def run_extraction_agent(
    agent: Agent,
    pdf: Path,
    template: PDFTemplateSettings,
) -> dict[str, Any]:
    """Setup in-memory ADK agent, give it the PDF, template and prompt."""
    svc = InMemorySessionService()
    await svc.create_session(app_name="agents", user_id="user", session_id="session")
    runner = Runner(agent=agent, app_name="agents", session_service=svc)

    prompt = build_prompt(pdf, template, max_pages=1)
    message = types.Content(role="user", parts=[types.Part(text=prompt)])

    logger.info("calling agent", model=agent.model)

    final_text = ""
    async for event in runner.run_async(
        user_id="user", session_id="session", new_message=message
    ):
        if event.is_final_response() and event.content and event.content.parts:
            final_text = event.content.parts[0].text
            break

    if not final_text:
        msg = "Agent produced no response."
        raise RuntimeError(msg)

    return extract_json(final_text)


async def process_pdf_workflow() -> dict[str, Any]:
    """
    Refactored logic from the original main() function.
    This runs the actual business logic when triggered by the TEE.
    """
    logger.info("Starting PDF workflow...")
    app_state.status = "processing"

    try:
        # Create PDF and save it (In a real TEE, this might come from the input payload)
        pdf_path, template = create_invoice_and_build_template("generated_invoice")
        logger.info("loaded pdf", path=pdf_path)

        # Add template to global settings
        app_settings = AppSettings(
            log_level="INFO",
            ingestion=IngestionSettings(
                pdf_ingestion=PDFIngestionSettings(
                    templates=[template],
                    use_ocr=False,
                    contract_settings=OnchainContractSettings(
                        contract_address="0x0000000000000000000000000000000000000000",
                        abi_name="OnchainDataRegistry",
                        function_name="registerDocument",
                    ),
                )
            ),
        )

        # Inject Gemini API Key
        if app_settings.agent and app_settings.agent.gemini_api_key:
            api_key = app_settings.agent.gemini_api_key.get_secret_value()
            os.environ["GOOGLE_API_KEY"] = api_key

        # Create ADK agent with tool access
        agent = Agent(
            name="flare_pdf_agent",
            model=app_settings.agent.gemini_model,
            tools=[read_pdf_text_tool],
            instruction=SYSTEM_INSTRUCTION,
            generate_content_config=types.GenerateContentConfig(
                temperature=0.0, top_k=1, top_p=0.3, candidate_count=1
            ),
        )

        kit = FlareAIKit(config=app_settings)

        # Deterministic parsing
        parsed = kit.pdf_processor.process_pdf(
            file_path=str(pdf_path), template_name=template.template_name
        )
        logger.info("deterministic parsed", parsed=parsed)

        # Agent parsing
        result = await run_extraction_agent(agent, pdf_path, template)
        logger.info("agent parsed", result=result)

        # Update state with result
        app_state.last_result = result

        # Mock onchain contract posting
        with (
            patch(
                "flare_ai_kit.onchain.contract_poster.ContractPoster.post_data",
                new_callable=AsyncMock,
                return_value=MOCK_TX_HASH,
            ) as mock_post,
            patch(
                "flare_ai_kit.onchain.contract_poster.open", mock_open(read_data="[]")
            ),
        ):
            kit = FlareAIKit(config=app_settings)
            tx_hash = await kit.pdf_processor.contract_poster.post_data(parsed)
            logger.info(
                "posted onchain", tx_hash=tx_hash, args=mock_post.call_args[0][0]
            )

            app_state.transaction_hash = tx_hash
            app_state.status = "completed"

            return {"status": "success", "result": result, "tx_hash": tx_hash}

    except Exception as e:
        logger.exception("Error in PDF workflow", error=str(e))
        app_state.status = "error"
        raise


# --- Interface Endpoints ---


class ActionRequest(BaseModel):
    action: str
    payload: dict[str, Any] | None = None


@app.post("/action")
async def handle_action(request: Request) -> dict[str, Any]:
    """
    Endpoint called to trigger operations.
    """
    try:
        # We accept generic JSON here to be flexible with TEE payloads
        body = await request.json()
        logger.info("Received action", body=body)

        # Trigger the workflow
        # In a real scenario, we might inspect body['action'] to decide what to do.
        result = await process_pdf_workflow()
    except Exception as e:
        logger.exception("Action failed")
        raise HTTPException(status_code=500, detail={"description": str(e)}) from e
    else:
        return {"result": result}


@app.get("/state")
async def get_state(
    stateVersion: str | None = None,  # noqa: ARG001,N803
    state: str | None = None,  # noqa: ARG001
) -> dict[str, Any]:
    """
    Endpoint called for the current state.
    Returns ABI encoded state (here simulated as hex encoded JSON).
    """
    current_state = {
        "status": app_state.status,
        "tx_hash": app_state.transaction_hash,
        "last_data": app_state.last_result,
    }

    # Convert state to a hex string to mimic ABI encoding requirement generically
    state_json = json.dumps(current_state)
    state_hex = "0x" + state_json.encode("utf-8").hex()

    return {"result": state_hex}


# --- Entrypoint ---

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=EXTENSION_PORT)  # noqa: S104
