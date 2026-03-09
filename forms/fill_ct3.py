#!/usr/bin/env python3
"""
Fill NY Form CT-3 (2025 tax year) for SimplyTrust Software Inc.
Uses reportlab to create text overlay, then merges with blank CT-3 PDF.
Coordinates calibrated from grid overlay on ct3_2026.pdf.
"""

import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from pypdf import PdfReader, PdfWriter

INPUT_PDF = "ct3_2026.pdf"
OUTPUT_PDF = "ct3_2025_FILLED.pdf"

WIDTH, HEIGHT = letter  # 612 x 792


def make_overlay():
    """Create a multi-page overlay with all the form data."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)

    def txt(x, y_from_top, text, size=9, right_align=False, font="Helvetica"):
        c.setFont(font, size)
        y = HEIGHT - y_from_top
        if right_align:
            c.drawRightString(x, y, str(text))
        else:
            c.drawString(x, y, str(text))

    def mark_x(x, y_from_top, size=10):
        txt(x, y_from_top, "X", size, font="Helvetica-Bold")

    # =========================================================
    # PAGE 1 - Header Information
    # =========================================================

    # Tax period: beginning / ending (y~178 from grid)
    txt(440, 180, "01/01/2025", 7)
    txt(555, 180, "12/31/2025", 7)

    # EIN (y~200 from grid, below label at y~190)
    txt(62, 200, "33-1284676", 9)

    # Business telephone (y~200, right side)
    txt(370, 206, "917", 8)
    txt(393, 206, "657-5994", 8)

    # Legal name (y~220 from grid)
    txt(62, 220, "SIMPLYTRUST SOFTWARE INC.", 9)

    # Mailing address (y~245) / State of incorporation
    txt(62, 245, "245 Dekalb Ave, #3", 9)
    txt(480, 245, "Delaware", 8)

    # Number and street (y~268) / Date of incorporation
    txt(62, 268, "245 Dekalb Ave, #3", 9)
    txt(480, 268, "09/19/2024", 8)

    # City / State / ZIP (y~290)
    txt(62, 290, "Brooklyn", 9)
    txt(175, 290, "NY", 9)
    txt(265, 290, "11205", 9)

    # Principal business activity / NAICS (y~318)
    txt(62, 318, "Software Development", 9)
    txt(370, 318, "511210", 9)

    # Box A - Payment amount: $25 (y~383)
    txt(575, 383, "25", 9, right_align=True)

    # Box B - MTA surcharge: Yes (y~412, checkbox square after "Yes" text)
    mark_x(524, 412)

    # Box D - Interest in partnerships: No (y~468, checkbox after "No" text)
    mark_x(564, 468)

    # Third-party designee: No (y~497, checkbox before "No" text)
    mark_x(133, 497)

    # Authorized person - Printed name (y~548) / Official title
    txt(100, 548, "Phillip Reyland", 9)
    txt(510, 548, "CEO", 9)

    # Telephone number (y~568, phone field at x~430)
    txt(430, 568, "(917) 657-5994", 7)

    c.showPage()

    # =========================================================
    # PAGE 2 - Part 1, General Corporate Information
    # =========================================================

    # Section A - Leave all blank (none apply)

    # Section B - New York State Information
    # Line 1: Number of NYS employees = 0 (y~305)
    txt(575, 305, "0", 9, right_align=True)
    # Line 2: Wages paid = $0 (y~318)
    txt(575, 318, "0", 9, right_align=True)
    # Line 3: Number of business establishments = 1 (y~333)
    txt(575, 333, "1", 9, right_align=True)

    # Section C - Filing Information
    # Line 1: Federal return filed - mark X next to 1120 (y~472)
    mark_x(90, 472)

    # Line 2a: Tax due from most recent NY return = $0 (y~555)
    txt(575, 555, "0", 9, right_align=True)

    # Line 4: Tax credit forms filed = 0 (y~635)
    txt(575, 635, "0", 9, right_align=True)

    c.showPage()

    # =========================================================
    # PAGE 3 - Part 2, Calculation of balance due or overpayment
    # Coordinates from fine 5pt grid calibration
    # =========================================================

    R = 575  # right margin for value column

    # Largest of three tax bases
    txt(R, 107, "0", 9, right_align=True)       # 1a: Business income base tax
    txt(R, 122, "0", 9, right_align=True)        # 1b: Capital base tax
    txt(250, 133, "0", 8)                        # 1c: NY receipts box
    txt(R, 144, "25", 9, right_align=True)       # 1c: Fixed dollar minimum tax
    txt(R, 156, "25", 9, right_align=True)       # 2: Tax due
    txt(R, 170, "0", 9, right_align=True)        # 3: Tax credits used
    txt(R, 184, "25", 9, right_align=True)       # 4: Tax due after credits

    # Penalties and interest (lines 5-7 have inline boxes)
    txt(385, 214, "0", 9, right_align=True)      # 5: Estimated tax penalty
    txt(385, 230, "0", 9, right_align=True)      # 6: Interest on late payment
    txt(385, 244, "0", 9, right_align=True)      # 7: Late filing penalties
    txt(R, 254, "0", 9, right_align=True)        # 8: Total penalties

    # Voluntary gifts/contributions
    txt(R, 274, "0", 9, right_align=True)        # 9: Voluntary gifts
    txt(R, 288, "25", 9, right_align=True)       # 10: Total amount due

    # Prepayments (lines 11-17 have inline boxes)
    txt(395, 312, "0", 9, right_align=True)      # 11: MFI from CT-300
    txt(395, 326, "0", 9, right_align=True)      # 12: Second installment
    txt(395, 337, "0", 9, right_align=True)      # 13: Third installment
    txt(395, 348, "0", 9, right_align=True)      # 14: Fourth installment
    txt(395, 360, "0", 9, right_align=True)      # 15: Payment with extension
    txt(395, 372, "0", 9, right_align=True)      # 16: Overpayment from prior
    txt(395, 384, "0", 9, right_align=True)      # 17: Overpayment from CT-3-M
    txt(R, 395, "0", 9, right_align=True)        # 18: Total prepayments

    # Payment due or overpayment
    txt(R, 418, "0", 9, right_align=True)        # 19a: Underpayment
    txt(R, 432, "0", 9, right_align=True)        # 19b: Additional for 2026 MFI
    txt(R, 445, "25", 9, right_align=True)       # 19c: Balance due
    txt(R, 455, "0", 9, right_align=True)        # 20a: Excess prepayments
    txt(R, 467, "0", 9, right_align=True)        # 20b: Previously credited
    txt(R, 479, "0", 9, right_align=True)        # 20c: Overpayment
    txt(R, 489, "0", 9, right_align=True)        # 21: Credited to next period
    txt(R, 500, "0", 9, right_align=True)        # 22: Balance of overpayment
    txt(R, 512, "0", 9, right_align=True)        # 23: Credited to CT-3-M
    txt(R, 524, "0", 9, right_align=True)        # 24: To be refunded
    txt(R, 537, "0", 9, right_align=True)        # 25: Unused tax credits
    txt(R, 550, "0", 9, right_align=True)        # 26: Refundable credits

    c.showPage()

    # =========================================================
    # PAGE 4 - Part 3, Calculation of tax on business income base
    # Coordinates from fine 5pt grid calibration
    # =========================================================

    txt(R, 98, "-180,383", 9, right_align=True)  # 1: FTI
    txt(R, 110, "0", 9, right_align=True)        # 2: Additions to FTI
    txt(R, 120, "-180,383", 9, right_align=True) # 3: Add lines 1 and 2
    txt(R, 130, "0", 9, right_align=True)        # 4: Subtractions from FTI
    txt(R, 140, "-180,383", 9, right_align=True) # 5: Subtract line 4 from 3
    txt(R, 155, "0", 9, right_align=True)        # 6: Subtraction modification
    txt(R, 168, "-180,383", 9, right_align=True) # 7: ENI
    txt(R, 180, "0", 9, right_align=True)        # 8: Investment/exempt income
    txt(R, 190, "-180,383", 9, right_align=True) # 9: Subtract line 8 from 7
    txt(R, 210, "0", 9, right_align=True)        # 10: Excess interest deductions
    txt(R, 225, "-180,383", 9, right_align=True) # 11: Business income
    txt(R, 250, "0", 9, right_align=True)        # 12: Addback of investment income
    txt(R, 265, "-180,383", 9, right_align=True) # 13: Business income after addback
    txt(R, 278, "1.000000", 9, right_align=True) # 14: Apportionment factor
    txt(R, 290, "-180,383", 9, right_align=True) # 15: Apportioned business income
    txt(R, 300, "0", 9, right_align=True)        # 16: Prior NOL conversion
    txt(R, 310, "-180,383", 9, right_align=True) # 17: Subtract line 16 from 15
    txt(R, 325, "0", 9, right_align=True)        # 18: NOL deduction
    txt(R, 340, "0", 9, right_align=True)        # 19: Business income base
    txt(R, 360, "0", 9, right_align=True)        # 20: Business income base tax

    c.showPage()

    # =========================================================
    # PAGE 5 - Part 4 + Part 5
    # =========================================================

    # Part 4 - Calculation of tax on capital base
    # All values $0, minimal assets
    # Line 1: Total assets (y~120) - Col A / Col B
    txt(380, 122, "0", 9, right_align=True)
    txt(500, 122, "0", 9, right_align=True)
    # Line 2 (y~138)
    txt(380, 140, "0", 9, right_align=True)
    txt(500, 140, "0", 9, right_align=True)
    # Line 3 (y~152)
    txt(380, 154, "0", 9, right_align=True)
    txt(500, 154, "0", 9, right_align=True)
    # Line 4 (y~175)
    txt(380, 177, "0", 9, right_align=True)
    txt(500, 177, "0", 9, right_align=True)
    # Line 5 (y~192) - Col A / Col B / Col C (average)
    txt(380, 194, "0", 9, right_align=True)
    txt(500, 194, "0", 9, right_align=True)
    txt(575, 194, "0", 9, right_align=True)
    # Line 6 (y~205)
    txt(380, 207, "0", 9, right_align=True)
    txt(500, 207, "0", 9, right_align=True)
    txt(575, 207, "0", 9, right_align=True)
    # Line 7: Total net assets = $0 (y~218)
    txt(575, 220, "0", 9, right_align=True)
    # Line 8: Investment capital = $0 (y~232)
    txt(575, 234, "0", 9, right_align=True)
    # Line 9: Business capital = $0 (y~245)
    txt(575, 247, "0", 9, right_align=True)
    # Line 10: Addback = $0 (y~255)
    txt(575, 257, "0", 9, right_align=True)
    # Line 11: Total business capital = $0 (y~265)
    txt(575, 267, "0", 9, right_align=True)
    # Line 12: Business apportionment factor = 1.000000 (y~278)
    txt(575, 280, "1.000000", 9, right_align=True)
    # Line 13: Apportioned business capital = $0 (y~290)
    txt(575, 292, "0", 9, right_align=True)
    # Line 15: Capital base tax = $0 (y~318)
    txt(575, 320, "0", 9, right_align=True)

    # Part 5 - Investment capital: all $0, leave blank

    c.showPage()

    # =========================================================
    # PAGE 6 - Part 6, Business apportionment factor
    # =========================================================

    # Mark X in "no receipts" box (y~100, right side)
    mark_x(580, 100)

    # All receipt lines are $0 - leave blank since we checked "no receipts"

    c.showPage()

    # =========================================================
    # PAGE 7 - Part 6 continued
    # =========================================================

    # Line 57: Col A = $0, Col B = $0 (y~565)
    txt(530, 567, "0", 9, right_align=True)
    txt(580, 567, "0", 9, right_align=True)

    # Line 58: Apportionment factor = 1.000000 (y~600)
    txt(580, 600, "1.000000", 9, right_align=True)

    c.showPage()

    # PAGE 8 - blank
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
