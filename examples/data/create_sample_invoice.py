"""Generate a sample invoice PDF and find coordinates for testing."""

import fitz  # type: ignore[reportMissingTypeStubs]
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

FILE_PATH = "examples/data/sample_invoice.pdf"
INVOICE_ID = "FAI-2025-001"
ISSUE_DATE = "July 10, 2025"
AMOUNT_DUE = "1,250,000"


def create_invoice_and_get_coords() -> dict[str, fitz.Rect]:
    """Generates the sample PDF and returns the exact coordinates of the data fields."""
    c = canvas.Canvas(FILE_PATH, pagesize=letter)
    width, _ = letter

    # --- Header & Addresses ---
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

    # --- Invoice Details (Labels and Values) ---
    c.setFont("Helvetica-Bold", 12)
    c.drawString(5.0 * inch, 9.25 * inch, "Invoice ID:")
    c.drawString(5.0 * inch, 9.0 * inch, "Issue Date:")
    c.setFont("Helvetica", 12)
    c.drawString(6.0 * inch, 9.25 * inch, INVOICE_ID)
    c.drawString(6.0 * inch, 9.0 * inch, ISSUE_DATE)

    # --- Table ---
    c.line(0.5 * inch, 8.0 * inch, width - 0.5 * inch, 8.0 * inch)
    # ... more table drawing ...

    # --- Total ---
    c.setFont("Helvetica-Bold", 14)
    c.drawString(5.0 * inch, 4.0 * inch, "Total Due:")
    c.setFont("Helvetica-Bold", 14)
    c.drawRightString(width - 0.7 * inch, 4.0 * inch, AMOUNT_DUE)

    c.save()
    print(f"✅ Successfully created '{FILE_PATH}'")

    # --- Programmatically Find Coordinates ---
    doc = fitz.open(FILE_PATH)
    page = doc[0]

    coords: dict[str, fitz.Rect] = {}
    # Find the bounding box for each data VALUE by first finding its LABEL

    # For Invoice ID
    label_rect = page.search_for("Invoice ID:")[0]  # type: ignore[reportUnknownMemberType]
    coords["invoice_id"] = fitz.Rect(
        label_rect.x1 + 5,  # type: ignore[reportArgumentType]
        label_rect.y0 - 2,  # type: ignore[reportArgumentType]
        width,
        label_rect.y1 + 2,  # type: ignore[reportArgumentType]
    )

    # For Issue Date
    label_rect = page.search_for("Issue Date:")[0]  # type: ignore[reportUnknownMemberType]
    coords["issue_date"] = fitz.Rect(
        label_rect.x1 + 5,  # type: ignore[reportArgumentType]
        label_rect.y0 - 2,  # type: ignore[reportArgumentType]
        width,
        label_rect.y1 + 2,  # type: ignore[reportArgumentType]
    )

    # For Amount Due
    label_rect = page.search_for("Total Due:")[0]  # type: ignore[reportUnknownMemberType]
    coords["amount_due"] = fitz.Rect(
        label_rect.x1 + 5,  # type: ignore[reportArgumentType]
        label_rect.y0 - 2,  # type: ignore[reportArgumentType]
        width - 0.7 * inch,
        label_rect.y1 + 2,  # type: ignore[reportArgumentType]
    )

    doc.close()
    print(f"✅ Found precise coordinates: {coords}")
    return coords


if __name__ == "__main__":
    create_invoice_and_get_coords()
