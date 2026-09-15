"""
Phase 6 — Unit tests for NarrativeService.

Covers: DecisionContext determinism, mock narrative generation, claim-level grounding,
hallucinated supplier detection, unsupported quantitative claims, provider failure,
regeneration append-only, human revision history, prompt versioning, superseded semantics,
and architectural boundary (narrative cannot invoke award).
"""

from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from unittest.mock import patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from procureflow.models.decision import (
    AwardStatus,
    DecisionContext,
    NarrativeGeneration,
    NarrativeOrigin,
    NarrativeRevision,
)
from procureflow.models.normalization import ComparisonSnapshot
from procureflow.models.rfq import RFQ, RFQStatus
from procureflow.models.scoring import ScoringConfiguration, ScoringRun
from procureflow.schemas.decision import (
    NarrativeGenerationRequest,
    NarrativeRevisionCreate,
    NarrativeType,
)
from procureflow.services.narrative_service import (
    NarrativeProviderError,
    NarrativeService,
    _canonical_json,
    _sha256,
    build_decision_context_payload,
    generate_mock_narrative,
    validate_claims_grounding,
)


# ---------------------------------------------------------------------------
# FIXTURES
# ---------------------------------------------------------------------------

SCORING_RUN_RESULTS = {
    "rfq_id": "rfq-1",
    "snapshot_id": "snap-1",
    "snapshot_version": 1,
    "comparison_snapshot_hash": "abc123snaphash",
    "configuration_id": "cfg-1",
    "configuration_version": 1,
    "configuration_name": "Default Config",
    "scoring_configuration_hash": "def456cfghash",
    "engine_version": "1.0.0",
    "engine_policy": {"ranking_policy": "standard_competitive_1224"},
    "provenance_hash": "provhash789",
    "evaluated_at": "2026-01-01T00:00:00",
    "eligible_suppliers_count": 3,
    "knockout_suppliers_count": 1,
    "suppliers": [
        {
            "quotation_id": "q-alpha",
            "supplier_name": "Alpha Supplies",
            "eligibility_status": "eligible",
            "knockout_reasons": [],
            "total_score": "92.5432",
            "exact_total_score": "92.5432109876",
            "rank": 1,
            "criteria_breakdown": [
                {
                    "criterion_id": "crit-price",
                    "criterion_name": "Price",
                    "raw_value": 10000,
                    "exact_raw_value": "10000.00",
                    "direction": "lower_is_better",
                    "normalized_score": "85.0000",
                    "exact_normalized_score": "85.00000000",
                    "weight": "0.6000",
                    "weighted_contribution": "51.0000",
                    "exact_weighted_contribution": "51.00000000",
                    "formula_audit": "min_max normalization",
                    "is_knockout_applied": False,
                    "source_path": "suppliers[q-alpha].normalized_comparable_total",
                    "notes": None,
                },
                {
                    "criterion_id": "crit-quality",
                    "criterion_name": "Quality Score",
                    "raw_value": 95,
                    "exact_raw_value": "95",
                    "direction": "higher_is_better",
                    "normalized_score": "95.0000",
                    "exact_normalized_score": "95.00000000",
                    "weight": "0.4000",
                    "weighted_contribution": "38.0000",
                    "exact_weighted_contribution": "38.00000000",
                    "formula_audit": "min_max normalization",
                    "is_knockout_applied": False,
                    "source_path": "suppliers[q-alpha].quality_score",
                    "notes": None,
                },
            ],
        },
        {
            "quotation_id": "q-beta",
            "supplier_name": "Beta Corp",
            "eligibility_status": "eligible",
            "knockout_reasons": [],
            "total_score": "87.4321",
            "exact_total_score": "87.4321098765",
            "rank": 2,
            "criteria_breakdown": [
                {
                    "criterion_id": "crit-price",
                    "criterion_name": "Price",
                    "raw_value": 12000,
                    "exact_raw_value": "12000.00",
                    "direction": "lower_is_better",
                    "normalized_score": "70.0000",
                    "exact_normalized_score": "70.00000000",
                    "weight": "0.6000",
                    "weighted_contribution": "42.0000",
                    "exact_weighted_contribution": "42.00000000",
                    "formula_audit": "min_max normalization",
                    "is_knockout_applied": False,
                    "source_path": "suppliers[q-beta].normalized_comparable_total",
                    "notes": None,
                },
                {
                    "criterion_id": "crit-quality",
                    "criterion_name": "Quality Score",
                    "raw_value": 98,
                    "exact_raw_value": "98",
                    "direction": "higher_is_better",
                    "normalized_score": "100.0000",
                    "exact_normalized_score": "100.00000000",
                    "weight": "0.4000",
                    "weighted_contribution": "40.0000",
                    "exact_weighted_contribution": "40.00000000",
                    "formula_audit": "min_max normalization",
                    "is_knockout_applied": False,
                    "source_path": "suppliers[q-beta].quality_score",
                    "notes": None,
                },
            ],
        },
        {
            "quotation_id": "q-gamma",
            "supplier_name": "Gamma Ltd",
            "eligibility_status": "eligible",
            "knockout_reasons": [],
            "total_score": "75.1111",
            "exact_total_score": "75.1111222233",
            "rank": 3,
            "criteria_breakdown": [],
        },
        {
            "quotation_id": "q-delta",
            "supplier_name": "Delta Industries",
            "eligibility_status": "knockout_failed",
            "knockout_reasons": ["Value 50000 exceeds maximum knockout threshold 30000 on 'Price'"],
            "total_score": "0.0000",
            "exact_total_score": "0.0000",
            "rank": None,
            "criteria_breakdown": [],
        },
    ],
}


async def _seed_scoring_data(db: AsyncSession) -> tuple[str, str, str, str]:
    """Seed RFQ, snapshot, config, and scoring run for narrative tests."""
    rfq = RFQ(
        id="rfq-1",
        title="Industrial Bearings RFQ 2026",
        description="Annual procurement of industrial ball bearings",
        category="MRO",
        reference_currency="USD",
        status=RFQStatus.EVALUATING,
    )
    db.add(rfq)

    snapshot = ComparisonSnapshot(
        id="snap-1",
        rfq_id="rfq-1",
        snapshot_version=1,
        reference_currency="USD",
        matrix_data={"suppliers": []},
    )
    db.add(snapshot)

    config = ScoringConfiguration(
        id="cfg-1",
        rfq_id="rfq-1",
        version=1,
        name="Default Config",
        engine_version="1.0.0",
        config_payload={"criteria": [], "normalization_method": "min_max"},
    )
    db.add(config)

    run = ScoringRun(
        id="run-1",
        rfq_id="rfq-1",
        configuration_id="cfg-1",
        snapshot_id="snap-1",
        run_number=1,
        name="Scoring Run #1",
        results_payload=SCORING_RUN_RESULTS,
        provenance_hash="provhash789",
    )
    db.add(run)

    await db.flush()
    return "rfq-1", "snap-1", "cfg-1", "run-1"


# ---------------------------------------------------------------------------
# TESTS
# ---------------------------------------------------------------------------


class TestDecisionContextDeterminism:
    """Test 1: DecisionContext hash is deterministic for identical inputs."""

    async def test_identical_inputs_produce_identical_hash(self, db_session: AsyncSession):
        rfq_id, snap_id, cfg_id, run_id = await _seed_scoring_data(db_session)

        svc = NarrativeService()
        ctx1 = await svc.create_decision_context(
            session=db_session, rfq_id=rfq_id, scoring_run_id=run_id
        )
        ctx2 = await svc.create_decision_context(
            session=db_session, rfq_id=rfq_id, scoring_run_id=run_id
        )
        assert ctx1.context_hash == ctx2.context_hash
        assert ctx1.context_payload == ctx2.context_payload

    async def test_context_hash_changes_with_different_data(self, db_session: AsyncSession):
        rfq_id, snap_id, cfg_id, run_id = await _seed_scoring_data(db_session)

        svc = NarrativeService()
        ctx1 = await svc.create_decision_context(
            session=db_session, rfq_id=rfq_id, scoring_run_id=run_id
        )

        # Modify scoring results
        from sqlalchemy import select

        run_stmt = select(ScoringRun).where(ScoringRun.id == run_id)
        result = await db_session.execute(run_stmt)
        run = result.scalar_one()
        modified_results = dict(run.results_payload)
        modified_results["eligible_suppliers_count"] = 99
        run.results_payload = modified_results
        await db_session.flush()

        ctx2 = await svc.create_decision_context(
            session=db_session, rfq_id=rfq_id, scoring_run_id=run_id
        )
        assert ctx1.context_hash != ctx2.context_hash


class TestMockNarrativeGeneration:
    """Test 7: Mock provider generates valid structured output."""

    async def test_mock_produces_valid_sections(self, db_session: AsyncSession):
        rfq_id, snap_id, cfg_id, run_id = await _seed_scoring_data(db_session)

        svc = NarrativeService()
        request = NarrativeGenerationRequest(
            scoring_run_id=run_id,
            narrative_type=NarrativeType.COMPARISON_SUMMARY,
        )
        response = await svc.generate_narrative(
            session=db_session, rfq_id=rfq_id, request=request
        )

        assert response.provider == "mock"
        assert response.raw_structured_output["executive_summary"]
        assert len(response.raw_structured_output["per_supplier_analysis"]) == 3
        assert response.claims  # Should have grounded claims
        assert response.output_hash
        assert response.decision_context_id

    async def test_mock_narrative_includes_server_rendered_scores(
        self, db_session: AsyncSession
    ):
        rfq_id, snap_id, cfg_id, run_id = await _seed_scoring_data(db_session)

        svc = NarrativeService()
        request = NarrativeGenerationRequest(
            scoring_run_id=run_id,
            narrative_type=NarrativeType.COMPARISON_SUMMARY,
        )
        response = await svc.generate_narrative(
            session=db_session, rfq_id=rfq_id, request=request
        )

        # Supplier analysis should contain server-rendered authoritative scores
        per_supplier = response.raw_structured_output["per_supplier_analysis"]
        alpha = next(s for s in per_supplier if s["supplier_name"] == "Alpha Supplies")
        assert alpha["total_score"] == "92.5432109876"  # Server-rendered exact value


class TestClaimGroundingValidation:
    """Tests 3-5: Grounding validation detects hallucinations."""

    def test_hallucinated_supplier_detected(self):
        """Test 3: Hallucinated supplier ID is detected and marked unsupported."""
        claims = [
            {
                "claim_index": 0,
                "text": "Phantom Corp scored 99.99",
                "claim_type": "deterministic_fact",
                "referenced_supplier_ids": ["q-phantom"],  # Not in context
                "referenced_criterion_ids": [],
                "referenced_evidence_ids": [],
                "fact_references": [],
            }
        ]
        result = validate_claims_grounding(claims, SCORING_RUN_RESULTS)
        assert result["unsupported"] == 1
        assert "Unknown supplier ID: q-phantom" in result["details"][0]["issues"][0]

    def test_nonexistent_criterion_detected(self):
        """Test 4: Nonexistent criterion reference detected."""
        claims = [
            {
                "claim_index": 0,
                "text": "Reliability was the key factor",
                "claim_type": "deterministic_fact",
                "referenced_supplier_ids": [],
                "referenced_criterion_ids": ["crit-reliability"],  # Not in context
                "referenced_evidence_ids": [],
                "fact_references": [],
            }
        ]
        result = validate_claims_grounding(claims, SCORING_RUN_RESULTS)
        assert result["unsupported"] == 1

    def test_unsupported_quantitative_claim(self):
        """Test 5: Wrong score value is detected."""
        claims = [
            {
                "claim_index": 0,
                "text": "Alpha scored 99.9999",
                "claim_type": "deterministic_fact",
                "referenced_supplier_ids": ["q-alpha"],
                "referenced_criterion_ids": [],
                "referenced_evidence_ids": [],
                "fact_references": [
                    {
                        "reference_type": "supplier_score",
                        "supplier_id": "q-alpha",
                        "field_path": "suppliers[0].total_score",
                        "authoritative_value": "99.9999",  # Wrong!
                    }
                ],
            }
        ]
        result = validate_claims_grounding(claims, SCORING_RUN_RESULTS)
        assert result["unsupported"] == 1
        assert "Score mismatch" in result["details"][0]["issues"][0]

    def test_correct_fact_reference_verified(self):
        """Correct fact reference is verified."""
        claims = [
            {
                "claim_index": 0,
                "text": "Alpha scored 92.5432109876",
                "claim_type": "deterministic_fact",
                "referenced_supplier_ids": ["q-alpha"],
                "referenced_criterion_ids": [],
                "referenced_evidence_ids": [],
                "fact_references": [
                    {
                        "reference_type": "supplier_score",
                        "supplier_id": "q-alpha",
                        "field_path": "suppliers[0].total_score",
                        "authoritative_value": "92.5432109876",
                    }
                ],
            }
        ]
        result = validate_claims_grounding(claims, SCORING_RUN_RESULTS)
        assert result["verified"] == 1
        assert result["unsupported"] == 0

    def test_nonexistent_evidence_detected(self):
        """Nonexistent evidence ID reference detected and rejected."""
        claims = [
            {
                "claim_index": 0,
                "text": "Based on certified ISO audit report DOC-999",
                "claim_type": "deterministic_fact",
                "referenced_supplier_ids": ["q-alpha"],
                "referenced_criterion_ids": [],
                "referenced_evidence_ids": ["doc-nonexistent-iso-999"],
                "fact_references": [],
            }
        ]
        result = validate_claims_grounding(claims, SCORING_RUN_RESULTS)
        assert result["unsupported"] == 1
        assert any("Unknown evidence ID" in iss for iss in result["details"][0]["issues"])

    def test_incorrect_rank_detected(self):
        """Claim stating wrong rank is detected as unsupported."""
        claims = [
            {
                "claim_index": 0,
                "text": "Alpha is ranked #2",
                "claim_type": "deterministic_fact",
                "referenced_supplier_ids": ["q-alpha"],
                "referenced_criterion_ids": [],
                "referenced_evidence_ids": [],
                "fact_references": [
                    {
                        "reference_type": "rank",
                        "supplier_id": "q-alpha",
                        "authoritative_value": "2",  # Alpha is actually rank 1
                    }
                ],
            }
        ]
        result = validate_claims_grounding(claims, SCORING_RUN_RESULTS)
        assert result["unsupported"] == 1
        assert any("Rank mismatch" in iss for iss in result["details"][0]["issues"])


class TestProviderFailure:
    """Test 6: Provider timeout/failure returns explicit error, no silent fallback."""

    async def test_no_silent_fallback_to_mock(self, db_session: AsyncSession):
        rfq_id, snap_id, cfg_id, run_id = await _seed_scoring_data(db_session)

        svc = NarrativeService()
        request = NarrativeGenerationRequest(
            scoring_run_id=run_id,
            narrative_type=NarrativeType.COMPARISON_SUMMARY,
        )

        # Patch settings to simulate a real provider with no key
        with patch("procureflow.services.narrative_service.settings") as mock_settings:
            mock_settings.llm_provider = "openai"
            mock_settings.openai_api_key = None
            mock_settings.anthropic_api_key = None

            with pytest.raises(NarrativeProviderError, match="no API key"):
                await svc.generate_narrative(
                    session=db_session, rfq_id=rfq_id, request=request
                )

    async def test_provider_timeout_returns_explicit_error(self, db_session: AsyncSession):
        rfq_id, snap_id, cfg_id, run_id = await _seed_scoring_data(db_session)
        svc = NarrativeService()
        request = NarrativeGenerationRequest(
            scoring_run_id=run_id,
            narrative_type=NarrativeType.COMPARISON_SUMMARY,
        )
        with patch("procureflow.services.narrative_service.settings") as mock_settings:
            mock_settings.llm_provider = "openai"
            mock_settings.openai_api_key = "sk-test-key"
            with patch.object(svc, "_live_generate", side_effect=TimeoutError("Provider request timed out after 30s")):
                with pytest.raises(NarrativeProviderError) as exc_info:
                    await svc.generate_narrative(
                        session=db_session, rfq_id=rfq_id, request=request
                    )
                assert "timed out" in str(exc_info.value)
                assert "Narrative generation is unavailable" in str(exc_info.value)

    async def test_provider_malformed_output_returns_explicit_error(self, db_session: AsyncSession):
        rfq_id, snap_id, cfg_id, run_id = await _seed_scoring_data(db_session)
        svc = NarrativeService()
        request = NarrativeGenerationRequest(
            scoring_run_id=run_id,
            narrative_type=NarrativeType.COMPARISON_SUMMARY,
        )
        with patch("procureflow.services.narrative_service.settings") as mock_settings:
            mock_settings.llm_provider = "openai"
            mock_settings.openai_api_key = "sk-test-key"
            with patch.object(svc, "_live_generate", side_effect=ValueError("Failed to parse provider JSON")):
                with pytest.raises(NarrativeProviderError) as exc_info:
                    await svc.generate_narrative(
                        session=db_session, rfq_id=rfq_id, request=request
                    )
                assert "Failed to parse provider JSON" in str(exc_info.value)


class TestRegenerationAppendOnly:
    """Test 8: Regeneration creates Generation #2, preserves Generation #1."""

    async def test_regeneration_preserves_previous(self, db_session: AsyncSession):
        rfq_id, snap_id, cfg_id, run_id = await _seed_scoring_data(db_session)

        svc = NarrativeService()
        request = NarrativeGenerationRequest(
            scoring_run_id=run_id,
            narrative_type=NarrativeType.COMPARISON_SUMMARY,
        )

        gen1 = await svc.generate_narrative(
            session=db_session, rfq_id=rfq_id, request=request
        )
        gen2 = await svc.generate_narrative(
            session=db_session, rfq_id=rfq_id, request=request
        )

        assert gen1.id != gen2.id
        assert gen1.generation_number == 1
        # Both exist in history
        all_narratives = await svc.list_narratives(
            session=db_session, rfq_id=rfq_id
        )
        assert len(all_narratives) == 2

        # Gen 1 is preserved unchanged
        gen1_retrieved = await svc.get_narrative(
            session=db_session, rfq_id=rfq_id, narrative_id=gen1.id
        )
        assert gen1_retrieved.output_hash == gen1.output_hash


class TestHumanRevisionHistory:
    """Test 9: Human revision creates NarrativeRevision, preserves original."""

    async def test_revision_creates_append_only_record(self, db_session: AsyncSession):
        rfq_id, snap_id, cfg_id, run_id = await _seed_scoring_data(db_session)

        svc = NarrativeService()
        request = NarrativeGenerationRequest(
            scoring_run_id=run_id,
            narrative_type=NarrativeType.COMPARISON_SUMMARY,
        )
        gen = await svc.generate_narrative(
            session=db_session, rfq_id=rfq_id, request=request
        )

        revision = await svc.create_revision(
            session=db_session,
            rfq_id=rfq_id,
            narrative_id=gen.id,
            data=NarrativeRevisionCreate(
                revised_text="Human-edited narrative content",
                revision_rationale="Improved clarity of trade-off section",
            ),
            actor_id="reviewer-1",
        )

        assert revision.revision_number == 1
        assert revision.revised_by == "reviewer-1"

        # Original generation is preserved
        gen_retrieved = await svc.get_narrative(
            session=db_session, rfq_id=rfq_id, narrative_id=gen.id
        )
        assert gen_retrieved.output_hash == gen.output_hash  # Original unchanged
        assert len(gen_retrieved.revisions) == 1
        assert gen_retrieved.current_origin.value == "ai_generated_human_revised"


class TestPromptVersioning:
    """Test 10: Prompt v1 vs v2 metadata is preserved and distinguishable."""

    async def test_prompt_metadata_persisted(self, db_session: AsyncSession):
        rfq_id, snap_id, cfg_id, run_id = await _seed_scoring_data(db_session)

        svc = NarrativeService()
        request = NarrativeGenerationRequest(
            scoring_run_id=run_id,
            narrative_type=NarrativeType.COMPARISON_SUMMARY,
        )
        gen = await svc.generate_narrative(
            session=db_session, rfq_id=rfq_id, request=request
        )

        assert gen.prompt_template_version == "narrative-prompt-v1"
        assert gen.prompt_template_hash  # Non-empty SHA-256
        assert len(gen.prompt_template_hash) == 64
        assert gen.rendered_prompt_hash
        assert len(gen.rendered_prompt_hash) == 64
        assert gen.response_schema_version == "narrative-sections-v1"

    def test_prompt_template_v1_and_v2_distinguishable(self):
        """Prompt template text changes produce distinct hashes for audit trail."""
        from procureflow.services.narrative_service import NARRATIVE_PROMPT_TEMPLATE
        hash_v1 = _sha256(NARRATIVE_PROMPT_TEMPLATE)
        template_v2 = NARRATIVE_PROMPT_TEMPLATE + "\n8. Adhere to strict public sector compliance."
        hash_v2 = _sha256(template_v2)
        assert hash_v1 != hash_v2
        assert len(hash_v1) == 64
        assert len(hash_v2) == 64


class TestProviderMetadata:
    """Test 11: Model/provider metadata is fully persisted."""

    async def test_full_metadata_persisted(self, db_session: AsyncSession):
        rfq_id, snap_id, cfg_id, run_id = await _seed_scoring_data(db_session)

        svc = NarrativeService()
        request = NarrativeGenerationRequest(
            scoring_run_id=run_id,
            narrative_type=NarrativeType.COMPARISON_SUMMARY,
        )
        gen = await svc.generate_narrative(
            session=db_session, rfq_id=rfq_id, request=request
        )

        assert gen.provider == "mock"
        assert gen.model_identifier == "mock-deterministic-v1"
        assert gen.generation_parameters["temperature"] == 0.0
        assert gen.output_hash
        assert gen.decision_context_id


class TestSupersededSemantics:
    """Test 12: Newer ScoringRun marks older narrative as superseded."""

    async def test_newer_run_supersedes_older_narratives(self, db_session: AsyncSession):
        rfq_id, snap_id, cfg_id, run_id = await _seed_scoring_data(db_session)

        svc = NarrativeService()
        request = NarrativeGenerationRequest(
            scoring_run_id=run_id,
            narrative_type=NarrativeType.COMPARISON_SUMMARY,
        )
        gen = await svc.generate_narrative(
            session=db_session, rfq_id=rfq_id, request=request
        )
        assert gen.is_superseded is False

        # Create newer scoring run
        run2 = ScoringRun(
            id="run-2",
            rfq_id="rfq-1",
            configuration_id="cfg-1",
            snapshot_id="snap-1",
            run_number=2,
            name="Scoring Run #2",
            results_payload=SCORING_RUN_RESULTS,
            provenance_hash="provhash-new",
        )
        db_session.add(run2)
        await db_session.flush()

        count = await svc.mark_superseded_by_newer_run(
            session=db_session, rfq_id=rfq_id, newer_scoring_run_id="run-2"
        )
        assert count == 1

        gen_updated = await svc.get_narrative(
            session=db_session, rfq_id=rfq_id, narrative_id=gen.id
        )
        assert gen_updated.is_superseded is True
        assert "run-2" in gen_updated.superseded_reason


class TestArchitecturalBoundary:
    """Test 15: NarrativeService cannot invoke AwardService."""

    def test_narrative_service_has_no_award_imports(self):
        """Verify NarrativeService module does not import award_service."""
        import ast
        import inspect
        import procureflow.services.narrative_service as ns_mod
        file_path = getattr(ns_mod, "__file__", None) or inspect.getfile(ns_mod.__class__)
        with open(file_path, "r", encoding="utf-8") as f:
            source = f.read()
        tree = ast.parse(source)
        imported_names = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported_names.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imported_names.append(node.module)
        assert not any("award" in name for name in imported_names)


class TestDecisionWorkflowWithoutAI:
    """Test 16: Complete decision workflow is functional with AI disabled."""

    async def test_workflow_without_ai(self, db_session: AsyncSession):
        """Award workflow operates without narrative generation."""
        rfq_id, snap_id, cfg_id, run_id = await _seed_scoring_data(db_session)

        # Import award service directly — no narrative needed
        from procureflow.services.award_service import AwardService

        award_svc = AwardService()
        from procureflow.schemas.decision import AwardDecisionCreate

        # Create draft without narrative
        draft = await award_svc.create_draft_award(
            session=db_session,
            rfq_id=rfq_id,
            data=AwardDecisionCreate(
                scoring_run_id=run_id,
                awarded_supplier_id="q-alpha",
                award_justification="Best overall score",
            ),
            actor_principal="test-principal",
        )
        assert draft.current_status.value == "draft"

        # Confirm without AI
        from procureflow.schemas.decision import AwardConfirm

        confirmed = await award_svc.confirm_award(
            session=db_session,
            rfq_id=rfq_id,
            award_id=draft.id,
            data=AwardConfirm(final_justification="Confirmed by procurement officer"),
            actor_principal="test-principal",
        )
        assert confirmed.current_status.value == "confirmed"
        assert confirmed.provenance_hash


class TestPrivacyProjection:
    """Test 8: Provider payloads use allowlisted minimum-necessary projection."""

    def test_privacy_projection_excludes_raw_blobs(self):
        from procureflow.services.narrative_service import build_provider_projection
        context_with_raw = dict(SCORING_RUN_RESULTS)
        context_with_raw["rfq"] = {"title": "Bearings RFQ", "category": "MRO", "reference_currency": "USD"}
        # Add raw file / blob fields that must never be projected
        context_with_raw["raw_pdf_bytes"] = "%PDF-1.4..."
        context_with_raw["raw_spreadsheet_data"] = "column_a,column_b\nval1,val2"
        context_with_raw["suppliers"][0]["raw_quotation_pdf"] = "JVBERi0xLjQK..."

        projection = build_provider_projection(context_with_raw, expanded_context=False)
        proj_str = json.dumps(projection)
        assert "raw_pdf_bytes" not in proj_str
        assert "raw_spreadsheet_data" not in proj_str
        assert "JVBERi0xLjQK" not in proj_str
        assert "raw_quotation_pdf" not in proj_str
        # Only allowlisted summary fields exist
        assert "rfq_title" in projection
        assert "suppliers" in projection
