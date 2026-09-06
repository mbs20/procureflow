from decimal import Decimal
from pathlib import Path
from typing import Any

import fitz  # PyMuPDF
import pdfplumber

from procureflow.services.extractors.base import (
    BaseExtractor,
    ExtractedQuotationData,
    RawLineItem,
    RawQuotationField,
    SourceEvidence,
)
from procureflow.services.extractors.csv_extractor import clean_num, detect_currency
from procureflow.services.extractors.llm_extractor import llm_extractor
from procureflow.services.extractors.ocr_engine import ocr_engine


class PDFExtractor(BaseExtractor):
    """
    Multi-tier PDF quotation extractor:
    1. Deterministic table parsing (pdfplumber) when structured tables are present.
    2. OCR fallback (PyMuPDF / Tesseract) when pages lack sufficient native text.
    3. LLM-assisted structured interpretation referencing authoritative parser-generated evidence IDs.
    """

    DESCRIPTION_KEYWORDS = [
        "description",
        "item",
        "product",
        "part",
        "details",
        "line item",
        "material",
        "name",
    ]
    QUANTITY_KEYWORDS = ["quantity", "qty", "count", "qte", "volume"]
    UNIT_PRICE_KEYWORDS = ["unit price", "unit_price", "price", "rate", "cost", "unit cost"]

    def extract(self, file_path: Path, **kwargs: Any) -> ExtractedQuotationData:
        reference_currency = kwargs.get("reference_currency", "USD")
        doc = fitz.open(file_path)

        evidence_registry: dict[str, SourceEvidence] = {}
        tagged_chunks: list[dict[str, Any]] = []
        is_scanned_doc = False
        all_text = ""

        # Step 1: Scan and chunk pages, generating authoritative evidence for each block
        for page_idx in range(len(doc)):
            page = doc[page_idx]
            page_num = page_idx + 1

            if ocr_engine.should_run_ocr(page):
                is_scanned_doc = True
                ocr_result = ocr_engine.perform_ocr_page(page, page_num)
                page_text = ocr_result.get("text", "")
                all_text += f"\n{page_text}"

                ev_id = f"p{page_num}_ocr"
                evidence = SourceEvidence(
                    evidence_id=ev_id,
                    type="ocr_pdf",
                    page=page_num,
                    ocr_confidence=ocr_result.get("ocr_confidence", 0.85),
                    text_snippet=page_text[:120].strip() if page_text else None,
                )
                evidence_registry[ev_id] = evidence
                tagged_chunks.append(
                    {
                        "evidence_id": ev_id,
                        "page": page_num,
                        "text": page_text,
                    }
                )
            else:
                # Extract native blocks with coordinates
                blocks = page.get_text("blocks")  # [(x0, y0, x1, y1, text, block_no, block_type)]
                for b_idx, b in enumerate(blocks):
                    if b[6] == 0:  # text block
                        text = b[4].strip()
                        if not text:
                            continue
                        all_text += f"\n{text}"
                        ev_id = f"p{page_num}_b{b_idx}"
                        bbox = [round(b[0], 2), round(b[1], 2), round(b[2], 2), round(b[3], 2)]
                        evidence = SourceEvidence(
                            evidence_id=ev_id,
                            type="pdf",
                            page=page_num,
                            bbox=bbox,
                            text_snippet=text[:120].replace("\n", " "),
                        )
                        evidence_registry[ev_id] = evidence
                        tagged_chunks.append(
                            {
                                "evidence_id": ev_id,
                                "page": page_num,
                                "text": text,
                            }
                        )

        doc.close()

        # Step 2: Try deterministic table extraction via pdfplumber
        deterministic_items: list[RawLineItem] = []
        validation_warnings: list[str] = []

        try:
            with pdfplumber.open(file_path) as pdf:
                for page_idx, p in enumerate(pdf.pages):
                    page_num = page_idx + 1
                    tables = p.extract_tables()
                    for t_idx, table in enumerate(tables):
                        if not table or len(table) < 2:
                            continue

                        header = [str(c).strip().lower() if c else "" for c in table[0]]
                        desc_col = next(
                            (
                                i
                                for i, h in enumerate(header)
                                if any(k in h for k in self.DESCRIPTION_KEYWORDS)
                            ),
                            None,
                        )
                        qty_col = next(
                            (
                                i
                                for i, h in enumerate(header)
                                if any(k in h for k in self.QUANTITY_KEYWORDS)
                            ),
                            None,
                        )
                        price_col = next(
                            (
                                i
                                for i, h in enumerate(header)
                                if any(k in h for k in self.UNIT_PRICE_KEYWORDS)
                            ),
                            None,
                        )

                        if desc_col is not None and (qty_col is not None or price_col is not None):
                            # Deterministic table found!
                            for r_idx in range(1, len(table)):
                                row = table[r_idx]
                                if not row or not row[desc_col]:
                                    continue
                                desc = str(row[desc_col]).strip()
                                if desc.lower().startswith(("total", "subtotal", "terms", "note")):
                                    continue

                                qty = (
                                    clean_num(row[qty_col])
                                    if qty_col is not None and qty_col < len(row)
                                    else Decimal("1.0")
                                )
                                price = (
                                    clean_num(row[price_col])
                                    if price_col is not None and price_col < len(row)
                                    else Decimal("0.0")
                                )

                                ev_id = f"p{page_num}_t{t_idx}_r{r_idx}"
                                evidence = SourceEvidence(
                                    evidence_id=ev_id,
                                    type="pdf",
                                    page=page_num,
                                    text_snippet=f"{desc} | {qty} | {price}",
                                )
                                evidence_registry[ev_id] = evidence

                                row_warnings: list[str] = []
                                conf = Decimal("0.95")
                                if price is None or price <= Decimal("0.0"):
                                    warning = (
                                        f"Page {page_num}: Zero or negative unit price ({price})"
                                    )
                                    row_warnings.append(warning)
                                    validation_warnings.append(warning)
                                    conf = min(conf, Decimal("0.60"))
                                    price = price or Decimal("0.0")

                                deterministic_items.append(
                                    RawLineItem(
                                        description_raw=desc,
                                        quantity=qty or Decimal("1.0"),
                                        unit="units",
                                        unit_price=price,
                                        currency=detect_currency(str(row)) or reference_currency,
                                        total_price=(qty or Decimal("1.0")) * price,
                                        confidence=conf,
                                        evidence=evidence,
                                        warnings=row_warnings,
                                    )
                                )
        except Exception:
            pass

        # If deterministic table extraction succeeded, return it directly
        if deterministic_items:
            overall_conf = sum(i.confidence for i in deterministic_items) / Decimal(
                len(deterministic_items)
            )
            return ExtractedQuotationData(
                extraction_model="deterministic-pdf-table",
                extraction_version="1.0",
                overall_confidence=round(overall_conf, 4),
                line_items=deterministic_items,
                validation_warnings=validation_warnings,
                notes=f"Extracted {len(deterministic_items)} line items deterministically from PDF tables.",
            )

        # Step 3: LLM-Assisted interpretation referencing authoritative evidence chunks
        llm_result = llm_extractor.extract_from_tagged_chunks(tagged_chunks, reference_currency)

        line_items: list[RawLineItem] = []
        for item in llm_result.line_items:
            # Crucial: Resolve the returned evidence_id back to authoritative parser-generated SourceEvidence!
            matched_evidence = evidence_registry.get(item.evidence_id)
            if not matched_evidence:
                # Default to first available chunk evidence rather than inventing coordinates
                first_ev = next(
                    iter(evidence_registry.values()), SourceEvidence(type="pdf", page=1)
                )
                matched_evidence = first_ev

            qty_dec = Decimal(str(item.quantity)) if item.quantity is not None else Decimal("1.0")
            price_dec = (
                Decimal(str(item.unit_price)) if item.unit_price is not None else Decimal("0.0")
            )
            total_dec = (
                Decimal(str(item.total_price))
                if item.total_price is not None
                else (qty_dec * price_dec)
            )

            row_warnings = []
            confidence = Decimal("0.90") if not is_scanned_doc else Decimal("0.80")

            if price_dec <= Decimal("0.0"):
                warning = (
                    f"Page {matched_evidence.page or 1}: Zero or negative unit price ({price_dec})"
                )
                row_warnings.append(warning)
                validation_warnings.append(warning)
                confidence = min(confidence, Decimal("0.55"))

            if qty_dec <= Decimal("0.0"):
                warning = f"Page {matched_evidence.page or 1}: Non-positive quantity ({qty_dec})"
                row_warnings.append(warning)
                validation_warnings.append(warning)
                confidence = min(confidence, Decimal("0.55"))

            line_items.append(
                RawLineItem(
                    description_raw=item.description_raw,
                    quantity=qty_dec,
                    unit=item.unit or "units",
                    unit_price=price_dec,
                    currency=item.currency or reference_currency,
                    total_price=total_dec,
                    lead_time_days=item.lead_time_days,
                    confidence=confidence,
                    evidence=matched_evidence,
                    warnings=row_warnings,
                )
            )

        fields: list[RawQuotationField] = []
        if llm_result.payment_terms:
            first_ev = next(iter(evidence_registry.values()), SourceEvidence(type="pdf", page=1))
            fields.append(
                RawQuotationField(
                    field_name="payment_terms",
                    raw_value=llm_result.payment_terms,
                    normalised_value={"terms": llm_result.payment_terms},
                    confidence=Decimal("0.85"),
                    evidence=first_ev,
                )
            )

        overall_conf = (
            sum(i.confidence for i in line_items) / Decimal(len(line_items))
            if line_items
            else Decimal("0.0")
        )

        model_name = "ocr-assisted-pdf" if is_scanned_doc else "llm-assisted-pdf"

        return ExtractedQuotationData(
            extraction_model=model_name,
            extraction_version="1.0",
            overall_confidence=round(overall_conf, 4),
            supplier_name=llm_result.supplier_name,
            supplier_reference=llm_result.supplier_reference,
            line_items=line_items,
            fields=fields,
            notes=llm_result.notes,
            validation_warnings=validation_warnings,
        )
