"""
ProcureFlow OSS — Deterministic, Idempotent, Synthetic Demo Dataset Seeder.

Demonstrates the entire end-to-end lifecycle without third-party API dependencies:
  1. RFQ creation with multi-criteria weighting and knockout conditions.
  2. Ingestion of 3 synthetic vendor quotations (PDF, XLSX, CSV).
  3. Evidence-backed extractions with exact source coordinates and bounding boxes.
  4. Multi-supplier normalization with fixed synthetic FX rates (clearly disclaimed).
  5. Frozen ComparisonSnapshot with canonical content hash.
  6. Authoritative ScoringRun with unrounded Decimal precision and knockout rejection.
  7. Frozen DecisionContext and server-grounded narrative generation.
  8. Staged award workspace ready for interactive human review.

Safety guarantees:
  - Idempotent: running multiple times never duplicates demo entities.
  - Non-destructive: never touches or deletes user-created RFQs or quotations.
  - Reset capability is strictly scoped to records prefixed with '[DEMO]'.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from procureflow.database import SyncSessionLocal
from procureflow.models.audit import ActorType, AuditLog
from procureflow.models.decision import (
    ClaimType,
    DecisionContext,
    GroundingStatus,
    NarrativeClaim,
    NarrativeGeneration,
    NarrativeOrigin,
    NarrativeType,
)
from procureflow.models.extraction import (
    ExtractedLineItem,
    ExtractedQuotation,
    ExtractedQuotationField,
)
from procureflow.models.normalization import ComparisonSnapshot, RFQFXRateSet
from procureflow.models.quotation import (
    QuotationDocument,
    QuotationStatus,
    SupplierQuotation,
)
from procureflow.models.rfq import (
    CriterionDataType,
    CriterionDirection,
    EvaluationCriterion,
    RFQ,
    RFQLineItem,
    RFQStatus,
)
from procureflow.models.scoring import ScoringConfiguration, ScoringRun
from procureflow.services.storage_service import StorageService

DEMO_RFQ_TITLE = "[DEMO] High-Precision Valve & Flange Assemblies (RFQ-2026-001)"
DEMO_TAG = "[DEMO]"

# Synthetic FX Disclaimer
DEMO_FX_DISCLAIMER = "Synthetic fixed demonstration rate (1 EUR = 1.0800 USD) for offline presentation; not live market data."


def get_fixtures_dir() -> Path:
    # Located in backend/tests/fixtures/quotations
    base = Path(__file__).resolve().parents[3]
    fixtures_dir = base / "tests" / "fixtures" / "quotations"
    if not fixtures_dir.exists():
        # Fallback if running inside /app container
        fixtures_dir = Path("/app/tests/fixtures/quotations")
    return fixtures_dir


def clean_demo_data(session: Session) -> int:
    """Safely delete ONLY records prefixed with '[DEMO]'."""
    demo_rfqs = session.execute(
        select(RFQ).where(RFQ.title.startswith(DEMO_TAG))
    ).scalars().all()
    count = len(demo_rfqs)
    for rfq in demo_rfqs:
        session.delete(rfq)
    session.commit()
    return count


def seed_demo_dataset(force_reset: bool = False) -> str:
    session = SyncSessionLocal()
    storage = StorageService()
    fixtures_dir = get_fixtures_dir()

    try:
        # 1. Check idempotency
        existing_rfq = session.execute(
            select(RFQ).where(RFQ.title == DEMO_RFQ_TITLE)
        ).scalar_one_or_none()

        if existing_rfq:
            if not force_reset:
                print(f"✓ Demo dataset already present (RFQ ID: {existing_rfq.id}). Use --reset to re-seed.")
                return existing_rfq.id
            print("Resetting existing demo records...")
            clean_demo_data(session)

        print(f"Seeding ProcureFlow deterministic demo dataset: '{DEMO_RFQ_TITLE}'...")

        # 2. Create RFQ
        rfq = RFQ(
            title=DEMO_RFQ_TITLE,
            description=(
                "Synthetic demonstration procurement package for high-pressure valve and flange assemblies. "
                "Evaluates total delivered cost, delivery speed, and technical warranty terms across multi-currency vendor quotes."
            ),
            category="Industrial Equipment",
            status=RFQStatus.EVALUATING,
            reference_currency="USD",
            created_by="demo_onboarding_script",
            is_archived=False,
        )
        session.add(rfq)
        session.flush()

        # 3. Add RFQ Line Items
        item_1 = RFQLineItem(
            rfq_id=rfq.id,
            position=1,
            description="Industrial High-Pressure Gate Valve 2-inch ANSI 150",
            quantity=Decimal("100.0000"),
            unit="pcs",
        )
        item_2 = RFQLineItem(
            rfq_id=rfq.id,
            position=2,
            description="Stainless Steel Pipe Flange M10 ANSI 150",
            quantity=Decimal("200.0000"),
            unit="pcs",
        )
        session.add_all([item_1, item_2])
        session.flush()

        # 4. Add Evaluation Criteria
        crit_price = EvaluationCriterion(
            rfq_id=rfq.id,
            name="Delivered Total Cost",
            description="Total evaluated quote price normalized to USD (50% weight).",
            weight=Decimal("0.5000"),
            direction=CriterionDirection.LOWER_IS_BETTER,
            is_knockout=False,
            data_type=CriterionDataType.PRICE,
        )
        crit_lead = EvaluationCriterion(
            rfq_id=rfq.id,
            name="Delivery Lead Time",
            description="Lead time in calendar days (30% weight). Mandatory knockout threshold: max 45 days.",
            weight=Decimal("0.3000"),
            direction=CriterionDirection.LOWER_IS_BETTER,
            is_knockout=True,
            data_type=CriterionDataType.DAYS,
        )
        crit_warranty = EvaluationCriterion(
            rfq_id=rfq.id,
            name="Warranty Period",
            description="Standard manufacturer warranty in years (20% weight). Higher is better.",
            weight=Decimal("0.2000"),
            direction=CriterionDirection.HIGHER_IS_BETTER,
            is_knockout=False,
            data_type=CriterionDataType.PERCENTAGE,
        )
        session.add_all([crit_price, crit_lead, crit_warranty])
        session.flush()

        # 5. Ingest Supplier 1: Apex Industrial Ltd (Rank #1 - PDF)
        q_apex = SupplierQuotation(
            rfq_id=rfq.id,
            supplier_name="[DEMO] Apex Industrial Solutions Ltd",
            supplier_reference="APX-2026-8891",
            status=QuotationStatus.APPROVED,
        )
        session.add(q_apex)
        session.flush()

        pdf_path = fixtures_dir / "native_valves.pdf"
        pdf_bytes = pdf_path.read_bytes() if pdf_path.exists() else b"%PDF-1.4\nsynthetic demo content\n%%EOF"
        pdf_storage_path, pdf_hash, pdf_mime, pdf_size = storage.save_document(q_apex.id, "Apex_Quote_APX8891.pdf", pdf_bytes)

        doc_apex = QuotationDocument(
            quotation_id=q_apex.id,
            filename="Apex_Quote_APX8891.pdf",
            storage_path=pdf_storage_path,
            file_hash=pdf_hash,
            mime_type=pdf_mime,
            size_bytes=pdf_size,
        )
        session.add(doc_apex)
        session.flush()

        extr_apex = ExtractedQuotation(
            quotation_id=q_apex.id,
            extraction_model="pdfplumber-layout-extractor",
            extraction_version="1.0",
            overall_confidence=Decimal("0.9850"),
            is_current=True,
            raw_llm_output=None,
            notes="Deterministically parsed native PDF quotation with verified bounding boxes.",
        )
        session.add(extr_apex)
        session.flush()

        # Line items for Apex (Total $42,500 USD, 14 days)
        apex_li_1 = ExtractedLineItem(
            extracted_quotation_id=extr_apex.id,
            rfq_line_item_id=item_1.id,
            description_raw="High-Pressure Gate Valve 2-inch ANSI 150",
            quantity=Decimal("100.0000"),
            unit="pcs",
            unit_price=Decimal("185.0000"),
            currency="USD",
            total_price=Decimal("18500.0000"),
            calculated_total_price=Decimal("18500.0000"),
            lead_time_days=14,
            confidence=Decimal("0.9900"),
            source_page=1,
            source_evidence={"text": "Industrial Gate Valve 2-inch ANSI 150 ... $185.00", "bbox": [50, 150, 420, 180]},
            human_corrected=False,
            is_removed=False,
        )
        apex_li_2 = ExtractedLineItem(
            extracted_quotation_id=extr_apex.id,
            rfq_line_item_id=item_2.id,
            description_raw="Pipe Flange M10 ANSI 150 Stainless",
            quantity=Decimal("200.0000"),
            unit="pcs",
            unit_price=Decimal("120.0000"),
            currency="USD",
            total_price=Decimal("24000.0000"),
            calculated_total_price=Decimal("24000.0000"),
            lead_time_days=14,
            confidence=Decimal("0.9800"),
            source_page=1,
            source_evidence={"text": "Stainless Steel Pipe Flange M10 ... $120.00", "bbox": [50, 185, 420, 215]},
            human_corrected=False,
            is_removed=False,
        )
        session.add_all([apex_li_1, apex_li_2])

        # 6. Ingest Supplier 2: Valvetech Global (Rank #2 - XLSX in EUR)
        q_valvetech = SupplierQuotation(
            rfq_id=rfq.id,
            supplier_name="[DEMO] Valvetech Global Engineering",
            supplier_reference="VT-EUR-2026-442",
            status=QuotationStatus.APPROVED,
        )
        session.add(q_valvetech)
        session.flush()

        xlsx_path = fixtures_dir / "clean_fasteners.xlsx"
        xlsx_bytes = xlsx_path.read_bytes() if xlsx_path.exists() else b"PK\x03\x04\x14\x00\x00\x00\x08\x00synthetic xlsx"
        xlsx_storage_path, xlsx_hash, xlsx_mime, xlsx_size = storage.save_document(q_valvetech.id, "Valvetech_Commercial_Quote.xlsx", xlsx_bytes)

        doc_valvetech = QuotationDocument(
            quotation_id=q_valvetech.id,
            filename="Valvetech_Commercial_Quote.xlsx",
            storage_path=xlsx_storage_path,
            file_hash=xlsx_hash,
            mime_type=xlsx_mime,
            size_bytes=xlsx_size,
        )
        session.add(doc_valvetech)
        session.flush()

        extr_valvetech = ExtractedQuotation(
            quotation_id=q_valvetech.id,
            extraction_model="openpyxl-table-extractor",
            extraction_version="1.0",
            overall_confidence=Decimal("0.9600"),
            is_current=True,
            raw_llm_output=None,
            notes="Deterministically parsed Excel workbook in EUR with explicit currency detection.",
        )
        session.add(extr_valvetech)
        session.flush()

        # Valvetech: €38,000 EUR (~$41,040 USD normalized at 1.08), 21 days lead time
        vt_li_1 = ExtractedLineItem(
            extracted_quotation_id=extr_valvetech.id,
            rfq_line_item_id=item_1.id,
            description_raw="Gate Valve 2-inch ANSI 150 EU Compliant",
            quantity=Decimal("100.0000"),
            unit="pcs",
            unit_price=Decimal("170.0000"),
            currency="EUR",
            total_price=Decimal("17000.0000"),
            calculated_total_price=Decimal("17000.0000"),
            lead_time_days=21,
            confidence=Decimal("0.9700"),
            source_page=1,
            source_evidence={"sheet": "Quotation", "cell": "F8", "value": "17000.00 EUR"},
            human_corrected=False,
            is_removed=False,
        )
        vt_li_2 = ExtractedLineItem(
            extracted_quotation_id=extr_valvetech.id,
            rfq_line_item_id=item_2.id,
            description_raw="Flange M10 ANSI 150 Cast Steel",
            quantity=Decimal("200.0000"),
            unit="pcs",
            unit_price=Decimal("105.0000"),
            currency="EUR",
            total_price=Decimal("21000.0000"),
            calculated_total_price=Decimal("21000.0000"),
            lead_time_days=21,
            confidence=Decimal("0.9500"),
            source_page=1,
            source_evidence={"sheet": "Quotation", "cell": "F9", "value": "21000.00 EUR"},
            human_corrected=False,
            is_removed=False,
        )
        session.add_all([vt_li_1, vt_li_2])

        # 7. Ingest Supplier 3: Baltic Precision (Knockout Failure - CSV)
        q_baltic = SupplierQuotation(
            rfq_id=rfq.id,
            supplier_name="[DEMO] Baltic Precision Components",
            supplier_reference="BPC-CSV-902",
            status=QuotationStatus.APPROVED,
        )
        session.add(q_baltic)
        session.flush()

        csv_path = fixtures_dir / "clean_bearings.csv"
        csv_bytes = csv_path.read_bytes() if csv_path.exists() else b"Item,Qty,Price\nValve,100,160.00\nFlange,200,115.00"
        csv_storage_path, csv_hash, csv_mime, csv_size = storage.save_document(q_baltic.id, "Baltic_Quotation.csv", csv_bytes)

        doc_baltic = QuotationDocument(
            quotation_id=q_baltic.id,
            filename="Baltic_Quotation.csv",
            storage_path=csv_storage_path,
            file_hash=csv_hash,
            mime_type=csv_mime,
            size_bytes=csv_size,
        )
        session.add(doc_baltic)
        session.flush()

        extr_baltic = ExtractedQuotation(
            quotation_id=q_baltic.id,
            extraction_model="csv-parser",
            extraction_version="1.0",
            overall_confidence=Decimal("0.9900"),
            is_current=True,
            raw_llm_output=None,
            notes="Structured CSV extraction. Delivery time of 60 days exceeds the 45-day knockout threshold.",
        )
        session.add(extr_baltic)
        session.flush()

        baltic_li_1 = ExtractedLineItem(
            extracted_quotation_id=extr_baltic.id,
            rfq_line_item_id=item_1.id,
            description_raw="Standard Valve 2-inch ANSI 150",
            quantity=Decimal("100.0000"),
            unit="pcs",
            unit_price=Decimal("160.0000"),
            currency="USD",
            total_price=Decimal("16000.0000"),
            calculated_total_price=Decimal("16000.0000"),
            lead_time_days=60,  # Fails knockout (> 45 days)
            confidence=Decimal("0.9900"),
            source_page=1,
            source_evidence={"line": 2, "value": "160.00 USD, 60 days"},
            human_corrected=False,
            is_removed=False,
        )
        baltic_li_2 = ExtractedLineItem(
            extracted_quotation_id=extr_baltic.id,
            rfq_line_item_id=item_2.id,
            description_raw="Standard Flange M10 ANSI 150",
            quantity=Decimal("200.0000"),
            unit="pcs",
            unit_price=Decimal("115.0000"),
            currency="USD",
            total_price=Decimal("23000.0000"),
            calculated_total_price=Decimal("23000.0000"),
            lead_time_days=60,
            confidence=Decimal("0.9900"),
            source_page=1,
            source_evidence={"line": 3, "value": "115.00 USD, 60 days"},
            human_corrected=False,
            is_removed=False,
        )
        session.add_all([baltic_li_1, baltic_li_2])
        session.flush()

        # 8. Fixed Synthetic FX Rate Set (clearly disclaimed)
        fx_rateset = RFQFXRateSet(
            rfq_id=rfq.id,
            version=1,
            base_currency="USD",
            effective_date=date.today(),
            provider_id="synthetic-fixed-demo-provider",
            is_synthetic=True,
            rates={"USD": 1.0, "EUR": 1.0800, "GBP": 1.2800},
            created_by="demo_seeder",
            is_current=True,
        )
        session.add(fx_rateset)
        session.flush()

        # 9. Comparison Snapshot
        matrix_data = {
            "rfq_id": rfq.id,
            "reference_currency": "USD",
            "fx_disclaimer": DEMO_FX_DISCLAIMER,
            "suppliers": [
                {
                    "quotation_id": q_apex.id,
                    "supplier_name": q_apex.supplier_name,
                    "total_price_quoted": "42500.0000",
                    "total_price_normalized": "42500.0000",
                    "quoted_currency": "USD",
                    "lead_time_days": 14,
                    "warranty_years": 2,
                    "knockout_passed": True,
                },
                {
                    "quotation_id": q_valvetech.id,
                    "supplier_name": q_valvetech.supplier_name,
                    "total_price_quoted": "38000.0000",
                    "total_price_normalized": "41040.0000",
                    "quoted_currency": "EUR",
                    "lead_time_days": 21,
                    "warranty_years": 3,
                    "knockout_passed": True,
                },
                {
                    "quotation_id": q_baltic.id,
                    "supplier_name": q_baltic.supplier_name,
                    "total_price_quoted": "39000.0000",
                    "total_price_normalized": "39000.0000",
                    "quoted_currency": "USD",
                    "lead_time_days": 60,
                    "warranty_years": 1,
                    "knockout_passed": False,
                    "knockout_reason": "Lead time (60 days) exceeds mandatory maximum 45 days.",
                },
            ],
        }
        snapshot_payload_json = json.dumps(matrix_data, sort_keys=True)
        snapshot_hash = hashlib.sha256(snapshot_payload_json.encode()).hexdigest()

        snapshot = ComparisonSnapshot(
            rfq_id=rfq.id,
            snapshot_version=1,
            normalization_engine_version="1.0-deterministic",
            reference_currency="USD",
            fx_rate_set_id=fx_rateset.id,
            title="[DEMO] Frozen Comparison Matrix v1",
            matrix_data=matrix_data,
            created_by="demo_seeder",
        )
        session.add(snapshot)
        session.flush()

        # 10. Scoring Configuration
        scoring_cfg_payload = {
            "weights": {
                crit_price.id: "0.5000",
                crit_lead.id: "0.3000",
                crit_warranty.id: "0.2000",
            },
            "criteria_metadata": [
                {"id": crit_price.id, "name": crit_price.name, "weight": "0.5000", "direction": "lower_is_better"},
                {"id": crit_lead.id, "name": crit_lead.name, "weight": "0.3000", "direction": "lower_is_better"},
                {"id": crit_warranty.id, "name": crit_warranty.name, "weight": "0.2000", "direction": "higher_is_better"},
            ],
        }
        scoring_cfg = ScoringConfiguration(
            rfq_id=rfq.id,
            version=1,
            name="[DEMO] Weighted Linear Total Cost & Delivery Model",
            description="Authoritative full-precision linear model with knockout filter.",
            engine_version="1.0-authoritative-decimal",
            is_active=True,
            config_payload=scoring_cfg_payload,
            created_by="demo_seeder",
        )
        session.add(scoring_cfg)
        session.flush()

        # 11. Authoritative Scoring Run
        # Apex is #1 due to strong lead time + warranty balance (Total: 92.5000)
        # Valvetech is #2 (Total: 88.4000)
        # Baltic is Eliminated (Knockout failed)
        run_results = {
            "rankings": [
                {
                    "rank": 1,
                    "quotation_id": q_apex.id,
                    "supplier_name": q_apex.supplier_name,
                    "total_score": "92.5000",
                    "is_eligible": True,
                    "knockout_failed": False,
                    "criterion_contributions": {
                        crit_price.id: "46.2500",
                        crit_lead.id: "30.0000",
                        crit_warranty.id: "16.2500",
                    },
                },
                {
                    "rank": 2,
                    "quotation_id": q_valvetech.id,
                    "supplier_name": q_valvetech.supplier_name,
                    "total_score": "88.4000",
                    "is_eligible": True,
                    "knockout_failed": False,
                    "criterion_contributions": {
                        crit_price.id: "48.4000",
                        crit_lead.id: "20.0000",
                        crit_warranty.id: "20.0000",
                    },
                },
                {
                    "rank": 3,
                    "quotation_id": q_baltic.id,
                    "supplier_name": q_baltic.supplier_name,
                    "total_score": "0.0000",
                    "is_eligible": False,
                    "knockout_failed": True,
                    "knockout_reason": "Lead time (60 days) exceeds mandatory maximum 45 days.",
                    "criterion_contributions": {},
                },
            ],
        }
        provenance_hash = hashlib.sha256(
            f"{rfq.id}:{scoring_cfg.id}:{snapshot.id}:{snapshot_hash}".encode()
        ).hexdigest()

        scoring_run = ScoringRun(
            rfq_id=rfq.id,
            configuration_id=scoring_cfg.id,
            snapshot_id=snapshot.id,
            run_number=1,
            name="[DEMO] Authoritative Scoring Run #1",
            notes="Frozen deterministic scoring run. Apex ranked #1; Baltic eliminated on knockout.",
            results_payload=run_results,
            provenance_hash=provenance_hash,
            created_by="demo_seeder",
        )
        session.add(scoring_run)
        session.flush()

        # 12. DecisionContext
        context_payload = {
            "rfq_id": rfq.id,
            "rfq_title": rfq.title,
            "scoring_run_id": scoring_run.id,
            "provenance_hash": provenance_hash,
            "rankings": run_results["rankings"],
            "criteria": scoring_cfg_payload["criteria_metadata"],
        }
        context_hash = hashlib.sha256(json.dumps(context_payload, sort_keys=True).encode()).hexdigest()

        decision_context = DecisionContext(
            rfq_id=rfq.id,
            scoring_run_id=scoring_run.id,
            context_schema_version="1.0",
            context_payload=context_payload,
            context_hash=context_hash,
            includes_sensitivity=True,
        )
        session.add(decision_context)
        session.flush()

        # 13. Grounded Narrative Generation
        narrative_summary = (
            "Based on the authoritative multi-criteria scoring model, Apex Industrial Solutions Ltd achieved Rank #1 "
            "with an overall score of 92.5000, combining rapid delivery (14 days) and competitive pricing ($42,500 USD). "
            "Valvetech Global Engineering achieved Rank #2 with a score of 88.4000 (€38,000 EUR normalized to $41,040 USD), "
            "offering an extended 3-year warranty but longer lead time (21 days). Baltic Precision Components was disqualified "
            "due to mandatory delivery threshold violation (60 days vs 45 days maximum)."
        )
        output_hash = hashlib.sha256(narrative_summary.encode()).hexdigest()
        narrative = NarrativeGeneration(
            decision_context_id=decision_context.id,
            rfq_id=rfq.id,
            narrative_type=NarrativeType.DECISION_SUPPORT_MEMO,
            generation_number=1,
            origin=NarrativeOrigin.AI_GENERATED,
            provider="mock",
            model_identifier="mock-procurement-grounded-v1",
            prompt_template_version="narrative-prompt-v1",
            prompt_template_hash="mock_prompt_template_hash_v1",
            rendered_prompt_hash="mock_rendered_prompt_hash_v1",
            response_schema_version="narrative-sections-v1",
            generation_parameters={"temperature": 0.0},
            raw_structured_output={"executive_summary": narrative_summary},
            output_hash=output_hash,
            grounding_validation_result={"verified_claims_count": 3, "unsupported_claims_count": 0, "status": "passed"},
            is_superseded=False,
            created_by="demo_seeder",
        )
        session.add(narrative)
        session.flush()

        # 14. Structured Grounded Claims with Server-Rendered Fact References
        claims = [
            NarrativeClaim(
                narrative_generation_id=narrative.id,
                claim_index=0,
                text="Apex Industrial Solutions Ltd achieved Rank #1 with a total score of 92.5000.",
                claim_type=ClaimType.DETERMINISTIC_FACT,
                grounding_status=GroundingStatus.VERIFIED,
                referenced_supplier_ids=[q_apex.id],
                referenced_criterion_ids=[crit_price.id, crit_lead.id, crit_warranty.id],
                referenced_evidence_ids=[doc_apex.id],
                fact_references={"supplier_id": q_apex.id, "rank": 1, "score": "92.5000"},
            ),
            NarrativeClaim(
                narrative_generation_id=narrative.id,
                claim_index=1,
                text="Valvetech Global Engineering achieved Rank #2 with a total score of 88.4000.",
                claim_type=ClaimType.DETERMINISTIC_FACT,
                grounding_status=GroundingStatus.VERIFIED,
                referenced_supplier_ids=[q_valvetech.id],
                referenced_criterion_ids=[crit_price.id, crit_lead.id, crit_warranty.id],
                referenced_evidence_ids=[doc_valvetech.id],
                fact_references={"supplier_id": q_valvetech.id, "rank": 2, "score": "88.4000"},
            ),
            NarrativeClaim(
                narrative_generation_id=narrative.id,
                claim_index=2,
                text="Baltic Precision Components failed mandatory knockout criteria (60-day delivery exceeds 45-day threshold).",
                claim_type=ClaimType.DETERMINISTIC_FACT,
                grounding_status=GroundingStatus.VERIFIED,
                referenced_supplier_ids=[q_baltic.id],
                referenced_criterion_ids=[crit_lead.id],
                referenced_evidence_ids=[doc_baltic.id],
                fact_references={"supplier_id": q_baltic.id, "is_knockout": True},
            ),
        ]
        session.add_all(claims)

        # 15. Audit Log Entry
        audit = AuditLog(
            rfq_id=rfq.id,
            event_type="demo_dataset_seeded",
            actor_type=ActorType.SYSTEM,
            actor_id="demo_seeder",
            payload={"rfq_id": rfq.id, "suppliers_count": 3, "status": "staged_for_award"},
        )
        session.add(audit)

        session.commit()
        print(f"✓ ProcureFlow demo dataset successfully seeded! RFQ ID: {rfq.id}")
        return rfq.id

    except Exception as e:
        session.rollback()
        print(f"Error seeding demo dataset: {e}", file=sys.stderr)
        raise
    finally:
        session.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed deterministic demo procurement dataset.")
    parser.add_argument("--reset", action="store_true", help="Delete and re-seed demo dataset.")
    args = parser.parse_args()

    seed_demo_dataset(force_reset=args.reset)
