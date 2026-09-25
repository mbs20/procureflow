"""
Phase 6 — AwardService: Human-confirmed award decision workflow.

Event-sourced award lifecycle: draft → confirm → revoke.
Confirmation and revocation history is fully reproducible via append-only events.

ARCHITECTURAL BOUNDARY: This service has NO LLM invocation capability.
Award confirmation is only reachable through authenticated human-initiated API calls.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime

import structlog
from sqlalchemy import desc, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from procureflow.models.audit import ActorType
from procureflow.models.decision import (
    AwardDecision,
    AwardDecisionEvent,
    AwardEventType,
    AwardStatus,
)
from procureflow.models.rfq import RFQ, RFQStatus
from procureflow.models.scoring import ScoringRun
from procureflow.schemas.decision import (
    AwardConfirm,
    AwardDecisionCreate,
    AwardDecisionEventResponse,
    AwardDecisionResponse,
    AwardRevoke,
)
from procureflow.schemas.decision import AwardStatus as ResponseAwardStatus
from procureflow.services.audit_service import record_audit_event

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# DOMAIN ERRORS
# ---------------------------------------------------------------------------


class AwardDomainError(Exception):
    pass


class AwardNotFoundError(AwardDomainError):
    pass


class AwardConflictError(AwardDomainError):
    """Raised when a concurrent or duplicate award operation is attempted."""

    pass


class AwardInvalidStateError(AwardDomainError):
    """Raised when an award operation is invalid for the current state."""

    pass


class AwardSupplierValidationError(AwardDomainError):
    """Raised when the selected supplier fails validation."""

    pass


# ---------------------------------------------------------------------------
# PROVENANCE HASHING
# ---------------------------------------------------------------------------


def _compute_award_provenance_hash(
    award_id: str,
    rfq_id: str,
    scoring_run_id: str,
    scoring_run_provenance_hash: str,
    awarded_supplier_id: str,
    justification: str,
    confirming_principal: str,
    confirmed_at: str,
) -> str:
    """Compute SHA-256 provenance hash binding the award to its scoring run."""
    canonical = json.dumps(
        {
            "award_id": award_id,
            "rfq_id": rfq_id,
            "scoring_run_id": scoring_run_id,
            "scoring_run_provenance_hash": scoring_run_provenance_hash,
            "awarded_supplier_id": awarded_supplier_id,
            "justification": justification,
            "confirming_principal": confirming_principal,
            "confirmed_at": confirmed_at,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# AWARD SERVICE
# ---------------------------------------------------------------------------


class AwardService:
    """
    Human-confirmed award decision service with event-sourced lifecycle.

    ARCHITECTURAL BOUNDARY: This class has NO LLM invocation capability.
    It does not import or reference NarrativeService's generation logic.
    """

    async def create_draft_award(
        self,
        session: AsyncSession,
        rfq_id: str,
        data: AwardDecisionCreate,
        actor_principal: str,
        actor_display_name: str | None = None,
    ) -> AwardDecisionResponse:
        """
        Create a draft award decision. Validates:
        - Scoring run exists and belongs to RFQ
        - Supplier exists in scoring run results and is eligible
        - Non-Rank-1 selection requires mandatory rationale
        - No existing confirmed award for this RFQ
        """
        # Validate scoring run
        run_stmt = select(ScoringRun).where(
            ScoringRun.id == data.scoring_run_id,
            ScoringRun.rfq_id == rfq_id,
        )
        run_result = await session.execute(run_stmt)
        scoring_run = run_result.scalar_one_or_none()
        if not scoring_run:
            raise AwardNotFoundError(
                f"ScoringRun '{data.scoring_run_id}' not found for RFQ '{rfq_id}'"
            )

        # Validate supplier in scoring results
        suppliers = scoring_run.results_payload.get("suppliers", [])
        matched_supplier = next(
            (s for s in suppliers if s["quotation_id"] == data.awarded_supplier_id),
            None,
        )
        if not matched_supplier:
            raise AwardSupplierValidationError(
                f"Supplier '{data.awarded_supplier_id}' not found in ScoringRun results."
            )

        # Reject knockout-failed suppliers
        elig_status = matched_supplier.get("eligibility_status", "")
        if elig_status != "eligible":
            raise AwardSupplierValidationError(
                f"Supplier '{matched_supplier.get('supplier_name')}' is not eligible "
                f"(status: {elig_status}). Only eligible suppliers can be awarded."
            )

        supplier_rank = matched_supplier.get("rank")
        supplier_name = matched_supplier.get("supplier_name", data.awarded_supplier_id)

        # Enforce mandatory rationale for non-Rank-1 selection
        if supplier_rank is not None and supplier_rank != 1:
            if not data.non_rank1_rationale:
                raise AwardSupplierValidationError(
                    f"Supplier '{supplier_name}' is ranked #{supplier_rank}, not #1. "
                    "Selecting a supplier other than Rank #1 requires a mandatory rationale "
                    "(non_rank1_rationale field)."
                )

        # Check no existing confirmed award
        existing_stmt = select(AwardDecision).where(
            AwardDecision.rfq_id == rfq_id,
            AwardDecision.current_status == AwardStatus.CONFIRMED,
        )
        existing_result = await session.execute(existing_stmt)
        if existing_result.scalar_one_or_none():
            raise AwardConflictError(
                f"RFQ '{rfq_id}' already has a confirmed award. "
                "Revoke the existing award before creating a new one."
            )

        # Create award decision
        award = AwardDecision(
            rfq_id=rfq_id,
            scoring_run_id=data.scoring_run_id,
            narrative_generation_id=data.narrative_generation_id,
            awarded_supplier_id=data.awarded_supplier_id,
            awarded_supplier_name=supplier_name,
            awarded_supplier_rank=supplier_rank,
            non_rank1_rationale=data.non_rank1_rationale,
            current_status=AwardStatus.DRAFT,
            created_by=actor_principal,
        )
        session.add(award)
        await session.flush()

        # Create draft event
        event = AwardDecisionEvent(
            award_decision_id=award.id,
            event_type=AwardEventType.DRAFT_CREATED,
            event_number=1,
            event_payload={
                "awarded_supplier_id": data.awarded_supplier_id,
                "awarded_supplier_name": supplier_name,
                "awarded_supplier_rank": supplier_rank,
                "award_justification": data.award_justification,
                "non_rank1_rationale": data.non_rank1_rationale,
                "scoring_run_id": data.scoring_run_id,
                "narrative_generation_id": data.narrative_generation_id,
            },
            actor_principal=actor_principal,
            actor_display_name=actor_display_name,
        )
        session.add(event)

        await record_audit_event(
            db=session,
            rfq_id=rfq_id,
            event_type="AWARD_DRAFT_CREATED",
            actor_id=actor_principal,
            actor_type=ActorType.USER,
            payload={
                "award_decision_id": award.id,
                "awarded_supplier": supplier_name,
                "awarded_supplier_rank": supplier_rank,
            },
        )

        await session.commit()
        await session.refresh(award)
        return await self._build_response(session, award, rfq_id)

    async def confirm_award(
        self,
        session: AsyncSession,
        rfq_id: str,
        award_id: str,
        data: AwardConfirm,
        actor_principal: str,
        actor_display_name: str | None = None,
    ) -> AwardDecisionResponse:
        """
        Explicitly confirm a draft award. This is the ONLY path to persist
        a final supplier decision. Requires authenticated human principal.
        """
        award = await self._get_award_or_raise(session, rfq_id, award_id)

        if award.current_status != AwardStatus.DRAFT:
            raise AwardInvalidStateError(
                f"Award '{award_id}' is in status '{award.current_status.value}', "
                "not 'draft'. Only draft awards can be confirmed."
            )

        # Double-check no other confirmed award (concurrent protection)
        existing_stmt = select(AwardDecision).where(
            AwardDecision.rfq_id == rfq_id,
            AwardDecision.current_status == AwardStatus.CONFIRMED,
            AwardDecision.id != award_id,
        )
        existing_result = await session.execute(existing_stmt)
        if existing_result.scalar_one_or_none():
            raise AwardConflictError(
                f"Another award for RFQ '{rfq_id}' was confirmed concurrently. "
                "Only one confirmed award per RFQ is allowed."
            )

        now = datetime.utcnow()
        justification = data.final_justification or ""

        # Load scoring run for provenance hash
        run_stmt = select(ScoringRun).where(ScoringRun.id == award.scoring_run_id)
        run_result = await session.execute(run_stmt)
        scoring_run = run_result.scalar_one_or_none()
        scoring_run_hash = scoring_run.provenance_hash if scoring_run else ""

        # Compute provenance hash
        provenance_hash = _compute_award_provenance_hash(
            award_id=award.id,
            rfq_id=rfq_id,
            scoring_run_id=award.scoring_run_id,
            scoring_run_provenance_hash=scoring_run_hash or "",
            awarded_supplier_id=award.awarded_supplier_id,
            justification=justification,
            confirming_principal=actor_principal,
            confirmed_at=now.isoformat(),
        )

        # Update operational state
        award.current_status = AwardStatus.CONFIRMED
        award.provenance_hash = provenance_hash

        # Get next event number
        max_evt_stmt = select(func.max(AwardDecisionEvent.event_number)).where(
            AwardDecisionEvent.award_decision_id == award_id,
        )
        max_evt_result = await session.execute(max_evt_stmt)
        max_evt = max_evt_result.scalar() or 0

        # Confirmation event
        event = AwardDecisionEvent(
            award_decision_id=award.id,
            event_type=AwardEventType.CONFIRMED,
            event_number=max_evt + 1,
            event_payload={
                "final_justification": justification,
                "provenance_hash": provenance_hash,
                "confirmed_at": now.isoformat(),
            },
            actor_principal=actor_principal,
            actor_display_name=actor_display_name,
        )
        session.add(event)

        # Transition RFQ status to DECIDED
        rfq_stmt = select(RFQ).where(RFQ.id == rfq_id)
        rfq_result = await session.execute(rfq_stmt)
        rfq = rfq_result.scalar_one_or_none()
        if rfq:
            rfq.status = RFQStatus.DECIDED

        await record_audit_event(
            db=session,
            rfq_id=rfq_id,
            event_type="AWARD_CONFIRMED",
            actor_id=actor_principal,
            actor_type=ActorType.USER,
            payload={
                "award_decision_id": award.id,
                "awarded_supplier": award.awarded_supplier_name,
                "provenance_hash": provenance_hash,
            },
        )

        try:
            await session.commit()
        except IntegrityError as exc:
            await session.rollback()
            raise AwardConflictError(
                f"Another award for RFQ '{rfq_id}' was confirmed concurrently. "
                "Only one confirmed award per RFQ is allowed by database constraint."
            ) from exc

        await session.refresh(award)
        return await self._build_response(session, award, rfq_id)

    async def revoke_award(
        self,
        session: AsyncSession,
        rfq_id: str,
        award_id: str,
        data: AwardRevoke,
        actor_principal: str,
        actor_display_name: str | None = None,
    ) -> AwardDecisionResponse:
        """Revoke a confirmed award with reason. Transitions RFQ back to EVALUATING."""
        award = await self._get_award_or_raise(session, rfq_id, award_id)

        if award.current_status != AwardStatus.CONFIRMED:
            raise AwardInvalidStateError(
                f"Award '{award_id}' is in status '{award.current_status.value}', "
                "not 'confirmed'. Only confirmed awards can be revoked."
            )

        award.current_status = AwardStatus.REVOKED

        max_evt_stmt = select(func.max(AwardDecisionEvent.event_number)).where(
            AwardDecisionEvent.award_decision_id == award_id,
        )
        max_evt_result = await session.execute(max_evt_stmt)
        max_evt = max_evt_result.scalar() or 0

        event = AwardDecisionEvent(
            award_decision_id=award.id,
            event_type=AwardEventType.REVOKED,
            event_number=max_evt + 1,
            event_payload={
                "revocation_reason": data.revocation_reason,
                "revoked_at": datetime.utcnow().isoformat(),
            },
            actor_principal=actor_principal,
            actor_display_name=actor_display_name,
        )
        session.add(event)

        # Transition RFQ status back to EVALUATING
        rfq_stmt = select(RFQ).where(RFQ.id == rfq_id)
        rfq_result = await session.execute(rfq_stmt)
        rfq = rfq_result.scalar_one_or_none()
        if rfq:
            rfq.status = RFQStatus.EVALUATING

        await record_audit_event(
            db=session,
            rfq_id=rfq_id,
            event_type="AWARD_REVOKED",
            actor_id=actor_principal,
            actor_type=ActorType.USER,
            payload={
                "award_decision_id": award.id,
                "revocation_reason": data.revocation_reason,
            },
        )

        await session.commit()
        await session.refresh(award)
        return await self._build_response(session, award, rfq_id)

    async def get_award(
        self,
        session: AsyncSession,
        rfq_id: str,
        award_id: str,
    ) -> AwardDecisionResponse:
        award = await self._get_award_or_raise(session, rfq_id, award_id)
        return await self._build_response(session, award, rfq_id)

    async def list_awards(
        self,
        session: AsyncSession,
        rfq_id: str,
    ) -> list[AwardDecisionResponse]:
        stmt = (
            select(AwardDecision)
            .where(AwardDecision.rfq_id == rfq_id)
            .order_by(desc(AwardDecision.created_at))
        )
        result = await session.execute(stmt)
        responses = []
        for a in result.scalars().all():
            responses.append(await self._build_response(session, a, rfq_id))
        return responses

    async def get_current_award(
        self,
        session: AsyncSession,
        rfq_id: str,
    ) -> AwardDecisionResponse | None:
        """Get the current non-revoked confirmed award, if any."""
        stmt = select(AwardDecision).where(
            AwardDecision.rfq_id == rfq_id,
            AwardDecision.current_status == AwardStatus.CONFIRMED,
        )
        result = await session.execute(stmt)
        award = result.scalar_one_or_none()
        if not award:
            return None
        return await self._build_response(session, award, rfq_id)

    # -----------------------------------------------------------------------
    # PRIVATE HELPERS
    # -----------------------------------------------------------------------

    async def _get_award_or_raise(
        self, session: AsyncSession, rfq_id: str, award_id: str
    ) -> AwardDecision:
        stmt = select(AwardDecision).where(
            AwardDecision.id == award_id,
            AwardDecision.rfq_id == rfq_id,
        )
        result = await session.execute(stmt)
        award = result.scalar_one_or_none()
        if not award:
            raise AwardNotFoundError(f"AwardDecision '{award_id}' not found for RFQ '{rfq_id}'")
        return award

    async def _build_response(
        self,
        session: AsyncSession,
        award: AwardDecision,
        rfq_id: str,
    ) -> AwardDecisionResponse:
        # Load events
        evt_stmt = (
            select(AwardDecisionEvent)
            .where(AwardDecisionEvent.award_decision_id == award.id)
            .order_by(AwardDecisionEvent.event_number)
        )
        evt_result = await session.execute(evt_stmt)
        events = [AwardDecisionEventResponse.model_validate(e) for e in evt_result.scalars().all()]

        # Check if based on latest scoring run
        latest_run_stmt = (
            select(ScoringRun)
            .where(ScoringRun.rfq_id == rfq_id)
            .order_by(desc(ScoringRun.run_number))
            .limit(1)
        )
        latest_result = await session.execute(latest_run_stmt)
        latest_run = latest_result.scalar_one_or_none()
        is_latest = latest_run.id == award.scoring_run_id if latest_run else True
        latest_run_id = latest_run.id if latest_run else None

        return AwardDecisionResponse(
            id=award.id,
            rfq_id=award.rfq_id,
            scoring_run_id=award.scoring_run_id,
            narrative_generation_id=award.narrative_generation_id,
            awarded_supplier_id=award.awarded_supplier_id,
            awarded_supplier_name=award.awarded_supplier_name,
            awarded_supplier_rank=award.awarded_supplier_rank,
            non_rank1_rationale=award.non_rank1_rationale,
            current_status=ResponseAwardStatus(award.current_status),
            provenance_hash=award.provenance_hash,
            created_by=award.created_by,
            created_at=award.created_at,
            events=events,
            is_based_on_latest_run=is_latest,
            latest_scoring_run_id=latest_run_id,
        )


award_service = AwardService()
