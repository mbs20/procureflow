"""
Phase 6 — API routes for Decision Narrative & Human Award Workflow.

Actor identity is derived from the authenticated request principal (verify_api_key),
not from arbitrary request-body strings.
"""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from procureflow.api.deps import get_db, verify_api_key
from procureflow.schemas.decision import (
    AwardConfirm,
    AwardDecisionCreate,
    AwardDecisionResponse,
    AwardRevoke,
    DecisionContextResponse,
    NarrativeGenerationRequest,
    NarrativeGenerationResponse,
    NarrativeRevisionCreate,
    NarrativeRevisionResponse,
)
from procureflow.services.award_service import (
    AwardConflictError,
    AwardDomainError,
    AwardInvalidStateError,
    AwardNotFoundError,
    AwardSupplierValidationError,
    award_service,
)
from procureflow.services.narrative_service import (
    NarrativeDomainError,
    NarrativeGenerationNotFoundError,
    NarrativeProviderError,
    NarrativeScoringRunNotFoundError,
    narrative_service,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/rfqs/{rfq_id}/decisions", tags=["decisions"])


# ---------------------------------------------------------------------------
# NARRATIVE ENDPOINTS
# ---------------------------------------------------------------------------


@router.post(
    "/narratives",
    response_model=NarrativeGenerationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate AI decision narrative from a ScoringRun",
)
async def generate_narrative(
    rfq_id: str,
    data: NarrativeGenerationRequest,
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(verify_api_key),
) -> NarrativeGenerationResponse:
    try:
        return await narrative_service.generate_narrative(
            session=db, rfq_id=rfq_id, request=data, actor_id=api_key
        )
    except NarrativeScoringRunNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except NarrativeProviderError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e)
        ) from e
    except NarrativeDomainError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get(
    "/narratives",
    response_model=list[NarrativeGenerationResponse],
    summary="List all narratives for an RFQ",
)
async def list_narratives(
    rfq_id: str,
    scoring_run_id: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> list[NarrativeGenerationResponse]:
    return await narrative_service.list_narratives(
        session=db, rfq_id=rfq_id, scoring_run_id=scoring_run_id
    )


@router.get(
    "/narratives/{narrative_id}",
    response_model=NarrativeGenerationResponse,
    summary="Get specific narrative",
)
async def get_narrative(
    rfq_id: str,
    narrative_id: str,
    db: AsyncSession = Depends(get_db),
) -> NarrativeGenerationResponse:
    try:
        return await narrative_service.get_narrative(
            session=db, rfq_id=rfq_id, narrative_id=narrative_id
        )
    except NarrativeGenerationNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.post(
    "/narratives/{narrative_id}/revisions",
    response_model=NarrativeRevisionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create append-only human revision of a narrative",
)
async def create_revision(
    rfq_id: str,
    narrative_id: str,
    data: NarrativeRevisionCreate,
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(verify_api_key),
) -> NarrativeRevisionResponse:
    try:
        return await narrative_service.create_revision(
            session=db,
            rfq_id=rfq_id,
            narrative_id=narrative_id,
            data=data,
            actor_id=api_key,
        )
    except NarrativeGenerationNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except NarrativeDomainError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get(
    "/contexts/{context_id}",
    response_model=DecisionContextResponse,
    summary="Get a specific DecisionContext",
)
async def get_decision_context(
    rfq_id: str,
    context_id: str,
    db: AsyncSession = Depends(get_db),
) -> DecisionContextResponse:
    try:
        return await narrative_service.get_decision_context(
            session=db, rfq_id=rfq_id, context_id=context_id
        )
    except NarrativeDomainError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


# ---------------------------------------------------------------------------
# AWARD ENDPOINTS
# ---------------------------------------------------------------------------


@router.post(
    "/awards",
    response_model=AwardDecisionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create draft award decision",
)
async def create_draft_award(
    rfq_id: str,
    data: AwardDecisionCreate,
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(verify_api_key),
) -> AwardDecisionResponse:
    try:
        return await award_service.create_draft_award(
            session=db,
            rfq_id=rfq_id,
            data=data,
            actor_principal=api_key,
        )
    except AwardNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except AwardConflictError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e
    except AwardSupplierValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)
        ) from e
    except AwardDomainError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get(
    "/awards",
    response_model=list[AwardDecisionResponse],
    summary="List all award decisions for an RFQ",
)
async def list_awards(
    rfq_id: str,
    db: AsyncSession = Depends(get_db),
) -> list[AwardDecisionResponse]:
    return await award_service.list_awards(session=db, rfq_id=rfq_id)


@router.get(
    "/awards/current",
    response_model=AwardDecisionResponse | None,
    summary="Get current confirmed award for an RFQ",
)
async def get_current_award(
    rfq_id: str,
    db: AsyncSession = Depends(get_db),
) -> AwardDecisionResponse | None:
    return await award_service.get_current_award(session=db, rfq_id=rfq_id)


@router.get(
    "/awards/{award_id}",
    response_model=AwardDecisionResponse,
    summary="Get specific award decision",
)
async def get_award(
    rfq_id: str,
    award_id: str,
    db: AsyncSession = Depends(get_db),
) -> AwardDecisionResponse:
    try:
        return await award_service.get_award(
            session=db, rfq_id=rfq_id, award_id=award_id
        )
    except AwardNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.post(
    "/awards/{award_id}/confirm",
    response_model=AwardDecisionResponse,
    summary="Human confirms the draft award — the ONLY path to a final decision",
)
async def confirm_award(
    rfq_id: str,
    award_id: str,
    data: AwardConfirm,
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(verify_api_key),
) -> AwardDecisionResponse:
    try:
        return await award_service.confirm_award(
            session=db,
            rfq_id=rfq_id,
            award_id=award_id,
            data=data,
            actor_principal=api_key,
        )
    except AwardNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except AwardInvalidStateError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)
        ) from e
    except AwardConflictError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e
    except AwardDomainError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.post(
    "/awards/{award_id}/revoke",
    response_model=AwardDecisionResponse,
    summary="Revoke a confirmed award with reason",
)
async def revoke_award(
    rfq_id: str,
    award_id: str,
    data: AwardRevoke,
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(verify_api_key),
) -> AwardDecisionResponse:
    try:
        return await award_service.revoke_award(
            session=db,
            rfq_id=rfq_id,
            award_id=award_id,
            data=data,
            actor_principal=api_key,
        )
    except AwardNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except AwardInvalidStateError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)
        ) from e
    except AwardDomainError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
