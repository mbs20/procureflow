from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from procureflow.api.deps import get_db
from procureflow.models.quotation import QuotationStatus
from procureflow.schemas.extraction import (
    ExtractedLineItemRead,
    ExtractedLineItemUpdate,
    ExtractedQuotationRead,
)
from procureflow.schemas.quotation import (
    DocumentRead,
    JobStatusResponse,
    QuotationStatusUpdate,
    SupplierQuotationCreate,
    SupplierQuotationRead,
)
from procureflow.services.quotation_service import quotation_service
from procureflow.services.storage_service import StorageValidationError, storage_service
from procureflow.tasks.extraction import extract_quotation_task

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/quotations", tags=["quotations"])


@router.post(
    "",
    response_model=SupplierQuotationRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new supplier quotation container",
)
async def create_quotation(
    payload: SupplierQuotationCreate,
    db: AsyncSession = Depends(get_db),
) -> SupplierQuotationRead:
    quotation = await quotation_service.create_quotation(db, payload)
    return SupplierQuotationRead.model_validate(quotation)


@router.get(
    "",
    response_model=list[SupplierQuotationRead],
    summary="List supplier quotations with optional filtering",
)
async def list_quotations(
    rfq_id: Annotated[str | None, Query(description="Filter by RFQ ID")] = None,
    quotation_status: Annotated[QuotationStatus | None, Query(alias="status")] = None,
    db: AsyncSession = Depends(get_db),
) -> list[SupplierQuotationRead]:
    quotations = await quotation_service.list_quotations(db, rfq_id=rfq_id, status=quotation_status)
    return [SupplierQuotationRead.model_validate(q) for q in quotations]


@router.get(
    "/{quotation_id}",
    response_model=SupplierQuotationRead,
    summary="Get quotation details and attached documents",
)
async def get_quotation(
    quotation_id: str,
    db: AsyncSession = Depends(get_db),
) -> SupplierQuotationRead:
    quotation = await quotation_service.get_quotation(db, quotation_id)
    if not quotation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Supplier quotation '{quotation_id}' not found",
        )
    return SupplierQuotationRead.model_validate(quotation)


@router.post(
    "/{quotation_id}/documents",
    response_model=DocumentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and immutably attach a quotation document (PDF, XLSX, CSV)",
)
async def upload_quotation_document(
    quotation_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
) -> DocumentRead:
    quotation = await quotation_service.get_quotation(db, quotation_id)
    if not quotation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Supplier quotation '{quotation_id}' not found",
        )

    try:
        content = await file.read()
        filename = file.filename or "uploaded_quotation"
        doc = await quotation_service.attach_document(
            session=db,
            quotation_id=quotation_id,
            filename=filename,
            content=content,
        )
        return DocumentRead.model_validate(doc)
    except StorageValidationError as e:
        logger.warning("Document upload validation error", quotation_id=quotation_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error("Unexpected error saving document", quotation_id=quotation_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process and store document: {e}",
        ) from e


@router.get(
    "/{quotation_id}/documents/{document_id}/download",
    summary="Download the original immutable supplier quotation document",
)
async def download_quotation_document(
    quotation_id: str,
    document_id: str,
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    quotation = await quotation_service.get_quotation(db, quotation_id)
    if not quotation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Supplier quotation '{quotation_id}' not found",
        )

    doc = next((d for d in quotation.documents if d.id == document_id), None)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{document_id}' not found on quotation '{quotation_id}'",
        )

    try:
        abs_path = storage_service.get_absolute_path(doc.storage_path)
        return FileResponse(
            path=str(abs_path),
            filename=doc.filename,
            media_type=doc.mime_type,
        )
    except Exception as e:
        logger.error("File download error", document_id=document_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Storage document file could not be read: {e}",
        ) from e


@router.post(
    "/{quotation_id}/extract",
    response_model=JobStatusResponse,
    summary="Trigger or retry asynchronous document extraction",
)
async def trigger_extraction(
    quotation_id: str,
    db: AsyncSession = Depends(get_db),
) -> JobStatusResponse:
    quotation = await quotation_service.get_quotation(db, quotation_id)
    if not quotation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Supplier quotation '{quotation_id}' not found",
        )

    if not quotation.documents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot extract quotation without at least one uploaded document.",
        )

    # Transition to queued and dispatch Celery worker task
    quotation.status = QuotationStatus.QUEUED
    quotation.failure_reason = None
    await db.commit()

    extract_quotation_task.delay(quotation_id)

    return JobStatusResponse(
        quotation_id=quotation_id,
        status=QuotationStatus.QUEUED,
        message="Extraction task dispatched successfully",
    )


@router.get(
    "/{quotation_id}/extractions/latest",
    response_model=ExtractedQuotationRead,
    summary="Get current authoritative extraction result with line items, coordinates, and warnings",
)
async def get_latest_extraction(
    quotation_id: str,
    db: AsyncSession = Depends(get_db),
) -> ExtractedQuotationRead:
    quotation = await quotation_service.get_quotation(db, quotation_id)
    if not quotation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Supplier quotation '{quotation_id}' not found",
        )

    extraction = await quotation_service.get_latest_extraction(db, quotation_id)
    if not extraction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No extraction found for quotation '{quotation_id}'. Status is '{quotation.status.value}'.",
        )

    return ExtractedQuotationRead.model_validate(extraction)


@router.patch(
    "/{quotation_id}/line-items/{line_item_id}",
    response_model=ExtractedLineItemRead,
    summary="Human-in-the-loop correction of an extracted line item",
)
async def correct_line_item(
    quotation_id: str,
    line_item_id: str,
    payload: ExtractedLineItemUpdate,
    db: AsyncSession = Depends(get_db),
) -> ExtractedLineItemRead:
    try:
        updated_item = await quotation_service.update_line_item(
            session=db,
            quotation_id=quotation_id,
            line_item_id=line_item_id,
            data=payload,
        )
        return ExtractedLineItemRead.model_validate(updated_item)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


@router.patch(
    "/{quotation_id}/status",
    response_model=SupplierQuotationRead,
    summary="Explicit human review decision (approve or reject)",
)
async def update_quotation_status(
    quotation_id: str,
    payload: QuotationStatusUpdate,
    db: AsyncSession = Depends(get_db),
) -> SupplierQuotationRead:
    try:
        updated_quotation = await quotation_service.update_quotation_status(
            session=db,
            quotation_id=quotation_id,
            target_status=payload.status,
            failure_reason=payload.failure_reason,
        )
        return SupplierQuotationRead.model_validate(updated_quotation)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        ) from e
