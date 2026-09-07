from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from procureflow.api.deps import get_db, verify_api_key
from procureflow.schemas.scoring import (
    ScoringConfigurationCreate,
    ScoringConfigurationResponse,
    ScoringRunCreate,
    ScoringRunResponse,
    ScoringSimulationRequest,
    SensitivityRequest,
    SensitivityResponse,
    SupplierScore,
)
from procureflow.services.scoring_service import scoring_service

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/rfqs/{rfq_id}/scoring", tags=["scoring"])


@router.post(
    "/configurations",
    response_model=ScoringConfigurationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new versioned ScoringConfiguration for an RFQ",
)
async def create_scoring_configuration(
    rfq_id: str,
    data: ScoringConfigurationCreate,
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(verify_api_key),
) -> ScoringConfigurationResponse:
    return await scoring_service.create_configuration(
        session=db, rfq_id=rfq_id, data=data, actor_id="evaluator"
    )


@router.get(
    "/configurations",
    response_model=list[ScoringConfigurationResponse],
    summary="List all ScoringConfigurations for an RFQ",
)
async def list_scoring_configurations(
    rfq_id: str,
    db: AsyncSession = Depends(get_db),
) -> list[ScoringConfigurationResponse]:
    return await scoring_service.list_configurations(session=db, rfq_id=rfq_id)


@router.get(
    "/configurations/active",
    response_model=ScoringConfigurationResponse,
    summary="Get currently active ScoringConfiguration for an RFQ",
)
async def get_active_scoring_configuration(
    rfq_id: str,
    db: AsyncSession = Depends(get_db),
) -> ScoringConfigurationResponse:
    return await scoring_service.get_active_configuration(session=db, rfq_id=rfq_id)


@router.get(
    "/configurations/{configuration_id}",
    response_model=ScoringConfigurationResponse,
    summary="Get specific ScoringConfiguration by ID",
)
async def get_scoring_configuration(
    rfq_id: str,
    configuration_id: str,
    db: AsyncSession = Depends(get_db),
) -> ScoringConfigurationResponse:
    return await scoring_service.get_configuration(
        session=db, rfq_id=rfq_id, configuration_id=configuration_id
    )


@router.post(
    "/runs",
    response_model=ScoringRunResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Execute scoring against an immutable ComparisonSnapshot and freeze as an immutable ScoringRun",
)
async def execute_scoring_run(
    rfq_id: str,
    data: ScoringRunCreate,
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(verify_api_key),
) -> ScoringRunResponse:
    return await scoring_service.execute_and_save_run(
        session=db, rfq_id=rfq_id, data=data, actor_id="evaluator"
    )


@router.get(
    "/runs",
    response_model=list[ScoringRunResponse],
    summary="List all historical ScoringRuns for an RFQ",
)
async def list_scoring_runs(
    rfq_id: str,
    db: AsyncSession = Depends(get_db),
) -> list[ScoringRunResponse]:
    return await scoring_service.list_runs(session=db, rfq_id=rfq_id)


@router.get(
    "/runs/{run_id}",
    response_model=ScoringRunResponse,
    summary="Get specific historical ScoringRun by ID",
)
async def get_scoring_run(
    rfq_id: str,
    run_id: str,
    db: AsyncSession = Depends(get_db),
) -> ScoringRunResponse:
    return await scoring_service.get_run(session=db, rfq_id=rfq_id, run_id=run_id)


@router.post(
    "/simulate",
    response_model=list[SupplierScore],
    summary="In-memory simulation of scoring against a ComparisonSnapshot without persisting",
)
async def simulate_scoring(
    rfq_id: str,
    data: ScoringSimulationRequest,
    db: AsyncSession = Depends(get_db),
) -> list[SupplierScore]:
    snapshot = await scoring_service.get_snapshot(db, rfq_id, data.snapshot_id)
    if data.custom_configuration:
        config = data.custom_configuration
    elif data.configuration_id:
        cfg_record = await scoring_service.get_configuration(db, rfq_id, data.configuration_id)
        config = ScoringConfigurationCreate.model_validate(cfg_record.config_payload)
    else:
        cfg_record = await scoring_service.get_active_configuration(db, rfq_id)
        config = ScoringConfigurationCreate.model_validate(cfg_record.config_payload)

    return scoring_service.evaluate_scoring(snapshot.matrix_data, config)


@router.post(
    "/sensitivity",
    response_model=SensitivityResponse,
    summary="Run in-memory sensitivity sweeps and bisection breakeven analysis against a ComparisonSnapshot",
)
async def run_sensitivity_analysis(
    rfq_id: str,
    data: SensitivityRequest,
    db: AsyncSession = Depends(get_db),
) -> SensitivityResponse:
    return await scoring_service.run_sensitivity_analysis(session=db, rfq_id=rfq_id, req=data)
