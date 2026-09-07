from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from procureflow.api.deps import get_db, verify_api_key
from procureflow.schemas.matrix import (
    ComparisonMatrixResponse,
    ComparisonSnapshotCreate,
    ComparisonSnapshotRead,
    NormalizationOverrideCreate,
    NormalizationOverrideRead,
    NormalizationOverrideRevert,
    RFQFXRateSetCreate,
    RFQFXRateSetRead,
)
from procureflow.services.matrix_service import matrix_service

router = APIRouter(prefix="/rfqs/{rfq_id}/matrix", tags=["Comparison Matrix"])


@router.get(
    "",
    response_model=ComparisonMatrixResponse,
    summary="Get normalized comparison matrix for an RFQ",
)
async def get_comparison_matrix(
    rfq_id: str,
    fx_rate_set_id: Annotated[
        str | None, Query(description="Optional specific FX rate set version ID")
    ] = None,
    db: AsyncSession = Depends(get_db),
) -> ComparisonMatrixResponse:
    """
    Returns the normalized apples-to-apples comparison matrix across all approved supplier quotations.
    Provides dual values (quoted vs normalized), UOM and currency conversions, alignment to RFQ line items,
    traceability evidence coordinates, and data quality warnings.
    """
    return await matrix_service.compile_comparison_matrix(
        session=db, rfq_id=rfq_id, fx_rate_set_id=fx_rate_set_id
    )


@router.get(
    "/fx-rates",
    response_model=RFQFXRateSetRead,
    summary="Get active FX rates for RFQ comparison",
)
async def get_rfq_fx_rates(
    rfq_id: str,
    db: AsyncSession = Depends(get_db),
) -> RFQFXRateSetRead:
    rate_set = await matrix_service.get_or_create_default_fx_rate_set(session=db, rfq_id=rfq_id)
    return RFQFXRateSetRead.model_validate(rate_set)


@router.post(
    "/fx-rates",
    response_model=RFQFXRateSetRead,
    status_code=status.HTTP_201_CREATED,
    summary="Configure new versioned FX rate set for RFQ",
)
async def update_rfq_fx_rates(
    rfq_id: str,
    payload: RFQFXRateSetCreate,
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(verify_api_key),
) -> RFQFXRateSetRead:
    """
    Creates a new rate-set version for the RFQ.
    Preserves historical comparison snapshots by keeping prior rate-set versions immutable.
    """
    new_rate_set = await matrix_service.update_rfq_fx_rates(
        session=db, rfq_id=rfq_id, data=payload, actor_id=api_key
    )
    return RFQFXRateSetRead.model_validate(new_rate_set)


@router.post(
    "/overrides",
    response_model=NormalizationOverrideRead,
    status_code=status.HTTP_201_CREATED,
    summary="Apply a human normalization override with audit trail",
)
async def apply_override(
    rfq_id: str,
    payload: NormalizationOverrideCreate,
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(verify_api_key),
) -> NormalizationOverrideRead:
    """
    Applies a human correction to a normalized value (e.g., custom UOM conversion factor or custom FX rate).
    Maintains append-only audit trail and supersedes prior active overrides for the same cell.
    """
    override = await matrix_service.apply_normalization_override(
        session=db, rfq_id=rfq_id, data=payload, actor_id=api_key
    )
    return NormalizationOverrideRead.model_validate(override)


@router.delete(
    "/overrides/{override_id}",
    response_model=NormalizationOverrideRead,
    summary="Revert a normalization override back to deterministic default",
)
async def revert_override(
    rfq_id: str,
    override_id: str,
    payload: NormalizationOverrideRevert | None = None,
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(verify_api_key),
) -> NormalizationOverrideRead:
    """
    Reverts a human override back to the deterministic default.
    Preserves the override row with is_active=False and records revert reason and timestamp.
    """
    revert_data = payload or NormalizationOverrideRevert()
    override = await matrix_service.revert_normalization_override(
        session=db, rfq_id=rfq_id, override_id=override_id, data=revert_data, actor_id=api_key
    )
    return NormalizationOverrideRead.model_validate(override)


@router.get(
    "/overrides",
    response_model=list[NormalizationOverrideRead],
    summary="List active normalization overrides for an RFQ",
)
async def list_overrides(
    rfq_id: str,
    db: AsyncSession = Depends(get_db),
) -> list[NormalizationOverrideRead]:
    overrides = await matrix_service.list_active_overrides(session=db, rfq_id=rfq_id)
    return [NormalizationOverrideRead.model_validate(o) for o in overrides]


@router.post(
    "/snapshots",
    response_model=ComparisonSnapshotRead,
    status_code=status.HTTP_201_CREATED,
    summary="Freeze an immutable comparison snapshot",
)
async def create_snapshot(
    rfq_id: str,
    payload: ComparisonSnapshotCreate | None = None,
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(verify_api_key),
) -> ComparisonSnapshotRead:
    """
    Freezes the current comparison matrix into a versioned, immutable snapshot.
    Guarantees reproducibility of past comparison states even if rates or rules change later.
    """
    data = payload or ComparisonSnapshotCreate()
    snapshot = await matrix_service.create_comparison_snapshot(
        session=db, rfq_id=rfq_id, data=data, actor_id=api_key
    )
    return snapshot


@router.get(
    "/snapshots",
    response_model=list[ComparisonSnapshotRead],
    summary="List historical comparison snapshots for an RFQ",
)
async def list_snapshots(
    rfq_id: str,
    db: AsyncSession = Depends(get_db),
) -> list[ComparisonSnapshotRead]:
    return await matrix_service.list_comparison_snapshots(session=db, rfq_id=rfq_id)


@router.get(
    "/snapshots/{snapshot_id}",
    response_model=ComparisonSnapshotRead,
    summary="Get a specific comparison snapshot",
)
async def get_snapshot(
    rfq_id: str,
    snapshot_id: str,
    db: AsyncSession = Depends(get_db),
) -> ComparisonSnapshotRead:
    return await matrix_service.get_comparison_snapshot(
        session=db, rfq_id=rfq_id, snapshot_id=snapshot_id
    )
