import io
import zipfile
from pathlib import Path

import pytest

from procureflow.services.storage_service import StorageService, StorageValidationError


@pytest.fixture
def storage(tmp_path: Path) -> StorageService:
    return StorageService(base_dir=str(tmp_path))


def test_pdf_validation_success(storage: StorageService):
    valid_pdf_content = b"%PDF-1.7\n%\xc7\xec\x8f\xa2\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
    ext, mime = storage.validate_file("quote.pdf", valid_pdf_content)
    assert ext == ".pdf"
    assert mime == "application/pdf"


def test_pdf_validation_corrupted_header(storage: StorageService):
    invalid_content = b"NOT_A_PDF_CONTENT"
    with pytest.raises(StorageValidationError, match="header does not match valid PDF magic bytes"):
        storage.validate_file("quote.pdf", invalid_content)


def test_legacy_xls_explicit_rejection(storage: StorageService):
    ole_content = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\x00" * 100
    with pytest.raises(
        StorageValidationError, match="Legacy Excel \\(.xls\\) format is not supported for v0.1"
    ):
        storage.validate_file("legacy.xls", ole_content)


def test_xlsx_validation_success(storage: StorageService):
    # Construct minimal valid XLSX zip archive
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("[Content_Types].xml", '<?xml version="1.0"?><Types></Types>')
        zf.writestr("xl/workbook.xml", "<workbook></workbook>")
    xlsx_bytes = buf.getvalue()

    ext, mime = storage.validate_file("fasteners.xlsx", xlsx_bytes)
    assert ext == ".xlsx"
    assert mime == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def test_xlsx_validation_not_excel_zip(storage: StorageService):
    # A zip file that lacks Excel openxml files
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("some_text.txt", "hello")
    non_excel_zip = buf.getvalue()

    with pytest.raises(StorageValidationError, match="does not contain Excel OpenXML structures"):
        storage.validate_file("test.xlsx", non_excel_zip)


def test_csv_validation_success(storage: StorageService):
    csv_bytes = b"Item,Quantity,Unit Price\nWidget A,10,5.50\nWidget B,20,12.00\n"
    ext, mime = storage.validate_file("bearings.csv", csv_bytes)
    assert ext == ".csv"
    assert mime == "text/csv"


def test_csv_validation_rejects_binary_null_bytes(storage: StorageService):
    binary_csv = b"Item,Quantity\x00,Price\n"
    with pytest.raises(StorageValidationError, match="contains binary/null bytes"):
        storage.validate_file("corrupt.csv", binary_csv)


def test_csv_validation_rejects_empty_or_whitespace(storage: StorageService):
    whitespace_csv = b"   \n\t  \n  "
    with pytest.raises(StorageValidationError, match="empty or contains only whitespace"):
        storage.validate_file("empty.csv", whitespace_csv)


def test_save_document_immutability_and_hash(storage: StorageService, tmp_path: Path):
    quotation_id = "11111111-2222-3333-4444-555555555555"
    content = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"

    storage_path, file_hash, mime_type, size_bytes = storage.save_document(
        quotation_id=quotation_id,
        filename="invoice.pdf",
        content=content,
    )

    assert storage_path.endswith(".pdf")
    assert mime_type == "application/pdf"
    assert size_bytes == len(content)
    assert len(file_hash) == 64  # SHA-256 hex string

    # Verify physical file existence
    abs_path = storage.get_absolute_path(storage_path)
    assert abs_path.exists()
    assert abs_path.read_bytes() == content


def test_path_traversal_guard(storage: StorageService):
    with pytest.raises(StorageValidationError):
        storage.get_absolute_path("../../etc/passwd")
