"""
Phase 6 — NarrativeService: Evidence-backed decision narrative generation.

Generates AI-assisted narratives grounded in deterministic Phase 1-5 data.
Implements claim-level grounding validation, structured fact references,
append-only generation history, and privacy-minimized provider projections.

ARCHITECTURAL BOUNDARY: This service MUST NOT invoke AwardService or any
award confirmation endpoint. The LLM has no tool or action permission
capable of persisting a final supplier decision.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from decimal import Decimal
from typing import Any

import structlog
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from procureflow.config import get_settings
from procureflow.models.audit import ActorType
from procureflow.models.decision import (
    AwardStatus,
    ClaimType,
    DecisionContext,
    GroundingStatus,
    NarrativeClaim,
    NarrativeGeneration,
    NarrativeOrigin,
    NarrativeRevision,
)
from procureflow.models.normalization import ComparisonSnapshot
from procureflow.models.scoring import ScoringConfiguration, ScoringRun
from procureflow.models.rfq import RFQ
from procureflow.schemas.decision import (
    DecisionContextResponse,
    FactReference,
    NarrativeClaimSchema,
    NarrativeGenerationRequest,
    NarrativeGenerationResponse,
    NarrativeRevisionCreate,
    NarrativeRevisionResponse,
    NarrativeSections,
    NarrativeType,
    SupplierAnalysis,
)
from procureflow.services.audit_service import record_audit_event

logger = structlog.get_logger(__name__)

settings = get_settings()

DECISION_CONTEXT_SCHEMA_VERSION = "decision-context-v1"
PROMPT_TEMPLATE_VERSION = "narrative-prompt-v1"
RESPONSE_SCHEMA_VERSION = "narrative-sections-v1"


# ---------------------------------------------------------------------------
# DOMAIN ERRORS
# ---------------------------------------------------------------------------


class NarrativeDomainError(Exception):
    pass


class NarrativeScoringRunNotFoundError(NarrativeDomainError):
    pass


class NarrativeGenerationNotFoundError(NarrativeDomainError):
    pass


class NarrativeProviderError(NarrativeDomainError):
    pass


# ---------------------------------------------------------------------------
# CANONICAL HASHING UTILITIES
# ---------------------------------------------------------------------------


def _canonical_json(data: Any) -> str:
    """Produce deterministic canonical JSON string for hashing."""

    def _normalize(obj: Any) -> Any:
        if isinstance(obj, Decimal):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, dict):
            return {k: _normalize(v) for k, v in sorted(obj.items())}
        if isinstance(obj, (list, tuple)):
            return [_normalize(i) for i in obj]
        return obj

    return json.dumps(_normalize(data), sort_keys=True, separators=(",", ":"))


def _sha256(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# PROMPT TEMPLATE
# ---------------------------------------------------------------------------

NARRATIVE_PROMPT_TEMPLATE = """You are an evidence-based procurement decision analyst for ProcureFlow.
You are explaining deterministic procurement scoring results.

RULES:
1. All scores, rankings, and weighted contributions below are MATHEMATICAL FACTS
   computed by a deterministic scoring engine. DO NOT recalculate or contradict them.
2. Reference ONLY the data provided in the structured input. Do NOT invent
   supplier facts, commercial terms, or evidence not present in the input.
3. If data is missing or insufficient for a conclusion, explicitly state this as
   a limitation. Never fill gaps with assumptions.
4. Your role is to EXPLAIN and SUMMARIZE, not to DECIDE.
   The final award decision is made by a human procurement officer.
5. Use neutral, professional procurement language.
6. Clearly distinguish between facts (from data) and observations (your analysis).
7. When referencing numeric values, use EXACTLY the values provided in the input data.
   Do not round, truncate, or recalculate any values.

NARRATIVE TYPE: {narrative_type}

STRUCTURED SCORING DATA:
{structured_data}
"""

HUMAN_NOTE_SECTION = """
---
UNVERIFIED REVIEWER NOTE (this is NOT documentary evidence; do not treat as fact):
{human_note}
---
"""


def _get_prompt_template_hash() -> str:
    return _sha256(NARRATIVE_PROMPT_TEMPLATE)


# ---------------------------------------------------------------------------
# DECISION CONTEXT BUILDER
# ---------------------------------------------------------------------------


def build_decision_context_payload(
    rfq: RFQ,
    scoring_run: ScoringRun,
    config: ScoringConfiguration,
    snapshot: ComparisonSnapshot,
    sensitivity_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Build the immutable DecisionContext canonical payload from Phase 1-5 data.
    Mutable RFQ fields are snapshotted at creation time.
    """
    results = scoring_run.results_payload

    # Snapshot mutable RFQ fields
    rfq_snapshot = {
        "rfq_id": rfq.id,
        "title": rfq.title,
        "description": rfq.description,
        "category": rfq.category,
        "reference_currency": rfq.reference_currency,
        "status": rfq.status.value if hasattr(rfq.status, "value") else str(rfq.status),
    }

    # Extract supplier data from results_payload
    suppliers_context = []
    for s in results.get("suppliers", []):
        supplier_entry = {
            "quotation_id": s["quotation_id"],
            "supplier_name": s["supplier_name"],
            "eligibility_status": s["eligibility_status"],
            "knockout_reasons": s.get("knockout_reasons", []),
            "total_score": s.get("total_score", "0.0000"),
            "exact_total_score": s.get("exact_total_score", "0.0000"),
            "rank": s.get("rank"),
            "criteria_breakdown": [],
        }
        for bd in s.get("criteria_breakdown", []):
            supplier_entry["criteria_breakdown"].append(
                {
                    "criterion_id": bd["criterion_id"],
                    "criterion_name": bd["criterion_name"],
                    "raw_value": bd.get("raw_value"),
                    "exact_raw_value": bd.get("exact_raw_value"),
                    "direction": bd["direction"],
                    "normalized_score": bd.get("normalized_score", "0.0000"),
                    "exact_normalized_score": bd.get("exact_normalized_score"),
                    "weight": bd.get("weight", "0.0000"),
                    "weighted_contribution": bd.get("weighted_contribution", "0.0000"),
                    "exact_weighted_contribution": bd.get("exact_weighted_contribution"),
                    "formula_audit": bd.get("formula_audit", ""),
                    "is_knockout_applied": bd.get("is_knockout_applied", False),
                    "source_path": bd.get("source_path", ""),
                    "notes": bd.get("notes"),
                }
            )
        suppliers_context.append(supplier_entry)

    payload = {
        "context_schema_version": DECISION_CONTEXT_SCHEMA_VERSION,
        "rfq": rfq_snapshot,
        "comparison_snapshot": {
            "id": snapshot.id,
            "version": snapshot.snapshot_version,
            "content_hash": results.get("comparison_snapshot_hash", ""),
        },
        "scoring_configuration": {
            "id": config.id,
            "version": config.version,
            "name": config.name,
            "content_hash": results.get("scoring_configuration_hash", ""),
            "engine_version": results.get("engine_version", ""),
        },
        "scoring_run": {
            "id": scoring_run.id,
            "run_number": scoring_run.run_number,
            "provenance_hash": scoring_run.provenance_hash or "",
            "evaluated_at": results.get("evaluated_at", ""),
        },
        "engine_policy": results.get("engine_policy", {}),
        "eligible_suppliers_count": results.get("eligible_suppliers_count", 0),
        "knockout_suppliers_count": results.get("knockout_suppliers_count", 0),
        "suppliers": suppliers_context,
    }

    if sensitivity_data:
        payload["sensitivity"] = sensitivity_data

    return payload


def build_provider_projection(
    context_payload: dict[str, Any],
    expanded_context: bool = False,
) -> dict[str, Any]:
    """
    Build an allowlisted minimum-necessary provider projection.
    By default, sends only structured, verified context fields.
    Local providers may use expanded_context=True for additional detail,
    but still never receive raw supplier documents.
    """
    suppliers_projection = []
    for s in context_payload.get("suppliers", []):
        entry: dict[str, Any] = {
            "supplier_name": s["supplier_name"],
            "eligibility_status": s["eligibility_status"],
            "total_score": s["total_score"],
            "rank": s.get("rank"),
            "knockout_reasons": s.get("knockout_reasons", []),
        }
        if expanded_context:
            entry["quotation_id"] = s["quotation_id"]
            entry["exact_total_score"] = s.get("exact_total_score")

        criteria_proj = []
        for bd in s.get("criteria_breakdown", []):
            crit_entry: dict[str, Any] = {
                "criterion_name": bd["criterion_name"],
                "normalized_score": bd["normalized_score"],
                "weight": bd["weight"],
                "weighted_contribution": bd["weighted_contribution"],
                "direction": bd["direction"],
            }
            if expanded_context:
                crit_entry["criterion_id"] = bd.get("criterion_id")
                crit_entry["raw_value"] = bd.get("raw_value")
                crit_entry["formula_audit"] = bd.get("formula_audit")
            criteria_proj.append(crit_entry)
        entry["criteria_breakdown"] = criteria_proj
        suppliers_projection.append(entry)

    projection = {
        "rfq_title": context_payload.get("rfq", {}).get("title", ""),
        "rfq_category": context_payload.get("rfq", {}).get("category", ""),
        "reference_currency": context_payload.get("rfq", {}).get("reference_currency", "USD"),
        "eligible_suppliers_count": context_payload.get("eligible_suppliers_count", 0),
        "knockout_suppliers_count": context_payload.get("knockout_suppliers_count", 0),
        "suppliers": suppliers_projection,
    }

    if "sensitivity" in context_payload and expanded_context:
        projection["sensitivity"] = context_payload["sensitivity"]

    return projection


# ---------------------------------------------------------------------------
# GROUNDING VALIDATOR
# ---------------------------------------------------------------------------


def validate_claims_grounding(
    claims: list[dict[str, Any]],
    context_payload: dict[str, Any],
) -> dict[str, Any]:
    """
    Deterministic post-generation grounding validation.
    Validates each claim against the authoritative DecisionContext.

    Rejects or marks unsupported:
    - Unknown supplier IDs not in context
    - Nonexistent criterion IDs not in context
    - Nonexistent evidence IDs
    - Score/rank values contradicting context
    """
    valid_supplier_ids = set()
    valid_criterion_ids = set()
    valid_evidence_ids = set()
    supplier_scores: dict[str, str] = {}
    supplier_ranks: dict[str, int | None] = {}

    for s in context_payload.get("suppliers", []):
        qid = s["quotation_id"]
        valid_supplier_ids.add(qid)
        supplier_scores[qid] = s.get("exact_total_score", s.get("total_score", ""))
        supplier_ranks[qid] = s.get("rank")
        for bd in s.get("criteria_breakdown", []):
            valid_criterion_ids.add(bd.get("criterion_id", ""))
            src = bd.get("source_path")
            if src:
                valid_evidence_ids.add(src)

    validation_result = {
        "total_claims": len(claims),
        "verified": 0,
        "unsupported": 0,
        "unverifiable": 0,
        "details": [],
    }

    for claim in claims:
        issues: list[str] = []

        # Check supplier references
        for sid in claim.get("referenced_supplier_ids", []):
            if sid and sid not in valid_supplier_ids:
                issues.append(f"Unknown supplier ID: {sid}")

        # Check criterion references
        for cid in claim.get("referenced_criterion_ids", []):
            if cid and cid not in valid_criterion_ids:
                issues.append(f"Unknown criterion ID: {cid}")

        # Check evidence references
        for eid in claim.get("referenced_evidence_ids", []):
            if eid and eid not in valid_evidence_ids:
                issues.append(f"Unknown evidence ID: {eid}")

        # Check fact references for score/rank accuracy
        for ref in claim.get("fact_references", []):
            if isinstance(ref, dict):
                ref_type = ref.get("reference_type", "")
                sid = ref.get("supplier_id")
                auth_val = ref.get("authoritative_value", "")

                if ref_type == "supplier_score" and sid:
                    if sid not in valid_supplier_ids:
                        issues.append(f"Score reference to unknown supplier: {sid}")
                    elif auth_val:
                        actual_val = supplier_scores.get(sid, "")
                        try:
                            if Decimal(str(auth_val)) != Decimal(str(actual_val)):
                                issues.append(
                                    f"Score mismatch for {sid}: claimed={auth_val}, "
                                    f"actual={actual_val}"
                                )
                        except Exception:
                            if str(auth_val) != str(actual_val):
                                issues.append(
                                    f"Score mismatch for {sid}: claimed={auth_val}, "
                                    f"actual={actual_val}"
                                )

                if ref_type == "rank" and sid:
                    try:
                        claimed_rank = int(auth_val)
                        actual_rank = supplier_ranks.get(sid)
                        if actual_rank is not None and claimed_rank != actual_rank:
                            issues.append(
                                f"Rank mismatch for {sid}: claimed={claimed_rank}, "
                                f"actual={actual_rank}"
                            )
                    except (ValueError, TypeError):
                        pass

        # Determine grounding status
        claim_type = claim.get("claim_type", "interpretation")
        if issues:
            status = "unsupported"
            validation_result["unsupported"] += 1
        elif claim_type == "deterministic_fact":
            status = "verified"
            validation_result["verified"] += 1
        else:
            status = "unverifiable"
            validation_result["unverifiable"] += 1

        validation_result["details"].append(
            {
                "claim_index": claim.get("claim_index", 0),
                "status": status,
                "issues": issues,
            }
        )

    return validation_result


# ---------------------------------------------------------------------------
# MOCK NARRATIVE PROVIDER
# ---------------------------------------------------------------------------


def generate_mock_narrative(
    context_payload: dict[str, Any],
    narrative_type: str,
) -> tuple[NarrativeSections, list[dict[str, Any]]]:
    """
    Deterministic, offline narrative generation from structured data.
    No LLM call — produces template-based sections from authoritative values.
    Returns (sections, claims) where critical numeric values are rendered
    server-side from DecisionContext.
    """
    suppliers = context_payload.get("suppliers", [])
    rfq_title = context_payload.get("rfq", {}).get("title", "Untitled RFQ")

    # Sort eligible suppliers by rank
    eligible = [s for s in suppliers if s.get("eligibility_status") == "eligible"]
    eligible.sort(key=lambda x: (x.get("rank") or 999, x.get("supplier_name", "")))
    knockout = [s for s in suppliers if s.get("eligibility_status") != "eligible"]

    # Build per-supplier analysis with server-rendered authoritative values
    per_supplier = []
    claims: list[dict[str, Any]] = []
    claim_idx = 0

    for s in eligible:
        name = s.get("supplier_name", "Unknown")
        qid = s.get("quotation_id", "")
        score = s.get("total_score", "0.0000")
        exact_score = s.get("exact_total_score", score)
        rank = s.get("rank")

        strengths = []
        weaknesses = []
        for bd in s.get("criteria_breakdown", []):
            cname = bd.get("criterion_name", "")
            nscore = bd.get("normalized_score", "0.0000")
            weight = bd.get("weight", "0.0000")
            wc = bd.get("weighted_contribution", "0.0000")
            try:
                ns_val = float(nscore)
                if ns_val >= 70:
                    strengths.append(f"{cname}: normalized {nscore}/100 (weight {weight})")
                elif ns_val < 40:
                    weaknesses.append(f"{cname}: normalized {nscore}/100 (weight {weight})")
            except (ValueError, TypeError):
                pass

        per_supplier.append(
            SupplierAnalysis(
                supplier_id=qid,
                supplier_name=name,
                rank=rank,
                total_score=exact_score,  # Server-rendered authoritative value
                strengths=strengths or [f"Scored {score} overall"],
                weaknesses=weaknesses or ["No significant weaknesses identified"],
                score_context=f"Ranked #{rank} with total score {score}",
            )
        )

        # Build grounded claims with fact references
        claims.append(
            {
                "claim_index": claim_idx,
                "text": f"{name} achieved a total score of {score} and is ranked #{rank}.",
                "claim_type": "deterministic_fact",
                "referenced_supplier_ids": [qid],
                "referenced_criterion_ids": [],
                "referenced_evidence_ids": [],
                "fact_references": [
                    {
                        "reference_type": "supplier_score",
                        "supplier_id": qid,
                        "field_path": f"suppliers[quotation_id={qid}].total_score",
                        "authoritative_value": str(score),
                    },
                    {
                        "reference_type": "rank",
                        "supplier_id": qid,
                        "field_path": f"suppliers[quotation_id={qid}].rank",
                        "authoritative_value": str(rank),
                    },
                ],
            }
        )
        claim_idx += 1

    # Executive summary
    top_name = eligible[0].get("supplier_name", "N/A") if eligible else "N/A"
    top_score = eligible[0].get("total_score", "N/A") if eligible else "N/A"
    exec_summary = (
        f"This {narrative_type.replace('_', ' ')} evaluates {len(eligible)} eligible "
        f"supplier(s) and {len(knockout)} ineligible supplier(s) for '{rfq_title}'. "
        f"The highest-ranked supplier is {top_name} with a score of {top_score}."
    )

    # Knockout summary
    knockout_notes = []
    for ko in knockout:
        ko_name = ko.get("supplier_name", "Unknown")
        ko_reasons = "; ".join(ko.get("knockout_reasons", ["No reason provided"]))
        knockout_notes.append(f"{ko_name}: {ko_reasons}")

    trade_offs = "Trade-off analysis based on criterion contributions across ranked suppliers."
    if len(eligible) >= 2:
        s1, s2 = eligible[0], eligible[1]
        trade_offs = (
            f"Between {s1.get('supplier_name')} (#{s1.get('rank')}, score {s1.get('total_score')}) "
            f"and {s2.get('supplier_name')} (#{s2.get('rank')}, score {s2.get('total_score')}): "
            f"differences emerge across individual criterion contributions."
        )

    limitations = [
        "This narrative is generated from structured scoring data only.",
        "Qualitative factors not captured in the scoring model are not considered.",
    ]
    if knockout_notes:
        limitations.append(
            f"{len(knockout)} supplier(s) were excluded due to knockout criteria."
        )

    # Add a limitation claim
    claims.append(
        {
            "claim_index": claim_idx,
            "text": "This analysis is based solely on the deterministic scoring model and does not account for qualitative factors outside the configured criteria.",
            "claim_type": "limitation",
            "referenced_supplier_ids": [],
            "referenced_criterion_ids": [],
            "referenced_evidence_ids": [],
            "fact_references": [],
        }
    )

    sections = NarrativeSections(
        executive_summary=exec_summary,
        ranking_explanation=(
            f"Suppliers are ranked using standard competitive ranking (1-2-2-4) "
            f"based on weighted normalized scores across all configured criteria. "
            f"{len(eligible)} supplier(s) are eligible; {len(knockout)} are ineligible."
        ),
        per_supplier_analysis=per_supplier,
        trade_offs=trade_offs,
        decision_considerations=(
            "The procurement officer should consider qualitative factors, "
            "commercial relationship history, and strategic alignment alongside "
            "the quantitative scores presented in this analysis."
        ),
        risk_factors=[
            "Scoring model is sensitive to criterion weight configuration.",
            "Suppliers near the threshold may change rank with minor weight adjustments.",
        ],
        data_limitations=limitations,
    )

    return sections, claims


# ---------------------------------------------------------------------------
# NARRATIVE SERVICE
# ---------------------------------------------------------------------------


class NarrativeService:
    """
    Evidence-backed decision narrative generation service.

    ARCHITECTURAL BOUNDARY: This class MUST NOT import, reference, or invoke
    AwardService or any award confirmation action.
    """

    async def create_decision_context(
        self,
        session: AsyncSession,
        rfq_id: str,
        scoring_run_id: str,
        include_sensitivity: bool = False,
        sensitivity_data: dict[str, Any] | None = None,
        actor_id: str = "system",
    ) -> DecisionContext:
        """Build and persist an immutable DecisionContext from Phase 1-5 data."""
        # Load required Phase 1-5 records
        run_stmt = select(ScoringRun).where(
            ScoringRun.id == scoring_run_id,
            ScoringRun.rfq_id == rfq_id,
        )
        run_result = await session.execute(run_stmt)
        scoring_run = run_result.scalar_one_or_none()
        if not scoring_run:
            raise NarrativeScoringRunNotFoundError(
                f"ScoringRun '{scoring_run_id}' not found for RFQ '{rfq_id}'"
            )

        cfg_stmt = select(ScoringConfiguration).where(
            ScoringConfiguration.id == scoring_run.configuration_id,
        )
        cfg_result = await session.execute(cfg_stmt)
        config = cfg_result.scalar_one_or_none()
        if not config:
            raise NarrativeDomainError(
                f"ScoringConfiguration '{scoring_run.configuration_id}' not found"
            )

        snap_stmt = select(ComparisonSnapshot).where(
            ComparisonSnapshot.id == scoring_run.snapshot_id,
        )
        snap_result = await session.execute(snap_stmt)
        snapshot = snap_result.scalar_one_or_none()
        if not snapshot:
            raise NarrativeDomainError(
                f"ComparisonSnapshot '{scoring_run.snapshot_id}' not found"
            )

        rfq_stmt = select(RFQ).where(RFQ.id == rfq_id)
        rfq_result = await session.execute(rfq_stmt)
        rfq = rfq_result.scalar_one_or_none()
        if not rfq:
            raise NarrativeDomainError(f"RFQ '{rfq_id}' not found")

        # Build canonical payload
        context_payload = build_decision_context_payload(
            rfq=rfq,
            scoring_run=scoring_run,
            config=config,
            snapshot=snapshot,
            sensitivity_data=sensitivity_data if include_sensitivity else None,
        )
        context_hash = _sha256(_canonical_json(context_payload))

        # Build privacy-minimized provider projection
        is_local = settings.llm_provider in ("ollama", "mock")
        provider_projection = build_provider_projection(
            context_payload, expanded_context=is_local
        )

        dc = DecisionContext(
            rfq_id=rfq_id,
            scoring_run_id=scoring_run_id,
            context_schema_version=DECISION_CONTEXT_SCHEMA_VERSION,
            context_payload=context_payload,
            context_hash=context_hash,
            provider_projection=provider_projection,
            includes_sensitivity=include_sensitivity,
            created_by=actor_id,
        )
        session.add(dc)
        await session.flush()
        return dc

    async def generate_narrative(
        self,
        session: AsyncSession,
        rfq_id: str,
        request: NarrativeGenerationRequest,
        actor_id: str = "system",
    ) -> NarrativeGenerationResponse:
        """
        Generate an evidence-backed decision narrative.

        1. Create immutable DecisionContext
        2. Generate narrative via configured provider (LLM or mock)
        3. Validate grounding of all claims
        4. Persist NarrativeGeneration + NarrativeClaims
        5. Record audit event
        """
        # 1. Create DecisionContext
        dc = await self.create_decision_context(
            session=session,
            rfq_id=rfq_id,
            scoring_run_id=request.scoring_run_id,
            include_sensitivity=request.include_sensitivity,
            actor_id=actor_id,
        )

        # 2. Determine generation number
        gen_count_stmt = select(func.count(NarrativeGeneration.id)).where(
            NarrativeGeneration.decision_context_id == dc.id,
        )
        gen_count_result = await session.execute(gen_count_stmt)
        existing_count = gen_count_result.scalar() or 0
        generation_number = existing_count + 1

        # Also count across all contexts for this scoring run
        all_gen_stmt = select(func.count(NarrativeGeneration.id)).where(
            NarrativeGeneration.rfq_id == rfq_id,
        )
        all_gen_result = await session.execute(all_gen_stmt)

        # 3. Build prompt
        structured_data_json = json.dumps(
            dc.provider_projection or dc.context_payload, indent=2, default=str
        )

        rendered_prompt = NARRATIVE_PROMPT_TEMPLATE.format(
            narrative_type=request.narrative_type.value,
            structured_data=structured_data_json,
        )

        if request.human_unverified_note:
            rendered_prompt += HUMAN_NOTE_SECTION.format(
                human_note=request.human_unverified_note
            )

        prompt_template_hash = _get_prompt_template_hash()
        rendered_prompt_hash = _sha256(rendered_prompt)

        # 4. Generate narrative
        provider = settings.llm_provider
        model_id = "mock-deterministic"

        if provider == "mock" or not self._has_api_key():
            if provider != "mock" and not self._has_api_key():
                # Do NOT silently fall back — raise explicit error in non-mock config
                raise NarrativeProviderError(
                    f"LLM provider '{provider}' is configured but no API key is available. "
                    "Narrative generation requires either a valid API key or "
                    "PROCUREFLOW_LLM_PROVIDER=mock. "
                    "Deterministic scoring and human decision recording remain fully operational."
                )
            sections, claims_data = generate_mock_narrative(
                dc.context_payload, request.narrative_type.value
            )
            model_id = "mock-deterministic-v1"
        else:
            try:
                sections, claims_data = self._live_generate(
                    dc, request, rendered_prompt
                )
                model_id = self._get_model_identifier()
            except Exception as e:
                # Explicit error — no silent fallback to mock in production
                raise NarrativeProviderError(
                    f"LLM provider '{provider}' failed: {e}. "
                    "Narrative generation is unavailable. "
                    "Deterministic scoring and human decision recording remain fully operational."
                ) from e

        # 5. Validate grounding
        grounding_result = validate_claims_grounding(claims_data, dc.context_payload)

        # 6. Persist generation
        raw_output = sections.model_dump(mode="json")
        output_hash = _sha256(_canonical_json(raw_output))

        generation_params = {
            "temperature": 0.0,
            "provider": provider,
            "response_format": "instructor_pydantic",
        }

        gen = NarrativeGeneration(
            rfq_id=rfq_id,
            decision_context_id=dc.id,
            narrative_type=request.narrative_type.value,
            generation_number=generation_number,
            origin=NarrativeOrigin.AI_GENERATED,
            provider=provider,
            model_identifier=model_id,
            prompt_template_version=PROMPT_TEMPLATE_VERSION,
            prompt_template_hash=prompt_template_hash,
            rendered_prompt_hash=rendered_prompt_hash,
            response_schema_version=RESPONSE_SCHEMA_VERSION,
            generation_parameters=generation_params,
            raw_structured_output=raw_output,
            output_hash=output_hash,
            grounding_validation_result=grounding_result,
            created_by=actor_id,
        )
        session.add(gen)
        await session.flush()

        # 7. Persist claims
        for c in claims_data:
            grounding_detail = next(
                (d for d in grounding_result["details"] if d["claim_index"] == c["claim_index"]),
                None,
            )
            g_status = GroundingStatus.UNVERIFIABLE
            g_notes = None
            if grounding_detail:
                g_status = GroundingStatus(grounding_detail["status"])
                if grounding_detail.get("issues"):
                    g_notes = "; ".join(grounding_detail["issues"])

            claim = NarrativeClaim(
                narrative_generation_id=gen.id,
                claim_index=c["claim_index"],
                text=c["text"],
                claim_type=ClaimType(c.get("claim_type", "interpretation")),
                grounding_status=g_status,
                referenced_supplier_ids=c.get("referenced_supplier_ids", []),
                referenced_criterion_ids=c.get("referenced_criterion_ids", []),
                referenced_evidence_ids=c.get("referenced_evidence_ids", []),
                fact_references=c.get("fact_references"),
                grounding_notes=g_notes,
            )
            session.add(claim)

        # 8. Audit event
        await record_audit_event(
            db=session,
            rfq_id=rfq_id,
            event_type="NARRATIVE_GENERATED",
            actor_id=actor_id,
            actor_type=ActorType.SYSTEM,
            payload={
                "narrative_generation_id": gen.id,
                "decision_context_id": dc.id,
                "narrative_type": request.narrative_type.value,
                "generation_number": generation_number,
                "provider": provider,
                "model": model_id,
                "grounding_verified": grounding_result["verified"],
                "grounding_unsupported": grounding_result["unsupported"],
            },
        )

        await session.commit()
        await session.refresh(gen)

        # Build response
        claims_response = []
        claim_stmt = select(NarrativeClaim).where(
            NarrativeClaim.narrative_generation_id == gen.id
        )
        claim_result = await session.execute(claim_stmt)
        for nc in claim_result.scalars().all():
            claims_response.append(NarrativeClaimSchema.model_validate(nc))

        return NarrativeGenerationResponse(
            id=gen.id,
            rfq_id=gen.rfq_id,
            decision_context_id=gen.decision_context_id,
            narrative_type=NarrativeType(gen.narrative_type),
            generation_number=gen.generation_number,
            origin=NarrativeOrigin(gen.origin),
            provider=gen.provider,
            model_identifier=gen.model_identifier,
            prompt_template_version=gen.prompt_template_version,
            prompt_template_hash=gen.prompt_template_hash,
            rendered_prompt_hash=gen.rendered_prompt_hash,
            response_schema_version=gen.response_schema_version,
            generation_parameters=gen.generation_parameters,
            raw_structured_output=gen.raw_structured_output,
            output_hash=gen.output_hash,
            grounding_validation_result=gen.grounding_validation_result,
            is_superseded=gen.is_superseded,
            superseded_reason=gen.superseded_reason,
            generated_at=gen.generated_at,
            created_by=gen.created_by,
            claims=claims_response,
            revisions=[],
            current_origin=NarrativeOrigin.AI_GENERATED,
        )

    async def get_narrative(
        self,
        session: AsyncSession,
        rfq_id: str,
        narrative_id: str,
    ) -> NarrativeGenerationResponse:
        stmt = select(NarrativeGeneration).where(
            NarrativeGeneration.id == narrative_id,
            NarrativeGeneration.rfq_id == rfq_id,
        )
        result = await session.execute(stmt)
        gen = result.scalar_one_or_none()
        if not gen:
            raise NarrativeGenerationNotFoundError(
                f"NarrativeGeneration '{narrative_id}' not found for RFQ '{rfq_id}'"
            )

        return await self._build_generation_response(session, gen)

    async def list_narratives(
        self,
        session: AsyncSession,
        rfq_id: str,
        scoring_run_id: str | None = None,
    ) -> list[NarrativeGenerationResponse]:
        stmt = select(NarrativeGeneration).where(
            NarrativeGeneration.rfq_id == rfq_id,
        )
        if scoring_run_id:
            # Filter by DecisionContext linked to this scoring run
            stmt = stmt.join(DecisionContext).where(
                DecisionContext.scoring_run_id == scoring_run_id,
            )
        stmt = stmt.order_by(desc(NarrativeGeneration.generated_at))
        result = await session.execute(stmt)

        responses = []
        for gen in result.scalars().all():
            responses.append(await self._build_generation_response(session, gen))
        return responses

    async def create_revision(
        self,
        session: AsyncSession,
        rfq_id: str,
        narrative_id: str,
        data: NarrativeRevisionCreate,
        actor_id: str = "system",
    ) -> NarrativeRevisionResponse:
        """Create an append-only human revision of an AI narrative."""
        gen_stmt = select(NarrativeGeneration).where(
            NarrativeGeneration.id == narrative_id,
            NarrativeGeneration.rfq_id == rfq_id,
        )
        gen_result = await session.execute(gen_stmt)
        gen = gen_result.scalar_one_or_none()
        if not gen:
            raise NarrativeGenerationNotFoundError(
                f"NarrativeGeneration '{narrative_id}' not found for RFQ '{rfq_id}'"
            )

        # Get next revision number
        rev_count_stmt = select(func.max(NarrativeRevision.revision_number)).where(
            NarrativeRevision.narrative_generation_id == narrative_id,
        )
        rev_count_result = await session.execute(rev_count_stmt)
        max_rev = rev_count_result.scalar() or 0

        revision = NarrativeRevision(
            narrative_generation_id=narrative_id,
            revision_number=max_rev + 1,
            revised_text=data.revised_text,
            revision_rationale=data.revision_rationale,
            revised_by=actor_id,
        )
        session.add(revision)

        # Update origin on generation if still AI_GENERATED
        if gen.origin == NarrativeOrigin.AI_GENERATED:
            gen.origin = NarrativeOrigin.AI_GENERATED_HUMAN_REVISED

        await record_audit_event(
            db=session,
            rfq_id=rfq_id,
            event_type="NARRATIVE_REVISED",
            actor_id=actor_id,
            actor_type=ActorType.USER,
            payload={
                "narrative_generation_id": narrative_id,
                "revision_number": max_rev + 1,
            },
        )

        await session.commit()
        await session.refresh(revision)
        return NarrativeRevisionResponse.model_validate(revision)

    async def mark_superseded_by_newer_run(
        self,
        session: AsyncSession,
        rfq_id: str,
        newer_scoring_run_id: str,
    ) -> int:
        """
        Mark all narratives for an RFQ that are based on older scoring runs
        as superseded when a newer ScoringRun is created.
        Does NOT modify content — only sets the superseded flag.
        """
        # Find all DecisionContexts for this RFQ
        ctx_stmt = select(DecisionContext).where(
            DecisionContext.rfq_id == rfq_id,
            DecisionContext.scoring_run_id != newer_scoring_run_id,
        )
        ctx_result = await session.execute(ctx_stmt)
        old_context_ids = [c.id for c in ctx_result.scalars().all()]

        if not old_context_ids:
            return 0

        # Mark their narratives as superseded
        gen_stmt = select(NarrativeGeneration).where(
            NarrativeGeneration.decision_context_id.in_(old_context_ids),
            NarrativeGeneration.is_superseded == False,  # noqa: E712
        )
        gen_result = await session.execute(gen_stmt)
        count = 0
        for gen in gen_result.scalars().all():
            gen.is_superseded = True
            gen.superseded_reason = (
                f"A newer ScoringRun '{newer_scoring_run_id}' has been created for this RFQ."
            )
            count += 1

        if count > 0:
            await session.flush()
        return count

    async def get_decision_context(
        self,
        session: AsyncSession,
        rfq_id: str,
        context_id: str,
    ) -> DecisionContextResponse:
        stmt = select(DecisionContext).where(
            DecisionContext.id == context_id,
            DecisionContext.rfq_id == rfq_id,
        )
        result = await session.execute(stmt)
        dc = result.scalar_one_or_none()
        if not dc:
            raise NarrativeDomainError(
                f"DecisionContext '{context_id}' not found for RFQ '{rfq_id}'"
            )
        return DecisionContextResponse.model_validate(dc)

    # -----------------------------------------------------------------------
    # PRIVATE HELPERS
    # -----------------------------------------------------------------------

    def _has_api_key(self) -> bool:
        if settings.llm_provider == "openai":
            return bool(settings.openai_api_key)
        if settings.llm_provider == "anthropic":
            return bool(settings.anthropic_api_key)
        if settings.llm_provider == "ollama":
            return True  # No key needed for local
        return False

    def _get_model_identifier(self) -> str:
        if settings.llm_provider == "openai":
            return settings.openai_model
        if settings.llm_provider == "ollama":
            return settings.ollama_model
        return f"{settings.llm_provider}-default"

    def _live_generate(
        self,
        dc: DecisionContext,
        request: NarrativeGenerationRequest,
        rendered_prompt: str,
    ) -> tuple[NarrativeSections, list[dict[str, Any]]]:
        """Live LLM generation via instructor + litellm."""
        import instructor
        import litellm

        client = instructor.from_litellm(litellm.completion)
        model = self._get_model_identifier()

        response = client.chat.completions.create(
            model=model,
            response_model=NarrativeSections,
            messages=[
                {
                    "role": "system",
                    "content": rendered_prompt,
                },
            ],
            temperature=0.0,
        )

        # Convert structured output to claims
        claims = self._sections_to_claims(response, dc.context_payload)
        return response, claims

    def _sections_to_claims(
        self,
        sections: NarrativeSections,
        context_payload: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Convert NarrativeSections to structured claims with fact references."""
        claims: list[dict[str, Any]] = []
        suppliers = context_payload.get("suppliers", [])

        claim_idx = 0
        for sa in sections.per_supplier_analysis:
            # Build fact references from authoritative context
            fact_refs = []
            matching_supplier = next(
                (s for s in suppliers if s.get("quotation_id") == sa.supplier_id),
                None,
            )
            if matching_supplier:
                fact_refs.append(
                    {
                        "reference_type": "supplier_score",
                        "supplier_id": sa.supplier_id,
                        "field_path": f"suppliers[quotation_id={sa.supplier_id}].total_score",
                        "authoritative_value": str(
                            matching_supplier.get("total_score", "")
                        ),
                    }
                )
                if matching_supplier.get("rank"):
                    fact_refs.append(
                        {
                            "reference_type": "rank",
                            "supplier_id": sa.supplier_id,
                            "field_path": f"suppliers[quotation_id={sa.supplier_id}].rank",
                            "authoritative_value": str(matching_supplier["rank"]),
                        }
                    )

            claims.append(
                {
                    "claim_index": claim_idx,
                    "text": f"{sa.supplier_name}: {sa.score_context}",
                    "claim_type": "deterministic_fact",
                    "referenced_supplier_ids": [sa.supplier_id],
                    "referenced_criterion_ids": [],
                    "referenced_evidence_ids": [],
                    "fact_references": fact_refs,
                }
            )
            claim_idx += 1

        # Add limitation claims
        for lim in sections.data_limitations:
            claims.append(
                {
                    "claim_index": claim_idx,
                    "text": lim,
                    "claim_type": "limitation",
                    "referenced_supplier_ids": [],
                    "referenced_criterion_ids": [],
                    "referenced_evidence_ids": [],
                    "fact_references": [],
                }
            )
            claim_idx += 1

        return claims

    async def _build_generation_response(
        self,
        session: AsyncSession,
        gen: NarrativeGeneration,
    ) -> NarrativeGenerationResponse:
        # Load claims
        claim_stmt = select(NarrativeClaim).where(
            NarrativeClaim.narrative_generation_id == gen.id
        ).order_by(NarrativeClaim.claim_index)
        claim_result = await session.execute(claim_stmt)
        claims = [NarrativeClaimSchema.model_validate(c) for c in claim_result.scalars().all()]

        # Load revisions
        rev_stmt = select(NarrativeRevision).where(
            NarrativeRevision.narrative_generation_id == gen.id
        ).order_by(NarrativeRevision.revision_number)
        rev_result = await session.execute(rev_stmt)
        revisions = [
            NarrativeRevisionResponse.model_validate(r) for r in rev_result.scalars().all()
        ]

        # Determine current origin
        current_origin = NarrativeOrigin(gen.origin)
        if revisions:
            current_origin = NarrativeOrigin.AI_GENERATED_HUMAN_REVISED

        # Determine superseded status dynamically if newer scoring run exists
        is_superseded = gen.is_superseded
        superseded_reason = gen.superseded_reason
        if not is_superseded:
            dc_stmt = select(DecisionContext.scoring_run_id).where(
                DecisionContext.id == gen.decision_context_id
            )
            dc_run_id = (await session.execute(dc_stmt)).scalar()
            if dc_run_id:
                latest_run_stmt = (
                    select(ScoringRun.id, ScoringRun.run_number)
                    .where(ScoringRun.rfq_id == gen.rfq_id)
                    .order_by(desc(ScoringRun.run_number))
                    .limit(1)
                )
                latest_run = (await session.execute(latest_run_stmt)).first()
                if latest_run and latest_run[0] != dc_run_id:
                    cur_run_stmt = select(ScoringRun.run_number).where(
                        ScoringRun.id == dc_run_id
                    )
                    cur_run_num = (await session.execute(cur_run_stmt)).scalar() or 0
                    if latest_run[1] > cur_run_num:
                        is_superseded = True
                        superseded_reason = (
                            f"A newer ScoringRun (Run #{latest_run[1]}) exists for this RFQ."
                        )

        return NarrativeGenerationResponse(
            id=gen.id,
            rfq_id=gen.rfq_id,
            decision_context_id=gen.decision_context_id,
            narrative_type=NarrativeType(gen.narrative_type),
            generation_number=gen.generation_number,
            origin=NarrativeOrigin(gen.origin),
            provider=gen.provider,
            model_identifier=gen.model_identifier,
            prompt_template_version=gen.prompt_template_version,
            prompt_template_hash=gen.prompt_template_hash,
            rendered_prompt_hash=gen.rendered_prompt_hash,
            response_schema_version=gen.response_schema_version,
            generation_parameters=gen.generation_parameters,
            raw_structured_output=gen.raw_structured_output,
            output_hash=gen.output_hash,
            grounding_validation_result=gen.grounding_validation_result,
            is_superseded=is_superseded,
            superseded_reason=superseded_reason,
            generated_at=gen.generated_at,
            created_by=gen.created_by,
            claims=claims,
            revisions=revisions,
            current_origin=current_origin,
        )


narrative_service = NarrativeService()
