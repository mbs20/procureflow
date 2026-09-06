from decimal import Decimal

import structlog
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session, selectinload

from procureflow.models.extraction import (
    ExtractedLineItem,
    ExtractedQuotation,
    ExtractedQuotationField,
)
from procureflow.models.quotation import (
    QuotationDocument,
    QuotationStatus,
    SupplierQuotation,
)
from procureflow.schemas.extraction import ExtractedLineItemUpdate
from procureflow.schemas.quotation import SupplierQuotationCreate
from procureflow.services.extractors.base import ExtractedQuotationData
from procureflow.services.storage_service import storage_service

logger = structlog.get_logger(__name__)


class QuotationService:
    """Service handling supplier quotation lifecycles, document attachment, and extraction results."""

    # -------------------------------------------------------------------------
    # ASYNC METHODS (for FastAPI endpoints)
    # -------------------------------------------------------------------------

    async def create_quotation(
        self, session: AsyncSession, data: SupplierQuotationCreate
    ) -> SupplierQuotation:
        quotation = SupplierQuotation(
            rfq_id=data.rfq_id,
            supplier_name=data.supplier_name,
            supplier_reference=data.supplier_reference,
            status=QuotationStatus.UPLOADED,
        )
        session.add(quotation)
        await session.commit()
        return await self.get_quotation(session, quotation.id)

    async def get_quotation(
        self, session: AsyncSession, quotation_id: str
    ) -> SupplierQuotation | None:
        stmt = (
            select(SupplierQuotation)
            .where(SupplierQuotation.id == quotation_id)
            .options(
                selectinload(SupplierQuotation.documents),
                selectinload(SupplierQuotation.extractions),
            )
        )
        res = await session.execute(stmt)
        return res.scalar_one_or_none()

    async def list_quotations(
        self,
        session: AsyncSession,
        rfq_id: str | None = None,
        status: QuotationStatus | None = None,
    ) -> list[SupplierQuotation]:
        stmt = select(SupplierQuotation).options(selectinload(SupplierQuotation.documents))
        if rfq_id:
            stmt = stmt.where(SupplierQuotation.rfq_id == rfq_id)
        if status:
            stmt = stmt.where(SupplierQuotation.status == status)
        stmt = stmt.order_by(desc(SupplierQuotation.created_at))
        res = await session.execute(stmt)
        return list(res.scalars().all())

    async def attach_document(
        self,
        session: AsyncSession,
        quotation_id: str,
        filename: str,
        content: bytes,
    ) -> QuotationDocument:
        quotation = await self.get_quotation(session, quotation_id)
        if not quotation:
            raise ValueError(f"Quotation {quotation_id} not found.")

        storage_path, file_hash, mime_type, size_bytes = storage_service.save_document(
            quotation_id=quotation_id,
            filename=filename,
            content=content,
        )

        doc = QuotationDocument(
            quotation_id=quotation_id,
            filename=filename,
            storage_path=storage_path,
            file_hash=file_hash,
            mime_type=mime_type,
            size_bytes=size_bytes,
        )
        session.add(doc)
        await session.commit()
        await session.refresh(doc)
        return doc

    async def get_latest_extraction(
        self, session: AsyncSession, quotation_id: str
    ) -> ExtractedQuotation | None:
        """Retrieves the current/latest extraction with line items and fields."""
        stmt = (
            select(ExtractedQuotation)
            .where(
                ExtractedQuotation.quotation_id == quotation_id,
                ExtractedQuotation.is_current == True,  # noqa: E712
            )
            .options(
                selectinload(ExtractedQuotation.line_items),
                selectinload(ExtractedQuotation.fields),
            )
            .order_by(desc(ExtractedQuotation.extracted_at))
        )
        res = await session.execute(stmt)
        extraction = res.scalars().first()
        if not extraction:
            # Fallback to absolute latest if is_current flag wasn't set
            fallback_stmt = (
                select(ExtractedQuotation)
                .where(ExtractedQuotation.quotation_id == quotation_id)
                .options(
                    selectinload(ExtractedQuotation.line_items),
                    selectinload(ExtractedQuotation.fields),
                )
                .order_by(desc(ExtractedQuotation.extracted_at))
            )
            fallback_res = await session.execute(fallback_stmt)
            extraction = fallback_res.scalars().first()
        return extraction

    async def update_line_item(
        self,
        session: AsyncSession,
        quotation_id: str,
        line_item_id: str,
        data: ExtractedLineItemUpdate,
    ) -> ExtractedLineItem:
        """Applies human review corrections to an extracted line item."""
        stmt = (
            select(ExtractedLineItem)
            .join(ExtractedQuotation)
            .where(
                ExtractedLineItem.id == line_item_id,
                ExtractedQuotation.quotation_id == quotation_id,
            )
        )
        res = await session.execute(stmt)
        item = res.scalar_one_or_none()
        if not item:
            raise ValueError(
                f"Extracted line item {line_item_id} not found for quotation {quotation_id}."
            )

        update_dict = data.model_dump(exclude_unset=True)
        for key, val in update_dict.items():
            setattr(item, key, val)

        # Update calculated_total_price if unit_price or quantity changed.
        # Preserve item.total_price (the supplier-quoted value) unless explicitly provided in update_dict.
        if "unit_price" in update_dict or "quantity" in update_dict:
            item.calculated_total_price = Decimal(str(item.quantity)) * Decimal(
                str(item.unit_price)
            )

        item.human_corrected = True
        await session.commit()
        await session.refresh(item)
        return item

    async def update_quotation_status(
        self,
        session: AsyncSession,
        quotation_id: str,
        target_status: QuotationStatus,
        failure_reason: str | None = None,
    ) -> SupplierQuotation:
        """Updates quotation status with validation for human-in-the-loop transitions."""
        quotation = await self.get_quotation(session, quotation_id)
        if not quotation:
            raise ValueError(f"Quotation {quotation_id} not found.")

        # Human approval can only be applied from needs_review
        if (
            target_status == QuotationStatus.APPROVED
            and quotation.status != QuotationStatus.NEEDS_REVIEW
        ):
            raise ValueError(
                f"Cannot approve quotation in '{quotation.status.value}' state. Must be in 'needs_review'."
            )

        quotation.status = target_status
        if failure_reason is not None:
            quotation.failure_reason = failure_reason

        await session.commit()
        return await self.get_quotation(session, quotation_id)

    # -------------------------------------------------------------------------
    # SYNCHRONOUS METHODS (for Celery Worker tasks)
    # -------------------------------------------------------------------------

    def get_quotation_sync(self, session: Session, quotation_id: str) -> SupplierQuotation | None:
        stmt = (
            select(SupplierQuotation)
            .where(SupplierQuotation.id == quotation_id)
            .options(
                selectinload(SupplierQuotation.documents),
                selectinload(SupplierQuotation.extractions),
                selectinload(SupplierQuotation.rfq),
            )
        )
        return session.execute(stmt).scalar_one_or_none()

    def save_extraction_result_sync(
        self,
        session: Session,
        quotation_id: str,
        extracted_data: ExtractedQuotationData,
    ) -> ExtractedQuotation:
        """
        Idempotently saves extraction results while preserving full extraction history.
        Prior extractions are archived with is_current=False.
        Status transitions to needs_review (never approved directly).
        """
        quotation = self.get_quotation_sync(session, quotation_id)
        if not quotation:
            raise ValueError(f"Quotation {quotation_id} not found.")

        # 1. Archive prior extractions for audit/debugging history
        prior_stmt = (
            select(ExtractedQuotation)
            .where(ExtractedQuotation.quotation_id == quotation_id)
            .order_by(desc(ExtractedQuotation.extracted_at))
        )
        prior_extractions = list(session.execute(prior_stmt).scalars().all())
        for prev in prior_extractions:
            prev.is_current = False
        session.flush()

        version_num = len(prior_extractions) + 1
        extraction_version = f"{version_num}.0"

        # 2. Check for discrepancies between quoted and calculated totals
        for item in extracted_data.line_items:
            calc_total = (
                Decimal(str(item.quantity)) * Decimal(str(item.unit_price))
                if item.quantity is not None and item.unit_price is not None
                else None
            )
            if calc_total is not None and item.total_price is not None:
                if abs(Decimal(str(item.total_price)) - calc_total) > Decimal("0.01"):
                    warning_msg = (
                        f"Discrepancy detected for '{item.description_raw}': "
                        f"quoted total is {item.total_price}, but calculated total is {calc_total}"
                    )
                    if warning_msg not in extracted_data.validation_warnings:
                        extracted_data.validation_warnings.append(warning_msg)

        # 3. Create new authoritative current extraction
        extraction = ExtractedQuotation(
            quotation_id=quotation_id,
            extraction_model=extracted_data.extraction_model,
            extraction_version=extraction_version,
            overall_confidence=Decimal(str(extracted_data.overall_confidence)),
            is_current=True,
            raw_llm_output={"validation_warnings": extracted_data.validation_warnings},
            notes=extracted_data.notes,
        )
        session.add(extraction)
        session.flush()

        # 4. Insert line items with authoritative parser/OCR coordinates
        for item in extracted_data.line_items:
            ev_dict = item.evidence.to_dict() if item.evidence else {}
            calc_total = (
                Decimal(str(item.quantity)) * Decimal(str(item.unit_price))
                if item.quantity is not None and item.unit_price is not None
                else None
            )
            line_item = ExtractedLineItem(
                extracted_quotation_id=extraction.id,
                rfq_line_item_id=item.rfq_line_item_id,
                description_raw=item.description_raw,
                quantity=item.quantity,
                unit=item.unit,
                unit_price=item.unit_price,
                currency=item.currency,
                total_price=item.total_price,
                calculated_total_price=calc_total,
                lead_time_days=item.lead_time_days,
                confidence=item.confidence,
                source_page=item.evidence.page if item.evidence else None,
                source_evidence=ev_dict if ev_dict else None,
                source_bbox=ev_dict if ev_dict else None,
                human_corrected=False,
            )
            session.add(line_item)

        # 5. Insert quotation fields
        for field in extracted_data.fields:
            ev_dict = field.evidence.to_dict() if field.evidence else {}
            quotation_field = ExtractedQuotationField(
                extracted_quotation_id=extraction.id,
                field_name=field.field_name,
                raw_value=field.raw_value,
                normalised_value=field.normalised_value,
                confidence=field.confidence,
                source_page=field.evidence.page if field.evidence else None,
                source_evidence=ev_dict if ev_dict else None,
                source_bbox=ev_dict if ev_dict else None,
                human_corrected=False,
            )
            session.add(quotation_field)

        # 5. Update quotation status to needs_review (human-in-the-loop principle)
        quotation.status = QuotationStatus.NEEDS_REVIEW
        quotation.failure_reason = None
        if extracted_data.supplier_reference and not quotation.supplier_reference:
            quotation.supplier_reference = extracted_data.supplier_reference

        session.commit()
        session.refresh(extraction)

        logger.info(
            "Saved quotation extraction result (sync)",
            quotation_id=quotation_id,
            extraction_id=extraction.id,
            version=extraction_version,
            items_count=len(extracted_data.line_items),
        )
        return extraction


quotation_service = QuotationService()
