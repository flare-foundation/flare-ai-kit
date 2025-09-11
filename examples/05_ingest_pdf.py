from __future__ import annotations

import asyncio
import json
import os
import re
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, mock_open, patch

from data.create_sample_invoice import create_invoice_and_build_template
from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from flare_ai_kit import FlareAIKit
from flare_ai_kit.agent.pdf_tools import read_pdf_text_tool
from flare_ai_kit.config import AppSettings
from flare_ai_kit.ingestion.settings import (
    IngestionSettings,
    OnchainContractSettings,
    PDFIngestionSettings,
    PDFTemplateSettings,
)

MOCK_TX_HASH = "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"


def _prompt(pdf: Path, template: PDFTemplateSettings, max_pages: int | None) -> str:
    """Build the prompt from the template."""
    return (
        "Parse this PDF using tools and return ONLY JSON per the template.\n"
        f"PDF_PATH: {pdf}\nMAX_PAGES: {max_pages or 'ALL'}\n\n"
        "TEMPLATE_JSON:\n```json\n" + json.dumps(template.model_dump()) + "\n```\n\n"
        "- Call read_pdf_text(file_path=PDF_PATH, max_pages=MAX_PAGES).\n"
        "- Extract each field in TEMPLATE_JSON.fields.\n"
        "- Reply with a single JSON object (no markdown)."
    )


def _json_from(text: str) -> dict[str, Any]:
    """Extract JSON from agent return text."""
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        fence = re.search(
            r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL | re.IGNORECASE
        )
        if fence:
            return json.loads(fence.group(1))
        blob = re.search(r"\{.*\}", text, re.DOTALL)
        if blob:
            return json.loads(blob.group(0))
        msg = f"Agent response is not valid JSON:\n{text}"
        raise RuntimeError(msg) from e


async def parse_pdf_to_template_json(
    agent: Agent,
    pdf: str | Path,
    template: PDFTemplateSettings,
    max_pages: int | None = None,
) -> dict[str, Any]:
    """Setup in-memory ADK agent, give it the PDF, template and prompt."""
    pdf = Path(pdf)
    svc = InMemorySessionService()
    await svc.create_session(app_name="app", user_id="u", session_id="s")
    runner = Runner(agent=agent, app_name="app", session_service=svc)

    msg = types.Content(
        role="user", parts=[types.Part(text=_prompt(pdf, template, max_pages))]
    )
    final_text = None
    print(f"Calling {agent.name} using model: {agent.model}")
    async for ev in runner.run_async(user_id="u", session_id="s", new_message=msg):
        if ev.is_final_response() and ev.content and ev.content.parts:
            final_text = ev.content.parts[0].text
            break
    if not final_text:
        msg = "Agent produced no response."
        raise RuntimeError(msg)
    return _json_from(final_text)


async def main() -> None:
    # Create PDF and save it
    pdf_path, template = create_invoice_and_build_template("generated_invoice")

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

    # Create ADK agent with tool access.
    pdf_agent_instruction = (
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
    )

    # Construct the Agent instance using the imported tool and settings
    pdf_agent = Agent(
        name="flare_pdf_agent",
        model=app_settings.agent.gemini_model,
        tools=[read_pdf_text_tool],
        instruction=pdf_agent_instruction,
        generate_content_config=types.GenerateContentConfig(
            temperature=0.0, top_k=1, top_p=0.3, candidate_count=1
        ),
    )

    # Mock onchain contract posting
    with (
        patch(
            "flare_ai_kit.onchain.contract_poster.ContractPoster.post_data",
            new_callable=AsyncMock,
            return_value=MOCK_TX_HASH,
        ) as mock_post,
        patch("flare_ai_kit.onchain.contract_poster.open", mock_open(read_data="[]")),
    ):
        kit = FlareAIKit(config=app_settings)
        tx_hash = await kit.pdf_processor.ingest_and_post(
            file_path=str(pdf_path), template_name=template.template_name
        )
        print("✅ on-chain tx:", tx_hash)
        print("📄 extracted:", mock_post.call_args[0][0])

    # Agent PDF parsing
    structured = await parse_pdf_to_template_json(
        pdf_agent, pdf_path, template, max_pages=1
    )
    print("🧩 agent JSON:", json.dumps(structured, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
