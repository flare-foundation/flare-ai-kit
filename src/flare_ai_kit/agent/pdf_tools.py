"""PDF tools for agent."""

from __future__ import annotations

from typing import Any

import fitz  # type: ignore[reportMissingTypeStubs]
from google.adk.tools import ToolContext  # noqa: TC002

from flare_ai_kit.agent.tools import adk_tool


@adk_tool
def read_pdf_text(
    file_path: str,
    tool_context: ToolContext | None = None,
) -> dict[str, Any]:
    """
    Reads a PDF file and returns its text content page by page.

    Args:
        file_path: The local path to the PDF file to be processed.
        tool_context: The ADK tool context, used to store the result in the
            agent's state if provided.

    Returns:
        A dictionary containing the structured text from the PDF, including
        the file path, total page count, and a list of page objects, each
        with an index and its extracted text.

    """
    pages_data: list[dict[str, Any]] = []
    result: dict[str, Any] = {}
    with fitz.open(file_path) as doc:
        # The logic for handling a potential None value remains the same
        for i, page in enumerate(doc):  # type: ignore[reportArgumentType]
            txt = page.get_text("text")  # type: ignore[reportUnknownMemberType,reportUnknownMemberType]
            pages_data.append({"index": i, "text": txt})  # type: ignore[reportUnknownArgumentType]

        result = {
            "path": file_path,
            "page_count": len(doc),
            "pages": pages_data,
        }

        # If a tool_context is provided, store the result in its state
        if tool_context is not None:
            tool_context.state["last_pdf_text"] = result

    return result


read_pdf_text_tool = read_pdf_text.__wrapped__  # type: ignore[reportFunctionMemberAccess]
