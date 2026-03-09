#!/usr/bin/env python3
"""
Fill Delaware Certificate of Revival of Charter for SimplyTrust Software Inc.
Uses reportlab to create text overlay, then merges with the blank revival PDF.
Only page 3 of the PDF contains the actual form to fill.
"""

import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from pypdf import PdfReader, PdfWriter

INPUT_PDF = "renewalvoid16 (2).pdf"
OUTPUT_PDF = "revival_certificate_FILLED.pdf"

WIDTH, HEIGHT = letter  # 612 x 792


def make_overlay():
    """Create a 3-page overlay (pages 1-2 blank, page 3 has form data)."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)

    def txt(x, y_from_top, text, size=10, font="Helvetica"):
        c.setFont(font, size)
        y = HEIGHT - y_from_top
        c.drawString(x, y, str(text))

    # =========================================================
    # PAGE 1 - Cover letter (no fill needed)
    # =========================================================
    c.showPage()

    # =========================================================
    # PAGE 2 - Instructions (no fill needed)
    # =========================================================
    c.showPage()

    # =========================================================
    # PAGE 3 - The actual Certificate for Revival of Charter
    # =========================================================

    # 1. Name of the corporation
    # The blank line is after "The name of the corporation is"
    txt(310, 188, "SIMPLYTRUST SOFTWARE INC.", 10)

    # "and, if different..." line - leave blank (same name)

    # 2. Registered Office
    # Street address line
    txt(72, 282, "3500 South Dupont Highway", 10)

    # City of _____, County of _____
    txt(120, 302, "Dover", 10)
    txt(370, 302, "Kent", 10)

    # Zip Code
    txt(105, 322, "19901", 10)

    # Registered Agent name
    txt(72, 342, "Vanguard Corporate Services, Ltd.", 10)

    # 3. Date of filing original Certificate of Incorporation
    txt(165, 392, "September 19, 2024", 10)

    # 4. Pre-printed statement - no fill needed

    # 5. Date charter became void
    # "until the _____ day of _____ A.D. _____"
    txt(168, 450, "1st", 10)        # day
    txt(272, 450, "March", 10)      # month
    txt(400, 450, "2025", 10)       # year

    # Signature block
    # Name: (Print or Type)
    txt(340, 588, "Phillip Reyland", 10)

    c.showPage()

    c.save()
    buf.seek(0)
    return buf


def merge_overlay(base_path, overlay_buf, output_path):
    """Merge overlay pages onto base PDF pages."""
    base = PdfReader(base_path)
    overlay = PdfReader(overlay_buf)
    writer = PdfWriter()

    for i, base_page in enumerate(base.pages):
        if i < len(overlay.pages):
            base_page.merge_page(overlay.pages[i])
        writer.add_page(base_page)

    with open(output_path, "wb") as f:
        writer.write(f)
    print(f"Wrote filled form to: {output_path}")


if __name__ == "__main__":
    overlay_buf = make_overlay()
    merge_overlay(INPUT_PDF, overlay_buf, OUTPUT_PDF)
