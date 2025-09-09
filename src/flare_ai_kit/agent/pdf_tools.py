"""PDF tools for agent."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import fitz  # type: ignore[reportMissingTypeStubs]
from google.adk.tools import FunctionTool, ToolContext


@dataclass(frozen=True)
class PDFPage:
    """Class representing a single PDF page."""

    index: int
    text: str


@dataclass(frozen=True)
class PDFTextPayload:
    """Class representing a single PDF."""

    path: str
    page_count: int
    pages: list[PDFPage]


def read_pdf_text(
    file_path: str,
    tool_context: ToolContext | None = None,
) -> dict[str, Any]:
    """Return plain text for each page so the agent can parse it."""
    pages: list[PDFPage] = []
    with fitz.open(file_path) as doc:
        # The logic for handling a potential None value remains the same
        stop = len(doc)
        for i in range(stop):
            page = doc[i]
            txt = page.get_text("text")  # type: ignore[reportUnknownMemberType,reportUnknownMemberType]
            pages.append(PDFPage(index=i, text=txt))  # type: ignore[reportUnknownArgumentType]

        payload = PDFTextPayload(
            path=file_path,
            page_count=stop,
            pages=pages,
        )

    result = {
        "path": payload.path,
        "page_count": payload.page_count,
        "pages": [{"index": p.index, "text": p.text} for p in payload.pages],
    }
    if tool_context is not None:
        tool_context.state["last_pdf_text"] = result
    return result


read_pdf_text_tool = FunctionTool(read_pdf_text)
