from decimal import Decimal
from pathlib import Path
from typing import Any

import openpyxl

from procureflow.services.extractors.base import (
    BaseExtractor,
    ExtractedQuotationData,
    RawLineItem,
    RawQuotationField,
    SourceEvidence,
)
from procureflow.services.extractors.csv_extractor import clean_num, detect_currency


class ExcelExtractor(BaseExtractor):
    """Deterministic Excel (.xlsx) quotation extractor using openpyxl with cell and row citations."""

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
        default_currency = kwargs.get("reference_currency", "USD")

        try:
            wb = openpyxl.load_workbook(file_path, data_only=True)
        except Exception as e:
            return ExtractedQuotationData(
                extraction_model="deterministic-xlsx",
                overall_confidence=Decimal("0.0"),
                notes=f"Failed to load Excel workbook: {e}",
                validation_warnings=[f"Excel parsing error: {e}"],
            )

        line_items: list[RawLineItem] = []
        metadata_fields: list[RawQuotationField] = []
        validation_warnings: list[str] = []
        supplier_name = None
        supplier_reference = None

        # Iterate through sheets (prioritize sheets with 'quote', 'bid', 'offer', or active)
        sheets_to_process = wb.sheetnames
        for sheet_name in sheets_to_process:
            ws = wb[sheet_name]
            rows_data: list[list[tuple[str, Any]]] = []  # [(coordinate, value)]
            for row in ws.iter_rows(values_only=False):
                row_cells = [(cell.coordinate, cell.value) for cell in row]
                if any(val is not None and str(val).strip() != "" for _, val in row_cells):
                    rows_data.append(row_cells)

            if not rows_data:
                continue

            # Check for header row
            header_idx = -1
            col_map: dict[str, int | None] = {}

            for idx, r in enumerate(rows_data):
                row_vals = [str(val).strip().lower() if val is not None else "" for _, val in r]

                # Check metadata cells before table
                for coord, val in r:
                    if val is None:
                        continue
                    s = str(val).strip()
                    s_lower = s.lower()
                    curr_c_idx = [c[0] for c in r].index(coord)
                    adj_val = (
                        str(r[curr_c_idx + 1][1]).strip()
                        if curr_c_idx + 1 < len(r) and r[curr_c_idx + 1][1] is not None
                        else ""
                    )

                    if ":" in s:
                        k, v = s.split(":", 1)
                        k_lower = k.lower()
                        val_str = v.strip() or adj_val
                        if (
                            any(term in k_lower for term in ["supplier", "vendor"])
                            and not supplier_name
                        ):
                            supplier_name = val_str
                        elif (
                            any(term in k_lower for term in ["quote", "ref", "quotation no"])
                            and not supplier_reference
                        ):
                            supplier_reference = val_str
                        elif "payment term" in k_lower:
                            metadata_fields.append(
                                RawQuotationField(
                                    field_name="payment_terms",
                                    raw_value=val_str,
                                    normalised_value={"terms": val_str},
                                    confidence=Decimal("0.95"),
                                    evidence=SourceEvidence(
                                        type="spreadsheet",
                                        sheet=sheet_name,
                                        cells=[coord],
                                    ),
                                )
                            )
                    elif "payment term" in s_lower and adj_val:
                        metadata_fields.append(
                            RawQuotationField(
                                field_name="payment_terms",
                                raw_value=adj_val,
                                normalised_value={"terms": adj_val},
                                confidence=Decimal("0.95"),
                                evidence=SourceEvidence(
                                    type="spreadsheet",
                                    sheet=sheet_name,
                                    cells=[coord],
                                ),
                            )
                        )

                # Match table header candidates
                matches = {
                    "desc": next(
                        (
                            i
                            for i, c in enumerate(row_vals)
                            if any(k == c or k in c for k in self.DESCRIPTION_KEYWORDS)
                        ),
                        None,
                    ),
                    "qty": next(
                        (
                            i
                            for i, c in enumerate(row_vals)
                            if any(k == c or k in c for k in self.QUANTITY_KEYWORDS)
                        ),
                        None,
                    ),
                    "unit_price": next(
                        (
                            i
                            for i, c in enumerate(row_vals)
                            if any(k == c or k in c for k in self.UNIT_PRICE_KEYWORDS)
                        ),
                        None,
                    ),
                }

                if matches["desc"] is not None and (
                    matches["qty"] is not None or matches["unit_price"] is not None
                ):
                    header_idx = idx
                    col_map["desc"] = matches["desc"]
                    if matches["qty"] is not None:
                        col_map["qty"] = matches["qty"]
                    if matches["unit_price"] is not None:
                        col_map["unit_price"] = matches["unit_price"]

                    col_map["unit"] = next(
                        (
                            i
                            for i, c in enumerate(row_vals)
                            if any(k in c for k in self.UNIT_KEYWORDS)
                        ),
                        None,
                    )
                    col_map["total_price"] = next(
                        (
                            i
                            for i, c in enumerate(row_vals)
                            if any(k in c for k in self.TOTAL_PRICE_KEYWORDS)
                            and i != col_map.get("unit_price")
                        ),
                        None,
                    )
                    col_map["lead_time"] = next(
                        (
                            i
                            for i, c in enumerate(row_vals)
                            if any(k in c for k in self.LEAD_TIME_KEYWORDS)
                        ),
                        None,
                    )
                    col_map["currency"] = next(
                        (
                            i
                            for i, c in enumerate(row_vals)
                            if any(k == c or k in c for k in self.CURRENCY_KEYWORDS)
                        ),
                        None,
                    )
                    break

            if header_idx == -1:
                continue

            # Extract line items for this sheet
            for row_idx in range(header_idx + 1, len(rows_data)):
                r = rows_data[row_idx]
                desc_idx = col_map.get("desc")
                if desc_idx is None or desc_idx >= len(r):
                    continue

                desc_cell = r[desc_idx]
                if desc_cell[1] is None or str(desc_cell[1]).strip() == "":
                    continue

                description = str(desc_cell[1]).strip()
                if description.lower().startswith(("total", "subtotal", "grand total", "notes")):
                    continue

                qty_cell = (
                    r[col_map["qty"]]
                    if col_map.get("qty") is not None and col_map["qty"] < len(r)
                    else None
                )
                qty_val = clean_num(qty_cell[1]) if qty_cell else Decimal("1.0")

                up_cell = (
                    r[col_map["unit_price"]]
                    if col_map.get("unit_price") is not None and col_map["unit_price"] < len(r)
                    else None
                )
                unit_price_val = clean_num(up_cell[1]) if up_cell else Decimal("0.0")

                unit_cell = (
                    r[col_map["unit"]]
                    if col_map.get("unit") is not None and col_map["unit"] < len(r)
                    else None
                )
                unit_str = str(unit_cell[1]).strip() if unit_cell and unit_cell[1] else "units"

                # Currency
                item_currency = None
                if col_map.get("currency") is not None and col_map["currency"] < len(r):
                    curr_cell = r[col_map["currency"]]
                    if curr_cell[1]:
                        item_currency = detect_currency(str(curr_cell[1]))
                if not item_currency and up_cell and up_cell[1]:
                    item_currency = detect_currency(str(up_cell[1]))
                if not item_currency:
                    item_currency = default_currency

                # Total price
                total_price_val = None
                if col_map.get("total_price") is not None and col_map["total_price"] < len(r):
                    tp_cell = r[col_map["total_price"]]
                    if tp_cell:
                        total_price_val = clean_num(tp_cell[1])
                if total_price_val is None:
                    total_price_val = (qty_val or Decimal("1.0")) * (
                        unit_price_val or Decimal("0.0")
                    )

                # Lead time
                lead_time_days = None
                if col_map.get("lead_time") is not None and col_map["lead_time"] < len(r):
                    lt_cell = r[col_map["lead_time"]]
                    if lt_cell and lt_cell[1]:
                        lt_clean = clean_num(lt_cell[1])
                        if lt_clean is not None:
                            lead_time_days = int(lt_clean)

                # Validation warnings & confidence
                row_warnings: list[str] = []
                confidence = Decimal("1.0")

                if unit_price_val is None or unit_price_val <= Decimal("0.0"):
                    msg = f"Sheet '{sheet_name}' Row {row_idx + 1}: Zero or negative unit price ({unit_price_val})"
                    row_warnings.append(msg)
                    validation_warnings.append(msg)
                    confidence = min(confidence, Decimal("0.60"))
                    if unit_price_val is None:
                        unit_price_val = Decimal("0.0")

                if qty_val is None or qty_val <= Decimal("0.0"):
                    msg = (
                        f"Sheet '{sheet_name}' Row {row_idx + 1}: Non-positive quantity ({qty_val})"
                    )
                    row_warnings.append(msg)
                    validation_warnings.append(msg)
                    confidence = min(confidence, Decimal("0.60"))
                    if qty_val is None:
                        qty_val = Decimal("1.0")

                # Cells list for authoritative evidence citation
                used_cells = [
                    c[0]
                    for c in [desc_cell, qty_cell, up_cell, unit_cell]
                    if c and c[1] is not None
                ]
                evidence = SourceEvidence(
                    type="spreadsheet",
                    sheet=sheet_name,
                    row=row_idx + 1,
                    cells=used_cells,
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

        wb.close()

        overall_conf = (
            sum(item.confidence for item in line_items) / Decimal(len(line_items))
            if line_items
            else Decimal("0.0")
        )

        return ExtractedQuotationData(
            extraction_model="deterministic-xlsx",
            extraction_version="1.0",
            overall_confidence=round(overall_conf, 4),
            supplier_name=supplier_name,
            supplier_reference=supplier_reference,
            line_items=line_items,
            fields=metadata_fields,
            validation_warnings=validation_warnings,
            notes=f"Extracted {len(line_items)} line items deterministically from Excel workbook.",
        )
