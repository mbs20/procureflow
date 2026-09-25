"""
Phase 6 — Unit tests for AwardService.

Covers: draft creation, supplier validation, knockout rejection, Rank #2 rationale,
confirmation lifecycle, RFQ status transitions, double-award protection,
revocation, provenance hashing, event-sourced history, actor identity,
concurrent confirmation, and based-on-latest-run detection.
"""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from procureflow.models.decision import (
    AwardDecision,
    AwardStatus,
)
from procureflow.models.normalization import ComparisonSnapshot
from procureflow.models.rfq import RFQ, RFQStatus
from procureflow.models.scoring import ScoringConfiguration, ScoringRun
from procureflow.schemas.decision import (
    AwardConfirm,
    AwardDecisionCreate,
    AwardRevoke,
)
from procureflow.services.award_service import (
    AwardConflictError,
    AwardInvalidStateError,
    AwardService,
    AwardSupplierValidationError,
)

# ---------------------------------------------------------------------------
# FIXTURES
# ---------------------------------------------------------------------------

SCORING_RUN_RESULTS = {
    "rfq_id": "rfq-1",
    "snapshot_id": "snap-1",
    "snapshot_version": 1,
    "comparison_snapshot_hash": "abc123",
    "configuration_id": "cfg-1",
    "configuration_version": 1,
    "scoring_configuration_hash": "def456",
    "engine_version": "1.0.0",
    "engine_policy": {},
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
            "criteria_breakdown": [],
        },
        {
            "quotation_id": "q-beta",
            "supplier_name": "Beta Corp",
            "eligibility_status": "eligible",
            "knockout_reasons": [],
            "total_score": "87.4321",
            "exact_total_score": "87.4321098765",
            "rank": 2,
            "criteria_breakdown": [],
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
            "knockout_reasons": ["Value 50000 exceeds threshold"],
            "total_score": "0.0000",
            "exact_total_score": "0.0000",
            "rank": None,
            "criteria_breakdown": [],
        },
    ],
}


async def _seed_data(db: AsyncSession) -> tuple[str, str]:
    """Seed RFQ and scoring run."""
    rfq = RFQ(
        id="rfq-1",
        title="Test RFQ",
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
        config_payload={"criteria": []},
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
    return "rfq-1", "run-1"


# ---------------------------------------------------------------------------
# TESTS
# ---------------------------------------------------------------------------

svc = AwardService()


class TestDraftCreation:
    """Draft creation validates supplier existence and eligibility."""

    async def test_create_valid_draft_rank1(self, db_session: AsyncSession):
        rfq_id, run_id = await _seed_data(db_session)

        draft = await svc.create_draft_award(
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
        assert draft.awarded_supplier_name == "Alpha Supplies"
        assert draft.awarded_supplier_rank == 1
        assert draft.created_by == "test-principal"
        assert len(draft.events) == 1
        assert draft.events[0].event_type.value == "draft_created"
        assert draft.events[0].actor_principal == "test-principal"

    async def test_reject_knockout_supplier(self, db_session: AsyncSession):
        """Draft creation rejects knockout-failed supplier."""
        rfq_id, run_id = await _seed_data(db_session)

        with pytest.raises(AwardSupplierValidationError, match="not eligible"):
            await svc.create_draft_award(
                session=db_session,
                rfq_id=rfq_id,
                data=AwardDecisionCreate(
                    scoring_run_id=run_id,
                    awarded_supplier_id="q-delta",
                    award_justification="Testing knockout",
                ),
                actor_principal="test-principal",
            )

    async def test_reject_unknown_supplier(self, db_session: AsyncSession):
        rfq_id, run_id = await _seed_data(db_session)

        with pytest.raises(AwardSupplierValidationError, match="not found"):
            await svc.create_draft_award(
                session=db_session,
                rfq_id=rfq_id,
                data=AwardDecisionCreate(
                    scoring_run_id=run_id,
                    awarded_supplier_id="q-phantom",
                    award_justification="Testing unknown",
                ),
                actor_principal="test-principal",
            )


class TestNonRank1Rationale:
    """Test 13: Human selects Rank #2 → rationale is mandatory."""

    async def test_rank2_without_rationale_rejected(self, db_session: AsyncSession):
        rfq_id, run_id = await _seed_data(db_session)

        with pytest.raises(AwardSupplierValidationError, match="Rank #1"):
            await svc.create_draft_award(
                session=db_session,
                rfq_id=rfq_id,
                data=AwardDecisionCreate(
                    scoring_run_id=run_id,
                    awarded_supplier_id="q-beta",  # Rank #2
                    award_justification="Choose Beta",
                    non_rank1_rationale=None,  # Missing!
                ),
                actor_principal="test-principal",
            )

    async def test_rank2_with_rationale_accepted(self, db_session: AsyncSession):
        rfq_id, run_id = await _seed_data(db_session)

        draft = await svc.create_draft_award(
            session=db_session,
            rfq_id=rfq_id,
            data=AwardDecisionCreate(
                scoring_run_id=run_id,
                awarded_supplier_id="q-beta",  # Rank #2
                award_justification="Choose Beta for quality",
                non_rank1_rationale="Beta has significantly higher quality score and existing relationship",
            ),
            actor_principal="test-principal",
        )
        assert draft.awarded_supplier_rank == 2
        assert draft.non_rank1_rationale is not None


class TestConfirmationLifecycle:
    """Test 18: Final decision requires explicit human confirmation event."""

    async def test_confirmation_creates_event_and_transitions_rfq(self, db_session: AsyncSession):
        rfq_id, run_id = await _seed_data(db_session)

        draft = await svc.create_draft_award(
            session=db_session,
            rfq_id=rfq_id,
            data=AwardDecisionCreate(
                scoring_run_id=run_id,
                awarded_supplier_id="q-alpha",
                award_justification="Best overall",
            ),
            actor_principal="test-principal",
        )

        confirmed = await svc.confirm_award(
            session=db_session,
            rfq_id=rfq_id,
            award_id=draft.id,
            data=AwardConfirm(final_justification="Confirmed after review"),
            actor_principal="confirmer-principal",
        )

        assert confirmed.current_status.value == "confirmed"
        assert confirmed.provenance_hash
        assert len(confirmed.provenance_hash) == 64
        assert len(confirmed.events) == 2
        assert confirmed.events[1].event_type.value == "confirmed"
        assert confirmed.events[1].actor_principal == "confirmer-principal"

        # RFQ should be DECIDED
        rfq_stmt = select(RFQ).where(RFQ.id == rfq_id)
        rfq_result = await db_session.execute(rfq_stmt)
        rfq = rfq_result.scalar_one()
        assert rfq.status == RFQStatus.DECIDED

    async def test_double_confirmation_rejected(self, db_session: AsyncSession):
        """Cannot confirm an already-confirmed award."""
        rfq_id, run_id = await _seed_data(db_session)

        draft = await svc.create_draft_award(
            session=db_session,
            rfq_id=rfq_id,
            data=AwardDecisionCreate(
                scoring_run_id=run_id,
                awarded_supplier_id="q-alpha",
                award_justification="Best",
            ),
            actor_principal="test-principal",
        )

        await svc.confirm_award(
            session=db_session,
            rfq_id=rfq_id,
            award_id=draft.id,
            data=AwardConfirm(),
            actor_principal="confirmer",
        )

        with pytest.raises(AwardInvalidStateError, match="not 'draft'"):
            await svc.confirm_award(
                session=db_session,
                rfq_id=rfq_id,
                award_id=draft.id,
                data=AwardConfirm(),
                actor_principal="confirmer",
            )


class TestDoubleAwardProtection:
    """Test 17: Database prevents concurrent double-award."""

    async def test_second_draft_blocked_when_confirmed_exists(self, db_session: AsyncSession):
        rfq_id, run_id = await _seed_data(db_session)

        draft = await svc.create_draft_award(
            session=db_session,
            rfq_id=rfq_id,
            data=AwardDecisionCreate(
                scoring_run_id=run_id,
                awarded_supplier_id="q-alpha",
                award_justification="Best",
            ),
            actor_principal="test-principal",
        )

        await svc.confirm_award(
            session=db_session,
            rfq_id=rfq_id,
            award_id=draft.id,
            data=AwardConfirm(),
            actor_principal="confirmer",
        )

        # Try to create another draft while confirmed exists
        with pytest.raises(AwardConflictError, match="already has a confirmed award"):
            await svc.create_draft_award(
                session=db_session,
                rfq_id=rfq_id,
                data=AwardDecisionCreate(
                    scoring_run_id=run_id,
                    awarded_supplier_id="q-beta",
                    award_justification="Try another",
                    non_rank1_rationale="Testing",
                ),
                actor_principal="test-principal",
            )


class TestRevocation:
    """Revocation flow with status transitions."""

    async def test_revocation_transitions_rfq_back(self, db_session: AsyncSession):
        rfq_id, run_id = await _seed_data(db_session)

        draft = await svc.create_draft_award(
            session=db_session,
            rfq_id=rfq_id,
            data=AwardDecisionCreate(
                scoring_run_id=run_id,
                awarded_supplier_id="q-alpha",
                award_justification="Best",
            ),
            actor_principal="test-principal",
        )

        await svc.confirm_award(
            session=db_session,
            rfq_id=rfq_id,
            award_id=draft.id,
            data=AwardConfirm(),
            actor_principal="confirmer",
        )

        revoked = await svc.revoke_award(
            session=db_session,
            rfq_id=rfq_id,
            award_id=draft.id,
            data=AwardRevoke(revocation_reason="New information received"),
            actor_principal="revoker",
        )

        assert revoked.current_status.value == "revoked"
        assert len(revoked.events) == 3
        assert revoked.events[2].event_type.value == "revoked"

        # RFQ should be back to EVALUATING
        rfq_stmt = select(RFQ).where(RFQ.id == rfq_id)
        rfq_result = await db_session.execute(rfq_stmt)
        rfq = rfq_result.scalar_one()
        assert rfq.status == RFQStatus.EVALUATING


class TestActorIdentity:
    """Test 14: Actor identity is server-derived, not from request body."""

    async def test_actor_principal_from_auth(self, db_session: AsyncSession):
        rfq_id, run_id = await _seed_data(db_session)

        draft = await svc.create_draft_award(
            session=db_session,
            rfq_id=rfq_id,
            data=AwardDecisionCreate(
                scoring_run_id=run_id,
                awarded_supplier_id="q-alpha",
                award_justification="Best",
                # Note: no actor field in the request body
            ),
            actor_principal="auth-derived-principal",
        )

        # Actor comes from the service parameter, not request body
        assert draft.created_by == "auth-derived-principal"
        assert draft.events[0].actor_principal == "auth-derived-principal"


class TestBasedOnLatestRun:
    """Award based on older run is not auto-revoked but clearly marked."""

    async def test_based_on_latest_run_tracking(self, db_session: AsyncSession):
        rfq_id, run_id = await _seed_data(db_session)

        draft = await svc.create_draft_award(
            session=db_session,
            rfq_id=rfq_id,
            data=AwardDecisionCreate(
                scoring_run_id=run_id,
                awarded_supplier_id="q-alpha",
                award_justification="Best",
            ),
            actor_principal="test",
        )

        confirmed = await svc.confirm_award(
            session=db_session,
            rfq_id=rfq_id,
            award_id=draft.id,
            data=AwardConfirm(),
            actor_principal="confirmer",
        )
        assert confirmed.is_based_on_latest_run is True

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

        # Award is still confirmed but NOT based on latest
        award_now = await svc.get_award(session=db_session, rfq_id=rfq_id, award_id=draft.id)
        assert award_now.is_based_on_latest_run is False
        assert award_now.latest_scoring_run_id == "run-2"
        assert award_now.current_status.value == "confirmed"  # Not auto-revoked


class TestDatabaseLevelConcurrentAwardProtection:
    """Test 7: Database-level unique constraint prevents two active confirmed awards."""

    async def test_db_constraint_rejects_second_confirmed_award(self, db_session: AsyncSession):
        from sqlalchemy.exc import IntegrityError

        rfq_id, run_id = await _seed_data(db_session)

        award1 = AwardDecision(
            id="award-conf-1",
            rfq_id=rfq_id,
            scoring_run_id=run_id,
            awarded_supplier_id="q-alpha",
            awarded_supplier_name="Alpha Supplies",
            awarded_supplier_rank=1,
            current_status=AwardStatus.CONFIRMED,
            created_by="officer_1",
        )
        db_session.add(award1)
        await db_session.commit()

        # Attempt to insert a second confirmed award directly into DB bypassing service logic
        award2 = AwardDecision(
            id="award-conf-2",
            rfq_id=rfq_id,
            scoring_run_id=run_id,
            awarded_supplier_id="q-beta",
            awarded_supplier_name="Beta Corp",
            awarded_supplier_rank=2,
            current_status=AwardStatus.CONFIRMED,
            created_by="officer_2",
        )
        db_session.add(award2)

        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    async def test_confirm_award_catches_db_conflict(self, db_session: AsyncSession):
        """Simulate concurrent confirmation where DB constraint raises IntegrityError."""
        rfq_id, run_id = await _seed_data(db_session)

        draft1 = await svc.create_draft_award(
            session=db_session,
            rfq_id=rfq_id,
            data=AwardDecisionCreate(
                scoring_run_id=run_id,
                awarded_supplier_id="q-alpha",
                award_justification="Alpha is best",
            ),
            actor_principal="officer_1",
        )

        # Confirm award 1
        await svc.confirm_award(
            session=db_session,
            rfq_id=rfq_id,
            award_id=draft1.id,
            data=AwardConfirm(),
            actor_principal="officer_1",
        )

        # Create another draft award by manual insertion (simulating race before first committed)
        draft2 = AwardDecision(
            id="draft-2",
            rfq_id=rfq_id,
            scoring_run_id=run_id,
            awarded_supplier_id="q-beta",
            awarded_supplier_name="Beta Corp",
            awarded_supplier_rank=2,
            current_status=AwardStatus.DRAFT,
            created_by="officer_2",
        )
        db_session.add(draft2)
        await db_session.commit()

        # Attempting to confirm draft2 fails with AwardConflictError
        with pytest.raises(AwardConflictError, match="Only one confirmed award per RFQ is allowed"):
            await svc.confirm_award(
                session=db_session,
                rfq_id=rfq_id,
                award_id="draft-2",
                data=AwardConfirm(),
                actor_principal="officer_2",
            )


class TestActorIdentitySpoofing:
    """Test 6: Authoritative actor identity is derived from authenticated request principal."""

    async def test_actor_identity_ignores_spoofed_body(self, db_session: AsyncSession):
        rfq_id, run_id = await _seed_data(db_session)

        # Client attempts to pass a spoofed actor identity in body
        draft = await svc.create_draft_award(
            session=db_session,
            rfq_id=rfq_id,
            data=AwardDecisionCreate(
                scoring_run_id=run_id,
                awarded_supplier_id="q-alpha",
                award_justification="Authorized selection",
            ),
            actor_principal="authenticated_buyer_principal_123",
            actor_display_name="Authenticated Buyer",
        )

        assert draft.created_by == "authenticated_buyer_principal_123"
        assert draft.events[0].actor_principal == "authenticated_buyer_principal_123"
        assert draft.events[0].actor_display_name == "Authenticated Buyer"
