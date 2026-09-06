import csv
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from procureflow.services.extractors.base import (
    BaseExtractor,
    ExtractedQuotationData,
    RawLineItem,
    RawQuotationField,
    SourceEvidence,
)


def clean_num(val: Any) -> Decimal | None:
    """Safely convert strings or numbers to Decimal, stripping currency symbols and formatting."""
    if val is None:
        return None
    s = str(val).strip()
    if not s:
        return None
    # Remove currency symbols and non-numeric characters except . and -
    s = re.sub(r"[^\d.-]", "", s)
    try:
        return Decimal(s)
    except (InvalidOperation, ValueError):
        return None


def detect_currency(raw_str: str) -> str | None:
    """Detect ISO currency from symbols or abbreviations."""
    upper = raw_str.upper()
    if "$" in raw_str or "USD" in upper:
        return "USD"
    if "€" in raw_str or "EUR" in upper:
        return "EUR"
    if "£" in raw_str or "GBP" in upper:
        return "GBP"
    if "CHF" in upper:
        return "CHF"
    if "JPY" in upper or "¥" in raw_str:
        return "JPY"
    return None


class CSVExtractor(BaseExtractor):
    """Deterministic CSV quote parser with header detection and evidence tracking."""

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
    UNIT_KEYWORDS = ["unit", "uom", "packaging", "measure"]
    UNIT_PRICE_KEYWORDS = [
        "unit price",
        "unit_price",
        "price",
        "rate",
        "cost",
        "unit cost",
        "prix unitaire",
    ]
    TOTAL_PRICE_KEYWORDS = [
        "total price",
        "total_price",
        "total",
        "extended",
        "subtotal",
        "amount",
        "total amount",
    ]
    LEAD_TIME_KEYWORDS = [
        "lead time",
        "lead_time",
        "delivery",
        "lead time (days)",
        "lead time days",
        "delivery days",
        "days",
    ]
    CURRENCY_KEYWORDS = ["currency", "curr", "devise"]

    def extract(self, file_path: Path, **kwargs: Any) -> ExtractedQuotationData:
        lines: list[list[str]] = []
        with open(file_path, encoding="utf-8-sig", errors="replace") as f:
            sample = f.read(4096)
            f.seek(0)
            try:
                dialect = csv.Sniffer().sniff(sample)
                delimiter = dialect.delimiter
            except Exception:
                delimiter = "," if "," in sample else ";"
            reader = csv.reader(f, delimiter=delimiter)
            for row in reader:
                lines.append([c.strip() for c in row])

        if not lines:
            return ExtractedQuotationData(
                extraction_model="deterministic-csv",
                overall_confidence=Decimal("0.0"),
                notes="CSV file was empty.",
                validation_warnings=["CSV file contained no readable rows."],
            )

        # 1. Locate header row and extract potential metadata from preceding rows
        header_row_idx = -1
        col_map: dict[str, int | None] = {}
        metadata_fields: list[RawQuotationField] = []
        supplier_name = None
        supplier_reference = None
        default_currency = kwargs.get("reference_currency", "USD")

        for idx, row in enumerate(lines):
            row_lower = [c.lower() for c in row]

            # Check for metadata rows before table (e.g. "Supplier: Acme Corp", "Quote Ref: Q-1234")
            row_text = " ".join(row).lower()
            if "supplier:" in row_text or "vendor:" in row_text:
                for c in row:
                    if ":" in c:
                        parts = c.split(":", 1)
                        if any(k in parts[0].lower() for k in ["supplier", "vendor"]):
                            supplier_name = parts[1].strip()
            if "quote" in row_text and (
                "ref" in row_text or "number" in row_text or "id" in row_text
            ):
                for c in row:
                    if ":" in c:
                        parts = c.split(":", 1)
                        if any(k in parts[0].lower() for k in ["quote", "ref"]):
                            supplier_reference = parts[1].strip()
            if "payment terms:" in row_text:
                for c in row:
                    if ":" in c:
                        k, v = c.split(":", 1)
                        if "payment terms" in k.lower():
                            metadata_fields.append(
                                RawQuotationField(
                                    field_name="payment_terms",
                                    raw_value=v.strip(),
                                    normalised_value={"terms": v.strip()},
                                    confidence=Decimal("0.95"),
                                    evidence=SourceEvidence(
                                        type="spreadsheet", sheet="CSV", row=idx + 1
                                    ),
                                )
                            )

            # Detect candidate header row by counting matching keywords
            matches = {
                "desc": next(
                    (
                        i
                        for i, c in enumerate(row_lower)
                        if any(k == c or k in c for k in self.DESCRIPTION_KEYWORDS)
                    ),
                    None,
                ),
                "qty": next(
                    (
                        i
                        for i, c in enumerate(row_lower)
                        if any(k == c or k in c for k in self.QUANTITY_KEYWORDS)
                    ),
                    None,
                ),
                "unit_price": next(
                    (
                        i
                        for i, c in enumerate(row_lower)
                        if any(k == c or k in c for k in self.UNIT_PRICE_KEYWORDS)
                    ),
                    None,
                ),
            }
            if matches["desc"] is not None and (
                matches["qty"] is not None or matches["unit_price"] is not None
            ):
                header_row_idx = idx
                col_map["desc"] = matches["desc"]
                if matches["qty"] is not None:
                    col_map["qty"] = matches["qty"]
                if matches["unit_price"] is not None:
                    col_map["unit_price"] = matches["unit_price"]

                # Additional optional columns
                col_map["unit"] = next(
                    (i for i, c in enumerate(row_lower) if any(k in c for k in self.UNIT_KEYWORDS)),
                    None,
                )
                col_map["total_price"] = next(
                    (
                        i
                        for i, c in enumerate(row_lower)
                        if any(k in c for k in self.TOTAL_PRICE_KEYWORDS)
                        and i != col_map.get("unit_price")
                    ),
                    None,
                )
                col_map["lead_time"] = next(
                    (
                        i
                        for i, c in enumerate(row_lower)
                        if any(k in c for k in self.LEAD_TIME_KEYWORDS)
                    ),
                    None,
                )
                col_map["currency"] = next(
                    (
                        i
                        for i, c in enumerate(row_lower)
                        if any(k == c or k in c for k in self.CURRENCY_KEYWORDS)
                    ),
                    None,
                )
                break

        if header_row_idx == -1:
            return ExtractedQuotationData(
                extraction_model="deterministic-csv",
                overall_confidence=Decimal("0.3"),
                notes="Could not unambiguously identify tabular header row in CSV.",
                validation_warnings=["Failed to locate line-item column headers in CSV."],
            )

        # 2. Extract line items from subsequent rows
        line_items: list[RawLineItem] = []
        validation_warnings: list[str] = []

        for row_idx in range(header_row_idx + 1, len(lines)):
            row = lines[row_idx]
            if not row or all(c == "" for c in row):
                continue

            desc_idx = col_map.get("desc")
            if desc_idx is None or desc_idx >= len(row) or not row[desc_idx]:
                continue
            description = row[desc_idx]

            # Stop if hitting summary rows (e.g. Total, Subtotal, Notes)
            if description.lower().startswith(
                ("total", "subtotal", "grand total", "notes", "terms")
            ):
                continue

            qty_val = (
                clean_num(row[col_map["qty"]])
                if col_map.get("qty") is not None and col_map["qty"] < len(row)
                else Decimal("1.0")
            )
            unit_price_val = (
                clean_num(row[col_map["unit_price"]])
                if col_map.get("unit_price") is not None and col_map["unit_price"] < len(row)
                else Decimal("0.0")
            )

            unit_str = (
                row[col_map["unit"]]
                if col_map.get("unit") is not None
                and col_map["unit"] < len(row)
                and row[col_map["unit"]]
                else "units"
            )

            # Currency
            item_currency = None
            if col_map.get("currency") is not None and col_map["currency"] < len(row):
                item_currency = detect_currency(row[col_map["currency"]])
            if (
                not item_currency
                and col_map.get("unit_price") is not None
                and col_map["unit_price"] < len(row)
            ):
                item_currency = detect_currency(row[col_map["unit_price"]])
            if not item_currency:
                item_currency = default_currency

            # Total Price
            total_price_val = None
            if col_map.get("total_price") is not None and col_map["total_price"] < len(row):
                total_price_val = clean_num(row[col_map["total_price"]])
            if total_price_val is None:
                total_price_val = (qty_val or Decimal("1.0")) * (unit_price_val or Decimal("0.0"))

            # Lead time
            lead_time_days = None
            if col_map.get("lead_time") is not None and col_map["lead_time"] < len(row):
                lt_clean = clean_num(row[col_map["lead_time"]])
                if lt_clean is not None:
                    lead_time_days = int(lt_clean)

            # Edge-case validations & warnings
            row_warnings: list[str] = []
            confidence = Decimal("1.0")

            if unit_price_val is None or unit_price_val <= Decimal("0.0"):
                warning_msg = f"Row {row_idx + 1}: Zero or negative unit price ({unit_price_val})"
                row_warnings.append(warning_msg)
                validation_warnings.append(warning_msg)
                confidence = min(confidence, Decimal("0.60"))
                if unit_price_val is None:
                    unit_price_val = Decimal("0.0")

            if qty_val is None or qty_val <= Decimal("0.0"):
                warning_msg = f"Row {row_idx + 1}: Non-positive quantity ({qty_val})"
                row_warnings.append(warning_msg)
                validation_warnings.append(warning_msg)
                confidence = min(confidence, Decimal("0.60"))
                if qty_val is None:
                    qty_val = Decimal("1.0")

            # Evidence
            evidence = SourceEvidence(
                type="spreadsheet",
                sheet="CSV",
                row=row_idx + 1,
                cells=[f"Col{i + 1}:{val}" for i, val in enumerate(row) if val],
                text_snippet=", ".join(str(val) for val in row if val),
            )

            line_items.append(
                RawLineItem(
                    description_raw=description,
                    quantity=qty_val,
                    unit=unit_str,
                    unit_price=unit_price_val,
                    currency=item_currency,
                    total_price=total_price_val,
                    lead_time_days=lead_time_days,
                    confidence=confidence,
                    evidence=evidence,
                    warnings=row_warnings,
                )
            )

        overall_conf = (
            sum(item.confidence for item in line_items) / Decimal(len(line_items))
            if line_items
            else Decimal("0.0")
        )

        return ExtractedQuotationData(
            extraction_model="deterministic-csv",
            extraction_version="1.0",
            overall_confidence=round(overall_conf, 4),
            supplier_name=supplier_name,
            supplier_reference=supplier_reference,
            line_items=line_items,
            fields=metadata_fields,
            validation_warnings=validation_warnings,
            notes=f"Extracted {len(line_items)} line items deterministically from CSV.",
        )
