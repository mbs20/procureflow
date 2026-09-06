from decimal import Decimal
from pathlib import Path

import fitz

from procureflow.services.extractors.csv_extractor import CSVExtractor
from procureflow.services.extractors.excel_extractor import ExcelExtractor
from procureflow.services.extractors.ocr_engine import ocr_engine
from procureflow.services.extractors.pdf_extractor import PDFExtractor

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "quotations"


def test_csv_extractor_clean_bearings():
    extractor = CSVExtractor()
    file_path = FIXTURES_DIR / "clean_bearings.csv"
    result = extractor.extract(file_path, reference_currency="USD")

    assert result.extraction_model == "deterministic-csv"
    assert len(result.line_items) == 3

    item1 = result.line_items[0]
    assert "Ball Bearings" in item1.description_raw
    assert item1.quantity == Decimal("100")
    assert item1.unit_price == Decimal("12.50")
    assert item1.total_price == Decimal("1250.00")
    assert item1.currency == "USD"
    assert item1.lead_time_days == 14
    assert item1.confidence == Decimal("1.0")

    # Authoritative coordinates check
    assert item1.evidence is not None
    assert item1.evidence.type == "spreadsheet"
    assert item1.evidence.row_idx == 2
    assert "6205-2RS" in (item1.evidence.text_snippet or "")


def test_csv_extractor_edge_cases_and_warnings():
    extractor = CSVExtractor()
    file_path = FIXTURES_DIR / "edge_case_warnings.csv"
    result = extractor.extract(file_path, reference_currency="USD")

    assert len(result.line_items) == 3
    assert len(result.validation_warnings) > 0

    # Item 1: 0.0 unit price
    zero_price_item = result.line_items[0]
    assert zero_price_item.unit_price == Decimal("0.0")
    assert any("Zero or negative unit price" in w for w in zero_price_item.warnings)
    assert zero_price_item.confidence <= Decimal("0.60")

    # Item 2: negative quantity
    neg_qty_item = result.line_items[1]
    assert neg_qty_item.quantity == Decimal("-20")
    assert any("Non-positive quantity" in w for w in neg_qty_item.warnings)
    assert neg_qty_item.confidence <= Decimal("0.60")


def test_excel_extractor_clean_fasteners():
    extractor = ExcelExtractor()
    file_path = FIXTURES_DIR / "clean_fasteners.xlsx"
    result = extractor.extract(file_path, reference_currency="USD")

    assert result.extraction_model == "deterministic-xlsx"
    assert len(result.line_items) == 3

    item = result.line_items[0]
    assert "Hex Bolt M10x50" in item.description_raw
    assert item.quantity == Decimal("1000")
    assert item.unit_price == Decimal("0.75")
    assert item.total_price == Decimal("750.00")

    # Check cell coordinates
    assert item.evidence is not None
    assert item.evidence.type == "spreadsheet"
    assert item.evidence.sheet_name == "Quotation"
    assert item.evidence.row_idx is not None

    # Check commercial terms extraction
    terms = [f for f in result.fields if f.field_name == "payment_terms"]
    assert len(terms) == 1
    assert "Net 30 days" in (terms[0].raw_value or "")


def test_ocr_detection_heuristics():
    # Native text PDF: should NOT run OCR
    native_path = FIXTURES_DIR / "native_valves.pdf"
    doc_native = fitz.open(native_path)
    page_native = doc_native[0]
    assert ocr_engine.should_run_ocr(page_native, min_chars=50) is False
    doc_native.close()

    # Scanned image PDF: 0 native text, has image -> SHOULD run OCR
    scanned_path = FIXTURES_DIR / "scanned_quote_image.pdf"
    doc_scanned = fitz.open(scanned_path)
    page_scanned = doc_scanned[0]
    assert ocr_engine.should_run_ocr(page_scanned, min_chars=50) is True
    doc_scanned.close()


def test_pdf_extractor_native_valves():
    extractor = PDFExtractor()
    file_path = FIXTURES_DIR / "native_valves.pdf"
    result = extractor.extract(file_path, reference_currency="USD")

    assert len(result.line_items) > 0
    # Verify authoritative parser coordinates
    for item in result.line_items:
        assert item.evidence is not None
        assert item.evidence.page == 1
        assert item.evidence.type in ("pdf", "ocr_pdf")
