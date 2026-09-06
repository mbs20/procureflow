from typing import Any

import structlog
from celery.exceptions import MaxRetriesExceededError

from procureflow.database import get_session_factory
from procureflow.models.quotation import QuotationStatus
from procureflow.services.extractors.pipeline import extraction_pipeline
from procureflow.services.quotation_service import quotation_service
from procureflow.services.storage_service import storage_service
from procureflow.tasks.celery_app import celery_app

logger = structlog.get_logger(__name__)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=10)
def extract_quotation_task(self: Any, quotation_id: str) -> dict[str, Any]:
    """
    Celery task to asynchronously extract line items and commercial terms from an uploaded quotation.
    Retries idempotently on transient failures, archiving previous extraction runs if any.
    """
    session_factory = get_session_factory()
    logger.info(
        "Starting quotation extraction task",
        quotation_id=quotation_id,
        attempt=self.request.retries + 1,
    )

    with session_factory() as session:
        quotation = quotation_service.get_quotation_sync(session, quotation_id)
        if not quotation:
            logger.error("Quotation not found for extraction task", quotation_id=quotation_id)
            return {"error": f"Quotation {quotation_id} not found", "status": "not_found"}

        if not quotation.documents:
            error_msg = f"Quotation {quotation_id} has no uploaded documents to extract."
            quotation.status = QuotationStatus.FAILED
            quotation.failure_reason = error_msg
            session.commit()
            return {"error": error_msg, "status": "failed"}

        # Set status to extracting
        quotation.status = QuotationStatus.EXTRACTING
        quotation.failure_reason = None
        session.commit()

        try:
            # Process the latest document uploaded for this quotation
            target_doc = quotation.documents[-1]
            abs_path = storage_service.get_absolute_path(target_doc.storage_path)

            extracted_data = extraction_pipeline.process_document(
                file_path=abs_path,
                rfq=quotation.rfq,
            )

            # Idempotently save extraction result (archives previous extractions, sets status to needs_review)
            extraction = quotation_service.save_extraction_result_sync(
                session=session,
                quotation_id=quotation_id,
                extracted_data=extracted_data,
            )

            logger.info(
                "Quotation extraction completed successfully",
                quotation_id=quotation_id,
                extraction_id=extraction.id,
                line_items_count=len(extracted_data.line_items),
                status=quotation.status.value,
            )

            return {
                "quotation_id": quotation_id,
                "extraction_id": extraction.id,
                "status": quotation.status.value,
                "line_items_count": len(extracted_data.line_items),
                "warnings": extracted_data.validation_warnings,
            }

        except Exception as exc:
            logger.warning(
                "Extraction task encountered an error",
                quotation_id=quotation_id,
                error=str(exc),
                attempt=self.request.retries + 1,
            )
            # Re-read or refresh quotation before status update
            session.rollback()
            try:
                # If we have retries left, retry the task
                raise self.retry(exc=exc)
            except MaxRetriesExceededError:
                with session_factory() as fail_session:
                    q = quotation_service.get_quotation_sync(fail_session, quotation_id)
                    if q:
                        q.status = QuotationStatus.FAILED
                        q.failure_reason = (
                            f"Extraction failed after {self.max_retries} attempts: {exc}"
                        )
                        fail_session.commit()
                logger.error(
                    "Extraction task exhausted all retries",
                    quotation_id=quotation_id,
                    error=str(exc),
                )
                return {
                    "quotation_id": quotation_id,
                    "status": "failed",
                    "error": str(exc),
                }
