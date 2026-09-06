"""Script to generate binary test fixtures for Phase 2 quotation tests."""

from pathlib import Path

import fitz  # PyMuPDF
import openpyxl

FIXTURES_DIR = Path(__file__).parent.resolve()


def generate_xlsx():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Quotation"

    # Metadata rows
    ws.append(["Supplier:", "Apex Fasteners Ltd."])
    ws.append(["Quote Ref:", "AF-2026-889"])
    ws.append(["Payment Terms:", "Net 30 days"])
    ws.append([])  # blank

    # Header
    ws.append(
        [
            "Item Description",
            "Quantity",
            "Unit",
            "Unit Price",
            "Currency",
            "Total Price",
            "Lead Time Days",
        ]
    )

    # Line items
    ws.append(["Stainless Steel Hex Bolt M10x50", 1000, "pcs", 0.75, "USD", 750.00, 14])
    ws.append(["Flange Nut M10 Zinc Plated", 1000, "pcs", 0.35, "USD", 350.00, 14])
    ws.append(["Spring Washer M10 Stainless", 2000, "pcs", 0.15, "USD", 300.00, 7])

    out_path = FIXTURES_DIR / "clean_fasteners.xlsx"
    wb.save(out_path)
    print(f"Generated {out_path}")


def generate_native_pdf():
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)  # A4

    # Add header text
    page.insert_text((50, 60), "VALVETECH INDUSTRIAL CORP", fontsize=18, fontname="helv")
    page.insert_text(
        (50, 85), "QUOTATION: VT-2026-0042 | Currency: USD", fontsize=11, fontname="helv"
    )
    page.insert_text(
        (50, 105), "Payment Terms: Net 45 Days | Validity: 30 Days", fontsize=10, fontname="helv"
    )

    # Table header
    y = 150
    page.insert_text((50, y), "Item Description", fontsize=10, fontname="helv")
    page.insert_text((280, y), "Qty", fontsize=10, fontname="helv")
    page.insert_text((340, y), "Unit Price", fontsize=10, fontname="helv")
    page.insert_text((420, y), "Total Price", fontsize=10, fontname="helv")
    page.draw_line(fitz.Point(50, y + 5), fitz.Point(520, y + 5))

    # Items
    items = [
        ("Industrial Gate Valve 2-inch ANSI 150", "10", "185.00", "1850.00"),
        ("Stainless Steel Ball Valve 1-inch 1000 WOG", "25", "48.50", "1212.50"),
        ("Cast Iron Check Valve 3-inch Flanged", "8", "135.00", "1080.00"),
    ]

    for item in items:
        y += 30
        page.insert_text((50, y), item[0], fontsize=9, fontname="helv")
        page.insert_text((285, y), item[1], fontsize=9, fontname="helv")
        page.insert_text((345, y), item[2], fontsize=9, fontname="helv")
        page.insert_text((425, y), item[3], fontsize=9, fontname="helv")

    out_path = FIXTURES_DIR / "native_valves.pdf"
    doc.save(out_path)
    doc.close()
    print(f"Generated {out_path}")


def generate_scanned_pdf():
    # First generate a native page, render to image, then insert into an image-only PDF
    temp_doc = fitz.open()
    temp_page = temp_doc.new_page(width=595, height=842)
    temp_page.insert_text((50, 80), "SCANNED INVOICE / QUOTATION", fontsize=16)
    temp_page.insert_text(
        (50, 120), "Heavy Duty Hydraulic Cylinder 50mm bore - Qty: 4 - Price: $320.00", fontsize=11
    )
    temp_page.insert_text(
        (50, 150), "High Pressure Hydraulic Hose 2m - Qty: 8 - Price: $45.00", fontsize=11
    )

    pix = temp_page.get_pixmap(dpi=150)
    img_bytes = pix.tobytes("png")
    temp_doc.close()

    # Create new PDF with ONLY the raster image (0 native text characters)
    scan_doc = fitz.open()
    scan_page = scan_doc.new_page(width=595, height=842)
    rect = fitz.Rect(0, 0, 595, 842)
    scan_page.insert_image(rect, stream=img_bytes)

    out_path = FIXTURES_DIR / "scanned_quote_image.pdf"
    scan_doc.save(out_path)
    scan_doc.close()
    print(f"Generated {out_path}")


def generate_legacy_xls():
    # Write OLE compound file binary header
    ole_header = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\x00" * 504
    out_path = FIXTURES_DIR / "legacy_quote.xls"
    with open(out_path, "wb") as f:
        f.write(ole_header)
    print(f"Generated {out_path}")


if __name__ == "__main__":
    generate_xlsx()
    generate_native_pdf()
    generate_scanned_pdf()
    generate_legacy_xls()
