from decimal import Decimal

import pytest

from procureflow.services.extractors.llm_extractor import LLMExtractor


@pytest.fixture(autouse=True)
def isolated_storage(tmp_path, monkeypatch):
    from procureflow.services.storage_service import storage_service

    monkeypatch.setattr(storage_service, "base_dir", tmp_path)
    return tmp_path


def test_generic_numbers_are_not_quotation_items():
    result = LLMExtractor()._mock_extract(
        [
            {
                "evidence_id": "p1",
                "text": "Quotation 2026-001\nPayment: 30 days, 50 percent upfront\nDimensions 200 x 400 mm\nBearing 6204 | 100 | 25.00 | 2500.00",
            }
        ]
    )
    assert len(result.line_items) == 1
    item = result.line_items[0]
    assert item.description_raw == "Bearing 6204"
    assert item.quantity == 100
    assert item.unit_price == 25
    assert item.lead_time_days is None
    assert result.supplier_name is None


@pytest.mark.asyncio
async def test_atomic_upload_rejects_without_orphans(async_client):
    response = await async_client.post(
        "/api/v1/quotations/upload",
        data={"rfq_id": "missing", "supplier_name": "Supplier"},
        files={"file": ("bad.exe", b"bad")},
    )
    assert response.status_code == 422
    assert (await async_client.get("/api/v1/quotations")).json() == []


@pytest.mark.asyncio
async def test_atomic_upload_success_and_storage_failure(async_client, monkeypatch):
    from procureflow.services.storage_service import storage_service

    rfq = await async_client.post(
        "/api/v1/rfqs",
        json={
            "title": "Upload test",
            "reference_currency": "USD",
            "line_items": [],
            "criteria": [],
        },
    )
    assert rfq.status_code == 201, rfq.text
    data = {"rfq_id": rfq.json()["id"], "supplier_name": "Supplier"}
    response = await async_client.post(
        "/api/v1/quotations/upload",
        data=data,
        files={"file": ("quote.csv", b"Description,Quantity,Price\nBolts,5,2")},
    )
    assert response.status_code == 201, response.text
    assert len(response.json()["documents"]) == 1

    def fail(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(storage_service, "save_document", fail)
    response = await async_client.post(
        "/api/v1/quotations/upload",
        data=data,
        files={"file": ("quote.csv", b"Description,Quantity,Price\nBolts,5,2")},
    )
    assert response.status_code == 500
    assert len((await async_client.get("/api/v1/quotations")).json()) == 1


@pytest.mark.asyncio
async def test_atomic_upload_oversize_has_no_container(async_client, monkeypatch):
    from procureflow.config import get_settings

    monkeypatch.setattr(get_settings(), "max_upload_size_bytes", 8)
    response = await async_client.post(
        "/api/v1/quotations/upload",
        data={"rfq_id": "missing", "supplier_name": "Supplier"},
        files={"file": ("quote.csv", b"0123456789")},
    )
    assert response.status_code == 422
    assert (await async_client.get("/api/v1/quotations")).json() == []


def test_pdf_unstructured_evidence_needs_review(tmp_path):
    import fitz

    from procureflow.services.extractors.pdf_extractor import PDFExtractor

    path = tmp_path / "generic.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text(
        (40, 50),
        "Quotation 2026-001\nPayment: 30 days, 50 percent upfront\nDimensions 200 x 400 mm\nBearing 6204 | 100 | 25.00 | 2500.00",
    )
    doc.save(path)
    doc.close()
    result = PDFExtractor().extract(path)
    assert len(result.line_items) == 1
    assert result.overall_confidence <= Decimal("0.60")
    assert result.validation_warnings
    assert result.line_items[0].evidence.page == 1
    assert result.line_items[0].evidence.bbox


def test_generic_pdf_without_items_fails_safe(tmp_path):
    import fitz

    from procureflow.services.extractors.pdf_extractor import PDFExtractor

    path = tmp_path / "generic.pdf"
    with fitz.open() as doc:
        page = doc.new_page()
        page.insert_text(
            (40, 50),
            "Quotation 2026-001\nPayment: 30 days, 50 percent upfront\nDimensions 200 x 400 mm",
        )
        doc.save(path)
    result = PDFExtractor().extract(path)
    assert result.line_items == []
    assert result.overall_confidence == 0
    assert result.validation_warnings


def test_pdf_unknown_evidence_is_not_attached_to_unrelated_source(tmp_path, monkeypatch):
    import fitz

    from procureflow.services.extractors.llm_extractor import (
        LLMExtractedLineItem,
        LLMExtractedQuotation,
    )
    from procureflow.services.extractors.pdf_extractor import PDFExtractor, llm_extractor

    path = tmp_path / "generic.pdf"
    with fitz.open() as doc:
        page = doc.new_page()
        page.insert_text(
            (40, 50),
            "Quotation 2026-001\nPayment: 30 days, 50 percent upfront\nDimensions 200 x 400 mm",
        )
        doc.save(path)
    monkeypatch.setattr(
        llm_extractor,
        "extract_from_tagged_chunks",
        lambda *args: LLMExtractedQuotation(
            line_items=[
                LLMExtractedLineItem(
                    description_raw="Invented", quantity=1, unit_price=2, evidence_id="unknown"
                )
            ]
        ),
    )
    result = PDFExtractor().extract(path)
    assert result.line_items == []
    assert result.overall_confidence == 0
    assert any("unknown source evidence" in warning for warning in result.validation_warnings)


@pytest.mark.asyncio
async def test_atomic_upload_commit_failure_repeated_then_retry(
    async_client, db_session, monkeypatch, isolated_storage
):
    from sqlalchemy import func, select

    from procureflow.models.quotation import QuotationDocument, SupplierQuotation

    rfq = await async_client.post(
        "/api/v1/rfqs",
        json={"title": "Retry test", "reference_currency": "USD", "line_items": [], "criteria": []},
    )
    assert rfq.status_code == 201, rfq.text
    data = {"rfq_id": rfq.json()["id"], "supplier_name": "Supplier"}
    real_commit = db_session.commit

    async def fail_commit():
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(db_session, "commit", fail_commit)
    for _ in range(3):
        response = await async_client.post(
            "/api/v1/quotations/upload",
            data=data,
            files={"file": ("quote.csv", b"Description,Quantity,Price\nBolts,5,2")},
        )
        assert response.status_code == 500, response.text
        assert await db_session.scalar(select(func.count()).select_from(SupplierQuotation)) == 0
        assert await db_session.scalar(select(func.count()).select_from(QuotationDocument)) == 0
        assert not list(isolated_storage.rglob("*.csv"))

    monkeypatch.setattr(db_session, "commit", real_commit)
    response = await async_client.post(
        "/api/v1/quotations/upload",
        data=data,
        files={"file": ("quote.csv", b"Description,Quantity,Price\nBolts,5,2")},
    )
    assert response.status_code == 201, response.text
    assert len(response.json()["documents"]) == 1
    assert await db_session.scalar(select(func.count()).select_from(SupplierQuotation)) == 1
    assert await db_session.scalar(select(func.count()).select_from(QuotationDocument)) == 1
    assert len(list(isolated_storage.rglob("*.csv"))) == 1


@pytest.mark.asyncio
async def test_atomic_upload_partial_file_write_failure_then_retry(
    async_client, monkeypatch, isolated_storage
):
    import builtins
    from pathlib import Path

    rfq = await async_client.post(
        "/api/v1/rfqs",
        json={
            "title": "Disk retry test",
            "reference_currency": "USD",
            "line_items": [],
            "criteria": [],
        },
    )
    assert rfq.status_code == 201, rfq.text
    data = {"rfq_id": rfq.json()["id"], "supplier_name": "Supplier"}
    real_open = builtins.open

    class PartialWrite:
        def __init__(self, path):
            self.file = real_open(path, "wb")

        def __enter__(self):
            return self

        def write(self, content):
            self.file.write(content[:4])
            raise OSError("disk full")

        def __exit__(self, *args):
            self.file.close()

    def fail_write(path, mode="r", *args, **kwargs):
        if mode == "wb" and Path(path).is_relative_to(isolated_storage):
            return PartialWrite(path)
        return real_open(path, mode, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", fail_write)
    for _ in range(3):
        response = await async_client.post(
            "/api/v1/quotations/upload",
            data=data,
            files={"file": ("quote.csv", b"Description,Quantity,Price\nBolts,5,2")},
        )
        assert response.status_code == 500, response.text
        assert (await async_client.get("/api/v1/quotations")).json() == []
        assert not list(isolated_storage.rglob("*.csv"))

    monkeypatch.setattr(builtins, "open", real_open)
    response = await async_client.post(
        "/api/v1/quotations/upload",
        data=data,
        files={"file": ("quote.csv", b"Description,Quantity,Price\nBolts,5,2")},
    )
    assert response.status_code == 201, response.text
    assert len((await async_client.get("/api/v1/quotations")).json()) == 1
    assert len(list(isolated_storage.rglob("*.csv"))) == 1
