"""
A helper script that generates a realistic PDF invoice and programmatically
finds the exact coordinates of the data for reliable testing.
"""
import fitz  # PyMuPDF
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch

FILE_PATH = "examples/sample_invoice.pdf"
INVOICE_ID = "FAI-2025-001"
ISSUE_DATE = "July 10, 2025"
AMOUNT_DUE = "1,250,000"

def create_invoice_and_get_coords() -> dict: # type: ignore
    """
    Generates the sample PDF and returns the exact coordinates of the data fields.
    """
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
    
    coords = {}
    # Find the bounding box for each data VALUE by first finding its LABEL
    
    # For Invoice ID
    label_rect = page.search_for("Invoice ID:")[0] # type: ignore
    coords["invoice_id"] = fitz.Rect(label_rect.x1 + 5, label_rect.y0 - 2, width, label_rect.y1 + 2) # type: ignore

    # For Issue Date
    label_rect = page.search_for("Issue Date:")[0] # type: ignore
    coords["issue_date"] = fitz.Rect(label_rect.x1 + 5, label_rect.y0 - 2, width, label_rect.y1 + 2) # type: ignore
    
    # For Amount Due
    label_rect = page.search_for("Total Due:")[0] # type: ignore
    coords["amount_due"] = fitz.Rect(label_rect.x1 + 5, label_rect.y0 - 2, width - 0.7 * inch, label_rect.y1 + 2) # type: ignore

    doc.close()
    print(f"✅ Found precise coordinates: {coords}")
    return coords # type: ignore

if __name__ == "__main__":
    create_invoice_and_get_coords()