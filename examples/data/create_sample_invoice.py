from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import fitz  # type: ignore[reportMissingTypeStubs]
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

from flare_ai_kit.ingestion.settings import (
    PDFFieldExtractionSettings,
    PDFTemplateSettings,
)

if TYPE_CHECKING:
    from collections.abc import Iterable


# ---------- Constants ----------
FILE_PATH = Path(__file__).resolve().parent / "examples" / "data" / "sample_invoice.pdf"
INVOICE_ID = "FAI-2025-001"
ISSUE_DATE = "July 10, 2025"
AMOUNT_DUE = "1,250,000"


# ---------- Types ----------
@dataclass(frozen=True)
class RectI:
    x0: int
    y0: int
    x1: int
    y1: int


# ---------- Helpers ----------
def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _round_rect(r: fitz.Rect) -> RectI:
    return RectI(*(round(v) for v in (r.x0, r.y0, r.x1, r.y1)))  # type: ignore[reportUnknownMemberType]


def _find_label_rect(page: fitz.Page, label: str) -> fitz.Rect:
    hits = page.search_for(label)  # type: ignore[reportUnknownMemberType]
    if not hits:
        msg = f"Label not found: '{label}'"
        raise ValueError(msg)
    return hits[0]  # type: ignore[reportUnknownVariableType]


def _value_rect_right_of_label(
    page: fitz.Page,
    label: str,
    right_x: float,
    pad_x: float = 5.0,
    pad_y: float = 2.0,
) -> fitz.Rect:
    lr = _find_label_rect(page, label)
    return fitz.Rect(lr.x1 + pad_x, lr.y0 - pad_y, right_x, lr.y1 + pad_y)


def _value_rect_same_line_after_label(
    page: fitz.Page, label: str, pad: float = 1.0
) -> fitz.Rect:
    """Union words on the same line to the right of the label for a tight value bbox."""
    lr = _find_label_rect(page, label)
    words: Iterable[tuple[float, float, float, float, str, int, int, int]] = (
        page.get_text("words")
    )
    y_mid = (lr.y0 + lr.y1) / 2.0
    line_words = [w for w in words if w[1] <= y_mid <= w[3]]
    right_side = [w for w in line_words if w[0] >= lr.x1 - 0.5]
    if not right_side:
        # Fallback to a region to the page right if nothing parsed
        return fitz.Rect(lr.x1 + pad, lr.y0 - pad, page.rect.x1 - pad, lr.y1 + pad)
    x0 = min(w[0] for w in right_side) - pad
    y0 = min(w[1] for w in right_side) - pad
    x1 = max(w[2] for w in right_side) + pad
    y1 = max(w[3] for w in right_side) + pad
    return fitz.Rect(x0, y0, x1, y1)


def _coords_to_template(
    template_name: str, coords: dict[str, RectI]
) -> PDFTemplateSettings:
    fields = [
        PDFFieldExtractionSettings(
            field_name=name,
            x0=r.x0,
            y0=r.y0,
            x1=r.x1,
            y1=r.y1,
            data_type="string",  # adjust per-field if needed
        )
        for name, r in coords.items()
    ]
    return PDFTemplateSettings(template_name=template_name, fields=fields)


# ---------- Main API ----------
def create_invoice_and_build_template(
    template_name: str = "generated_invoice",
) -> tuple[Path, PDFTemplateSettings]:
    """Generate the sample PDF and build PDFTemplateSettings."""
    _ensure_parent(FILE_PATH)

    # ----- Generate PDF -----
    c = canvas.Canvas(str(FILE_PATH), pagesize=letter)
    width, _ = letter

    # Header & addresses
    c.setFont("Helvetica-Bold", 16)
    c.drawString(0.5 * inch, 10 * inch, "Flare AI Systems")
    c.setFont("Helvetica", 12)
    c.drawString(0.5 * inch, 9.8 * inch, "Wuse II, Abuja, FCT, Nigeria")
    c.setFont("Helvetica-Bold", 24)
    c.drawRightString(width - 0.5 * inch, 10 * inch, "INVOICE")
    c.setFont("Helvetica-Bold", 12)
    c.drawString(0.5 * inch, 9.0 * inch, "BILL TO:")
    c.setFont("Helvetica", 12)
    c.drawString(0.5 * inch, 8.8 * inch, "Customer Corp")
    c.drawString(0.5 * inch, 8.6 * inch, "123 Innovation Drive, Maitama, Abuja")

    # Invoice details
    c.setFont("Helvetica-Bold", 12)
    c.drawString(5.0 * inch, 9.25 * inch, "Invoice ID:")
    c.drawString(5.0 * inch, 9.0 * inch, "Issue Date:")
    c.setFont("Helvetica", 12)
    c.drawString(6.0 * inch, 9.25 * inch, INVOICE_ID)
    c.drawString(6.0 * inch, 9.0 * inch, ISSUE_DATE)

    # Placeholder table
    c.line(0.5 * inch, 8.0 * inch, width - 0.5 * inch, 8.0 * inch)

    # Total
    c.setFont("Helvetica-Bold", 14)
    c.drawString(5.0 * inch, 4.0 * inch, "Total Due:")
    c.setFont("Helvetica-Bold", 14)
    c.drawRightString(width - 0.7 * inch, 4.0 * inch, AMOUNT_DUE)

    c.save()
    print(f"✅ Created {FILE_PATH}")

    # ----- Discover coordinates & build template -----
    with fitz.open(str(FILE_PATH)) as doc:
        page = doc[0]
        page_right = page.rect.x1

        coords: dict[str, RectI] = {
            "invoice_id": _round_rect(
                _value_rect_same_line_after_label(page, "Invoice ID:")
            ),
            "issue_date": _round_rect(
                _value_rect_same_line_after_label(page, "Issue Date:")
            ),
            "amount_due": _round_rect(
                _value_rect_right_of_label(
                    page, "Total Due:", right_x=page_right - 0.7 * inch
                )
            ),
        }

    template = _coords_to_template(template_name, coords)
    print(f"✅ Built PDF template: {template.template_name}")
    return FILE_PATH, template


if __name__ == "__main__":
    _, t = create_invoice_and_build_template()
    print(t.model_dump())
