"""Offline expected-versus-observed evaluation of repository synthetic fixtures.

Run from backend: python -m procureflow.scripts.evaluate_extraction
"""

from __future__ import annotations

import json
import os
import sys
from contextlib import redirect_stdout
from decimal import Decimal
from pathlib import Path


def evaluate() -> list[dict]:
    # Set before importing services: never send fixture contents to a paid provider.
    os.environ["PROCUREFLOW_LLM_PROVIDER"] = "mock"
    os.environ["PROCUREFLOW_ENV"] = "test"
    from procureflow.config import get_settings
    from procureflow.models.rfq import RFQ, RFQLineItem
    from procureflow.services.extractors.llm_extractor import settings as extractor_settings
    from procureflow.services.extractors.pipeline import ExtractionPipeline

    if extractor_settings.llm_provider != "mock":
        raise RuntimeError("Run evaluation in a fresh process with PROCUREFLOW_LLM_PROVIDER=mock.")
    if get_settings().rfq_match_threshold != 0.80:
        raise RuntimeError("Evaluation requires RFQ_MATCH_THRESHOLD=0.80.")

    fixtures = Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "quotations"
    # Ground truth is transcribed from the synthetic fixture source, not extractor output.
    cases = {
        "clean_bearings.csv": [
            ("Deep Groove Ball Bearings 6205-2RS", "100", "12.50", "USD", 14),
            ("Cylindrical Roller Bearings NU 210", "50", "34.00", "USD", 21),
            ("Tapered Roller Bearing 32008", "75", "22.80", "USD", 10),
        ],
        "clean_fasteners.xlsx": [
            ("Stainless Steel Hex Bolt M10x50", "1000", "0.75", "USD", 14),
            ("Flange Nut M10 Zinc Plated", "1000", "0.35", "USD", 14),
            ("Spring Washer M10 Stainless", "2000", "0.15", "USD", 7),
        ],
        "native_valves.pdf": [
            ("Industrial Gate Valve 2-inch ANSI 150", "10", "185.00", "USD", None),
            ("Stainless Steel Ball Valve 1-inch 1000 WOG", "25", "48.50", "USD", None),
            ("Cast Iron Check Valve 3-inch Flanged", "8", "135.00", "USD", None),
        ],
        "edge_case_warnings.csv": [
            ("Standard Hex Nut M8", "500", "0.00", "USD", 7),
            ("Heavy Duty Anchor Bolt M16", "-20", "15.50", "USD", 14),
            ("Custom Gasket Silicone", "100", None, "USD", 5),
        ],
    }

    def decimal_text(value: str | Decimal | None) -> str | None:
        return None if value is None else format(Decimal(value).normalize(), "f")

    reports = []
    pipeline = ExtractionPipeline()
    for filename, rows in cases.items():
        expected = [
            {
                "description": description,
                "quantity": decimal_text(quantity),
                "unit_price": decimal_text(price),
                "currency": currency,
                "lead_time_days": lead,
            }
            for description, quantity, price, currency, lead in rows
        ]
        # Only the first two requested items exist in the RFQ: the third must stay unmatched.
        rfq = RFQ(
            id="evaluation-rfq", title="Synthetic extraction evaluation", reference_currency="USD"
        )
        rfq.line_items = [
            RFQLineItem(
                id=f"line-{i}",
                rfq_id=rfq.id,
                position=i,
                description=row[0],
                quantity=Decimal("1"),
                unit="pcs",
            )
            for i, row in enumerate(rows[:2], 1)
        ]
        result = pipeline.process_document(fixtures / filename, rfq=rfq)
        actual = [
            {
                "description": item.description_raw,
                "quantity": decimal_text(item.quantity),
                "unit_price": decimal_text(item.unit_price),
                "currency": item.currency,
                "lead_time_days": item.lead_time_days,
            }
            for item in result.line_items
        ]
        differences = []
        if len(expected) != len(actual):
            differences.append(f"line count: expected {len(expected)}, actual {len(actual)}")
        for index, (wanted, observed) in enumerate(zip(expected, actual, strict=False), 1):
            for field, value in wanted.items():
                if value != observed[field]:
                    differences.append(
                        f"line {index} {field}: expected {value}, actual {observed[field]}"
                    )
        reports.append(
            {
                "fixture": filename,
                "expected_line_items": len(expected),
                "actual_line_items": len(actual),
                "expected": expected,
                "actual": actual,
                "differences": differences,
                "unmatched_items": sum(item.rfq_line_item_id is None for item in result.line_items),
                "warning_count": len(result.validation_warnings),
                "low_confidence_items": sum(
                    item.confidence < Decimal("0.80") for item in result.line_items
                ),
                "buyer_review_required": True,
                "review_reasons": result.validation_warnings,
            }
        )
    return reports


def main() -> None:
    import structlog

    # Keep machine-readable stdout separate from diagnostic logging.
    structlog.configure(logger_factory=structlog.PrintLoggerFactory(file=sys.stderr))
    with redirect_stdout(sys.stderr):
        results = evaluate()
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
