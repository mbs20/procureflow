from decimal import Decimal
from pathlib import Path

from procureflow.models.rfq import RFQLineItem
from procureflow.services.extractors.base import ExtractedQuotationData, RawLineItem, SourceEvidence
from procureflow.services.extractors.pipeline import ExtractionPipeline, calculate_similarity

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "quotations"


def test_similarity_calculation():
    # Exact or near matches
    assert (
        calculate_similarity("Deep Groove Ball Bearings 6205-2RS", "Ball Bearings 6205-2RS") > 0.80
    )
    # Completely different
    assert calculate_similarity("Stainless Steel Bolt M10", "Hydraulic Cylinder 50mm") < 0.30


def test_rfq_line_item_matching_threshold():
    pipeline = ExtractionPipeline()

    rfq_item1 = RFQLineItem(
        id="rfq-item-1",
        rfq_id="rfq-1",
        position=1,
        description="Deep Groove Ball Bearings 6205-2RS",
        quantity=Decimal("100"),
        unit="pcs",
    )
    rfq_item2 = RFQLineItem(
        id="rfq-item-2",
        rfq_id="rfq-1",
        position=2,
        description="Stainless Steel Hex Bolt M10x50",
        quantity=Decimal("500"),
        unit="pcs",
    )

    extracted_data = ExtractedQuotationData(
        extraction_model="test",
        extraction_version="1.0",
        overall_confidence=Decimal("0.90"),
        line_items=[
            RawLineItem(
                description_raw="Deep Groove Ball Bearings 6205-2RS",
                quantity=Decimal("100"),
                unit="pcs",
                unit_price=Decimal("12.50"),
                currency="USD",
                total_price=Decimal("1250.00"),
                evidence=SourceEvidence(type="spreadsheet", row_idx=2),
            ),
            RawLineItem(
                description_raw="Unknown Custom Titanium Bracket V3",
                quantity=Decimal("10"),
                unit="pcs",
                unit_price=Decimal("250.00"),
                currency="USD",
                total_price=Decimal("2500.00"),
                evidence=SourceEvidence(type="spreadsheet", row_idx=3),
            ),
        ],
    )

    pipeline._match_rfq_line_items(extracted_data, [rfq_item1, rfq_item2])

    # Item 1 matches high confidence
    assert extracted_data.line_items[0].rfq_line_item_id == "rfq-item-1"
    assert extracted_data.line_items[0].match_confidence >= Decimal("0.80")

    # Item 2 is an unknown custom bracket, below threshold, cautious matching leaves it None
    assert extracted_data.line_items[1].rfq_line_item_id is None
    assert len(extracted_data.line_items[1].warnings) > 0
    assert any("left unresolved for human review" in w for w in extracted_data.validation_warnings)
