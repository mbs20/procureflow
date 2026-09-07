from decimal import Decimal

import structlog
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session, selectinload

from procureflow.models.audit import ActorType, AuditLog
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
from procureflow.schemas.extraction import (
    ExtractedFieldUpdate,
    ExtractedLineItemCreate,
    ExtractedLineItemUpdate,
    ExtractionValidationStatus,
)
from procureflow.schemas.quotation import SupplierQuotationCreate
from procureflow.services.audit_service import record_audit_event
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
        created = await self.get_quotation(session, quotation.id)
        assert created is not None
        return created

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

    async def create_line_item(
        self,
        session: AsyncSession,
        quotation_id: str,
        data: ExtractedLineItemCreate,
        actor_id: str = "human_reviewer",
    ) -> ExtractedLineItem:
        """Manually append an extracted line item missed by the parser, marking it as human-corrected."""
        extraction = await self.get_latest_extraction(session, quotation_id)
        if not extraction:
            raise ValueError(f"No active extraction found for quotation {quotation_id}.")

        quotation = await self.get_quotation(session, quotation_id)
        if not quotation:
            raise ValueError(f"Quotation {quotation_id} not found.")

        qty = data.quantity
        unit_price = data.unit_price
        calc_total = qty * unit_price
        quoted_total = data.total_price if data.total_price is not None else calc_total

        new_item = ExtractedLineItem(
            extracted_quotation_id=extraction.id,
            rfq_line_item_id=data.rfq_line_item_id,
            description_raw=data.description_raw,
            quantity=qty,
            unit=data.unit,
            unit_price=unit_price,
            currency=data.currency,
            total_price=quoted_total,
            calculated_total_price=calc_total,
            lead_time_days=data.lead_time_days,
            confidence=Decimal("1.0"),
            human_corrected=True,
            is_removed=False,
        )
        session.add(new_item)
        await session.flush()

        await record_audit_event(
            db=session,
            rfq_id=quotation.rfq_id,
            event_type="LINE_ITEM_ADDED",
            actor_id=actor_id,
            actor_type=ActorType.USER,
            payload={
                "quotation_id": quotation_id,
                "line_item_id": new_item.id,
                "description_raw": new_item.description_raw,
                "quantity": float(new_item.quantity),
                "unit_price": float(new_item.unit_price),
                "total_price": float(new_item.total_price),
                "calculated_total_price": float(new_item.calculated_total_price or 0),
            },
        )

        await session.commit()
        await session.refresh(new_item)
        return new_item

    async def update_line_item(
        self,
        session: AsyncSession,
        quotation_id: str,
        line_item_id: str,
        data: ExtractedLineItemUpdate,
        actor_id: str = "human_reviewer",
    ) -> ExtractedLineItem:
        """
        Applies human review corrections to an extracted line item.
        Preserves supplier-quoted total_price vs calculated_total_price, and records audit trail.
        """
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

        quotation = await self.get_quotation(session, quotation_id)
        rfq_id = quotation.rfq_id if quotation else ""

        update_dict = data.model_dump(exclude_unset=True)
        previous_values = {k: getattr(item, k) for k in update_dict.keys()}

        for key, val in update_dict.items():
            setattr(item, key, val)

        # Recalculate calculated_total_price if unit_price or quantity changed.
        # CRITICAL: Preserve item.total_price (the supplier-quoted value) unless explicitly provided in update_dict!
        if "unit_price" in update_dict or "quantity" in update_dict:
            item.calculated_total_price = float(
                Decimal(str(item.quantity)) * Decimal(str(item.unit_price))
            )

        item.human_corrected = True

        # Convert Decimal values for JSON audit serialization
        audit_prev = {
            k: float(v) if isinstance(v, Decimal) else v for k, v in previous_values.items()
        }
        audit_new = {k: float(v) if isinstance(v, Decimal) else v for k, v in update_dict.items()}

        if rfq_id:
            await record_audit_event(
                db=session,
                rfq_id=rfq_id,
                event_type="LINE_ITEM_CORRECTED",
                actor_id=actor_id,
                actor_type=ActorType.USER,
                payload={
                    "quotation_id": quotation_id,
                    "line_item_id": line_item_id,
                    "previous_values": audit_prev,
                    "new_values": audit_new,
                    "supplier_quoted_total": float(item.total_price),
                    "calculated_total_price": float(item.calculated_total_price or 0),
                },
            )

        await session.commit()
        await session.refresh(item)
        return item

    async def soft_delete_line_item(
        self,
        session: AsyncSession,
        quotation_id: str,
        line_item_id: str,
        reason: str | None = None,
        actor_id: str = "human_reviewer",
    ) -> ExtractedLineItem:
        """
        Soft-delete an extracted line item for auditability.
        Never hard-deletes parser-generated items.
        """
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

        quotation = await self.get_quotation(session, quotation_id)
        rfq_id = quotation.rfq_id if quotation else ""

        item.is_removed = True
        item.removal_reason = reason or "Excluded by reviewer"
        item.human_corrected = True

        if rfq_id:
            await record_audit_event(
                db=session,
                rfq_id=rfq_id,
                event_type="LINE_ITEM_EXCLUDED",
                actor_id=actor_id,
                actor_type=ActorType.USER,
                payload={
                    "quotation_id": quotation_id,
                    "line_item_id": line_item_id,
                    "description_raw": item.description_raw,
                    "reason": item.removal_reason,
                },
            )

        await session.commit()
        await session.refresh(item)
        return item

    async def restore_line_item(
        self,
        session: AsyncSession,
        quotation_id: str,
        line_item_id: str,
        actor_id: str = "human_reviewer",
    ) -> ExtractedLineItem:
        """Restore a previously soft-deleted line item back into active extraction."""
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

        quotation = await self.get_quotation(session, quotation_id)
        rfq_id = quotation.rfq_id if quotation else ""

        item.is_removed = False
        item.removal_reason = None
        item.human_corrected = True

        if rfq_id:
            await record_audit_event(
                db=session,
                rfq_id=rfq_id,
                event_type="LINE_ITEM_RESTORED",
                actor_id=actor_id,
                actor_type=ActorType.USER,
                payload={
                    "quotation_id": quotation_id,
                    "line_item_id": line_item_id,
                    "description_raw": item.description_raw,
                },
            )

        await session.commit()
        await session.refresh(item)
        return item

    async def update_field(
        self,
        session: AsyncSession,
        quotation_id: str,
        field_id: str,
        data: ExtractedFieldUpdate,
        actor_id: str = "human_reviewer",
    ) -> ExtractedQuotationField:
        """Applies human review correction to header/commercial metadata field."""
        stmt = (
            select(ExtractedQuotationField)
            .join(ExtractedQuotation)
            .where(
                ExtractedQuotationField.id == field_id,
                ExtractedQuotation.quotation_id == quotation_id,
            )
        )
        res = await session.execute(stmt)
        field_obj = res.scalar_one_or_none()
        if not field_obj:
            raise ValueError(f"Extracted field {field_id} not found for quotation {quotation_id}.")

        quotation = await self.get_quotation(session, quotation_id)
        rfq_id = quotation.rfq_id if quotation else ""

        prev_raw = field_obj.raw_value
        if data.raw_value is not None:
            field_obj.raw_value = data.raw_value
        if data.normalised_value is not None:
            field_obj.normalised_value = data.normalised_value
        field_obj.human_corrected = True

        if rfq_id:
            await record_audit_event(
                db=session,
                rfq_id=rfq_id,
                event_type="QUOTATION_FIELD_CORRECTED",
                actor_id=actor_id,
                actor_type=ActorType.USER,
                payload={
                    "quotation_id": quotation_id,
                    "field_id": field_id,
                    "field_name": field_obj.field_name,
                    "previous_value": prev_raw,
                    "new_value": field_obj.raw_value,
                },
            )

        await session.commit()
        await session.refresh(field_obj)
        return field_obj

    def validate_extraction_for_approval(
        self, extraction: ExtractedQuotation
    ) -> ExtractionValidationStatus:
        """
        Strict server-side validation evaluating whether extraction is eligible for approval.
        Distinguishes unresolved critical blockers from ordinary or acknowledged warnings.
        """
        critical_issues: list[str] = []
        warnings: list[str] = []
        acknowledged = set(extraction.acknowledged_warnings or [])

        active_items = [it for it in extraction.line_items if not it.is_removed]

        if not active_items:
            critical_issues.append(
                "No active line items in extraction; cannot approve an empty quotation."
            )

        for item in active_items:
            # Check non-positive prices and quantities
            if item.quantity <= Decimal("0"):
                critical_issues.append(
                    f"Line item '{item.description_raw}' has invalid non-positive quantity ({item.quantity})."
                )
            if item.unit_price <= Decimal("0"):
                critical_issues.append(
                    f"Line item '{item.description_raw}' has invalid non-positive unit price ({item.unit_price})."
                )
            if item.total_price <= Decimal("0"):
                critical_issues.append(
                    f"Line item '{item.description_raw}' has invalid non-positive total price ({item.total_price})."
                )

        # Check internal currency consistency across active items
        # (Internal currency contradictions within extraction are critical blockers;
        # cross-currency differences between quotation and RFQ reference currency are valid and normalized in Phase 4)
        currencies = {item.currency.strip().upper() for item in active_items if item.currency}
        missing_currency_items = [
            item for item in active_items if not item.currency or not item.currency.strip()
        ]
        if missing_currency_items:
            critical_issues.append(
                f"{len(missing_currency_items)} line item(s) missing currency code."
            )
        if len(currencies) > 1:
            critical_issues.append(
                f"Contradictory currencies detected within quotation items ({', '.join(sorted(currencies))}). "
                "All items within an extraction must use consistent currency."
            )

        for item in active_items:
            # Check math discrepancies
            if item.calculated_total_price is not None and item.total_price is not None:
                diff = abs(item.total_price - item.calculated_total_price)
                if diff > Decimal("0.05"):
                    discrepancy_key = f"discrepancy_{item.id}"
                    if discrepancy_key not in acknowledged and item.id not in acknowledged:
                        critical_issues.append(
                            f"Line item '{item.description_raw}' has unacknowledged arithmetic discrepancy "
                            f"(Supplier quoted: {item.total_price}, Calculated: {item.calculated_total_price})."
                        )
                    else:
                        warnings.append(
                            f"Acknowledged arithmetic discrepancy on '{item.description_raw}' (diff: {diff})"
                        )

            # RFQ item match warning
            if not item.rfq_line_item_id:
                warnings.append(
                    f"Line item '{item.description_raw}' is not linked to any RFQ line item."
                )

        # Pipeline validation warnings
        pipeline_warnings = []
        if extraction.raw_llm_output and isinstance(extraction.raw_llm_output, dict):
            pipeline_warnings = extraction.raw_llm_output.get("validation_warnings", [])
        for pw in pipeline_warnings:
            if pw not in acknowledged:
                warnings.append(str(pw))

        return ExtractionValidationStatus(
            can_approve=len(critical_issues) == 0,
            critical_issues=critical_issues,
            warnings=warnings,
            acknowledged_warnings=list(acknowledged),
        )

    async def update_quotation_status(
        self,
        session: AsyncSession,
        quotation_id: str,
        target_status: QuotationStatus,
        failure_reason: str | None = None,
        acknowledged_warnings: list[str] | None = None,
        actor_id: str = "human_reviewer",
    ) -> SupplierQuotation:
        """
        Updates quotation status with strict server-side validation for human-in-the-loop review.
        Only explicit human actions can transition from needs_review to approved or rejected.
        """
        quotation = await self.get_quotation(session, quotation_id)
        if not quotation:
            raise ValueError(f"Quotation {quotation_id} not found.")

        # Human approval can only be applied from needs_review
        if target_status == QuotationStatus.APPROVED:
            if quotation.status != QuotationStatus.NEEDS_REVIEW:
                raise ValueError(
                    f"Cannot approve quotation extraction in '{quotation.status.value}' state. Must be in 'needs_review'."
                )

            extraction = await self.get_latest_extraction(session, quotation_id)
            if not extraction:
                raise ValueError(
                    f"Cannot approve quotation {quotation_id} without an active extraction."
                )

            # Record any acknowledged warnings
            if acknowledged_warnings:
                current_acks = set(extraction.acknowledged_warnings or [])
                current_acks.update(acknowledged_warnings)
                extraction.acknowledged_warnings = list(current_acks)
                await session.flush()

            # Strict server-side validation check
            val_status = self.validate_extraction_for_approval(extraction)
            if not val_status.can_approve:
                raise ValueError(
                    f"Quotation extraction cannot be approved due to critical unresolved issues: {'; '.join(val_status.critical_issues)}"
                )

            quotation.status = QuotationStatus.APPROVED
            quotation.failure_reason = None

            await record_audit_event(
                db=session,
                rfq_id=quotation.rfq_id,
                event_type="QUOTATION_EXTRACTION_APPROVED",
                actor_id=actor_id,
                actor_type=ActorType.USER,
                payload={
                    "quotation_id": quotation_id,
                    "supplier_name": quotation.supplier_name,
                    "extraction_id": extraction.id,
                    "line_items_count": len([i for i in extraction.line_items if not i.is_removed]),
                    "acknowledged_warnings": extraction.acknowledged_warnings,
                },
            )

        elif target_status == QuotationStatus.REJECTED:
            if quotation.status not in (
                QuotationStatus.NEEDS_REVIEW,
                QuotationStatus.UPLOADED,
                QuotationStatus.FAILED,
            ):
                raise ValueError(
                    f"Cannot reject quotation extraction in '{quotation.status.value}' state."
                )

            quotation.status = QuotationStatus.REJECTED
            quotation.failure_reason = failure_reason or "Rejected during human review"

            await record_audit_event(
                db=session,
                rfq_id=quotation.rfq_id,
                event_type="QUOTATION_EXTRACTION_REJECTED",
                actor_id=actor_id,
                actor_type=ActorType.USER,
                payload={
                    "quotation_id": quotation_id,
                    "supplier_name": quotation.supplier_name,
                    "rejection_reason": quotation.failure_reason,
                },
            )

        else:
            quotation.status = target_status
            if failure_reason is not None:
                quotation.failure_reason = failure_reason

        await session.commit()
        updated_quotation = await self.get_quotation(session, quotation_id)
        assert updated_quotation is not None
        return updated_quotation

    async def get_audit_logs(
        self,
        session: AsyncSession,
        quotation_id: str,
    ) -> list[AuditLog]:
        """Fetch audit log records for a given quotation."""
        quotation = await self.get_quotation(session, quotation_id)
        if not quotation:
            return []

        stmt = (
            select(AuditLog)
            .where(AuditLog.rfq_id == quotation.rfq_id)
            .order_by(desc(AuditLog.timestamp))
        )
        res = await session.execute(stmt)
        all_logs = list(res.scalars().all())

        # Filter to logs pertaining to this quotation or general RFQ events
        return [
            log
            for log in all_logs
            if log.payload and log.payload.get("quotation_id") == quotation_id
        ]

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
