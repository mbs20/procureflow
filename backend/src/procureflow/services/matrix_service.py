from __future__ import annotations

import datetime as dt
from decimal import Decimal
from typing import Any

import structlog
from fastapi import HTTPException, status
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from procureflow.models.audit import ActorType
from procureflow.models.extraction import (
    ExtractedLineItem,
    ExtractedQuotation,
)
from procureflow.models.normalization import (
    ComparisonSnapshot,
    NormalizationOverride,
    RFQFXRateSet,
)
from procureflow.models.quotation import QuotationStatus, SupplierQuotation
from procureflow.models.rfq import RFQ
from procureflow.schemas.matrix import (
    ComparisonMatrixResponse,
    ComparisonSnapshotCreate,
    ComparisonSnapshotRead,
    MatrixExtraItem,
    MatrixLineItemCell,
    MatrixRequiredRow,
    MatrixSupplierHeader,
    NormalizationOverrideCreate,
    NormalizationOverrideRevert,
    RFQFXRateSetCreate,
    RFQFXRateSetRead,
)
from procureflow.services.audit_service import record_audit_event
from procureflow.services.normalization.currency import (
    NormalizationStatus,
    RFQFXRateProvider,
    StaticFXRateProvider,
    convert_currency,
)
from procureflow.services.normalization.lead_time import normalize_lead_time
from procureflow.services.normalization.payment_terms import normalize_payment_terms
from procureflow.services.normalization.uom import normalize_uom_and_price

logger = structlog.get_logger(__name__)

NORMALIZATION_ENGINE_VERSION = "1.0.0"


class MatrixService:
    """
    Core procurement comparison matrix service.
    Aligns approved supplier extractions against RFQ line items, runs deterministic
    normalization across currency, UOM price basis, lead times, and payment terms,
    handles append-only human overrides, and freezes versioned comparison snapshots.
    """

    async def get_or_create_default_fx_rate_set(
        self, session: AsyncSession, rfq_id: str, base_currency: str = "USD"
    ) -> RFQFXRateSet:
        """Loads current RFQ FX rate set, or initializes version 1 using synthetic static test rates."""
        stmt = (
            select(RFQFXRateSet)
            .where(RFQFXRateSet.rfq_id == rfq_id, RFQFXRateSet.is_current == True)  # noqa: E712
            .order_by(desc(RFQFXRateSet.version))
        )
        res = await session.execute(stmt)
        rate_set = res.scalar_one_or_none()

        if not rate_set:
            # Create default version 1 with synthetic rates
            static_prov = StaticFXRateProvider()
            raw_rates = {k: float(v) for k, v in static_prov.DEFAULT_SYNTHETIC_RATES_USD.items()}
            rate_set = RFQFXRateSet(
                rfq_id=rfq_id,
                version=1,
                base_currency=base_currency.upper(),
                effective_date=dt.date.today(),
                provider_id="synthetic_static_test_rates",
                is_synthetic=True,
                rates=raw_rates,
                created_by="system",
                is_current=True,
            )
            session.add(rate_set)
            await session.commit()
            await session.refresh(rate_set)

        return rate_set

    async def update_rfq_fx_rates(
        self,
        session: AsyncSession,
        rfq_id: str,
        data: RFQFXRateSetCreate,
        actor_id: str = "system",
    ) -> RFQFXRateSet:
        """
        Creates a new versioned RFQFXRateSet without mutating historical sets.
        Prior comparison snapshots referencing earlier versions remain reproducible.
        """
        # Find highest version
        stmt = select(func.max(RFQFXRateSet.version)).where(RFQFXRateSet.rfq_id == rfq_id)
        res = await session.execute(stmt)
        max_ver = res.scalar() or 0
        new_version = max_ver + 1

        # Mark previous current sets as not current
        prev_stmt = select(RFQFXRateSet).where(
            RFQFXRateSet.rfq_id == rfq_id,
            RFQFXRateSet.is_current == True,  # noqa: E712
        )
        prev_sets = (await session.execute(prev_stmt)).scalars().all()
        for p in prev_sets:
            p.is_current = False

        new_rate_set = RFQFXRateSet(
            rfq_id=rfq_id,
            version=new_version,
            base_currency=data.base_currency.upper(),
            effective_date=data.effective_date,
            provider_id=data.provider_id,
            is_synthetic=data.is_synthetic,
            rates=data.rates,
            created_by=actor_id,
            is_current=True,
        )
        session.add(new_rate_set)
        await session.flush()

        await record_audit_event(
            db=session,
            rfq_id=rfq_id,
            event_type="RFQ_FX_RATES_UPDATED",
            actor_id=actor_id,
            actor_type=ActorType.USER,
            payload={
                "rate_set_id": new_rate_set.id,
                "version": new_version,
                "base_currency": new_rate_set.base_currency,
                "effective_date": new_rate_set.effective_date.isoformat(),
                "rates": new_rate_set.rates,
                "is_synthetic": new_rate_set.is_synthetic,
            },
        )

        await session.commit()
        await session.refresh(new_rate_set)
        return new_rate_set

    async def apply_normalization_override(
        self,
        session: AsyncSession,
        rfq_id: str,
        data: NormalizationOverrideCreate,
        actor_id: str = "human_reviewer",
    ) -> NormalizationOverride:
        """
        Applies a human reviewer normalization override in an append-only manner.
        Supercedes any prior active override for the same target field.
        """
        # Deactivate any existing active override for this field
        stmt = select(NormalizationOverride).where(
            NormalizationOverride.rfq_id == rfq_id,
            NormalizationOverride.quotation_id == data.quotation_id,
            NormalizationOverride.line_item_id == data.line_item_id,
            NormalizationOverride.field_name == data.field_name,
            NormalizationOverride.is_active == True,  # noqa: E712
        )
        existing_overrides = (await session.execute(stmt)).scalars().all()
        for ex in existing_overrides:
            ex.is_active = False
            ex.reverted_at = dt.datetime.utcnow()
            ex.reverted_by = actor_id
            ex.revert_reason = "Superseded by new human override"

        # Capture original value
        orig_val: dict[str, Any] = {}
        if data.line_item_id:
            item_stmt = select(ExtractedLineItem).where(ExtractedLineItem.id == data.line_item_id)
            item = (await session.execute(item_stmt)).scalar_one_or_none()
            if item:
                orig_val = {
                    "description": item.description_raw,
                    "quantity": float(item.quantity),
                    "unit": item.unit,
                    "unit_price": float(item.unit_price),
                    "currency": item.currency,
                    "lead_time_days": item.lead_time_days,
                }

        override = NormalizationOverride(
            rfq_id=rfq_id,
            quotation_id=data.quotation_id,
            line_item_id=data.line_item_id,
            field_name=data.field_name,
            original_value=orig_val,
            override_value=data.override_value,
            override_reason=data.override_reason,
            actor_id=actor_id,
            is_active=True,
        )
        session.add(override)
        await session.flush()

        await record_audit_event(
            db=session,
            rfq_id=rfq_id,
            event_type="NORMALIZATION_OVERRIDE_APPLIED",
            actor_id=actor_id,
            actor_type=ActorType.USER,
            payload={
                "override_id": override.id,
                "quotation_id": data.quotation_id,
                "line_item_id": data.line_item_id,
                "field_name": data.field_name,
                "override_value": data.override_value,
                "override_reason": data.override_reason,
            },
        )

        await session.commit()
        await session.refresh(override)
        return override

    async def revert_normalization_override(
        self,
        session: AsyncSession,
        rfq_id: str,
        override_id: str,
        data: NormalizationOverrideRevert,
        actor_id: str = "human_reviewer",
    ) -> NormalizationOverride:
        """
        Reverts an override back to deterministic default calculation.
        Preserves the record by setting is_active=False and recording audit metadata.
        """
        stmt = select(NormalizationOverride).where(
            NormalizationOverride.id == override_id,
            NormalizationOverride.rfq_id == rfq_id,
        )
        res = await session.execute(stmt)
        override = res.scalar_one_or_none()
        if not override:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Normalization override '{override_id}' not found for RFQ '{rfq_id}'",
            )

        override.is_active = False
        override.reverted_at = dt.datetime.utcnow()
        override.reverted_by = actor_id
        override.revert_reason = data.revert_reason

        await record_audit_event(
            db=session,
            rfq_id=rfq_id,
            event_type="NORMALIZATION_OVERRIDE_REVERTED",
            actor_id=actor_id,
            actor_type=ActorType.USER,
            payload={
                "override_id": override.id,
                "quotation_id": override.quotation_id,
                "line_item_id": override.line_item_id,
                "field_name": override.field_name,
                "revert_reason": data.revert_reason,
            },
        )

        await session.commit()
        await session.refresh(override)
        return override

    async def list_active_overrides(
        self, session: AsyncSession, rfq_id: str
    ) -> list[NormalizationOverride]:
        stmt = (
            select(NormalizationOverride)
            .where(
                NormalizationOverride.rfq_id == rfq_id,
                NormalizationOverride.is_active == True,  # noqa: E712
            )
            .order_by(NormalizationOverride.created_at)
        )
        res = await session.execute(stmt)
        return list(res.scalars().all())

    async def compile_comparison_matrix(
        self,
        session: AsyncSession,
        rfq_id: str,
        fx_rate_set_id: str | None = None,
    ) -> ComparisonMatrixResponse:
        """
        Compiles the normalized supplier comparison matrix for an RFQ.
        Aligns approved quotation extractions against RFQ line items.
        Executes deterministic currency, UOM price basis, lead time, and payment terms normalization.
        Applies active human overrides with full traceability.
        """
        # 1. Load RFQ with required line items
        rfq_stmt = (
            select(RFQ)
            .where(RFQ.id == rfq_id)
            .options(
                selectinload(RFQ.line_items),
            )
        )
        rfq_res = await session.execute(rfq_stmt)
        rfq = rfq_res.scalar_one_or_none()
        if not rfq:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"RFQ '{rfq_id}' not found",
            )

        ref_currency = rfq.reference_currency.upper()

        # 2. Load FX rate set
        if fx_rate_set_id:
            fx_stmt = select(RFQFXRateSet).where(RFQFXRateSet.id == fx_rate_set_id)
            fx_res = await session.execute(fx_stmt)
            fx_set = fx_res.scalar_one_or_none()
        else:
            fx_set = await self.get_or_create_default_fx_rate_set(session, rfq_id, ref_currency)

        if not fx_set:
            fx_set = await self.get_or_create_default_fx_rate_set(session, rfq_id, ref_currency)

        # Initialize FX rate provider
        fx_provider = RFQFXRateProvider(
            base_currency=fx_set.base_currency,
            rates=fx_set.rates,
            effective_date=fx_set.effective_date,
            provider_id=fx_set.provider_id,
            rate_set_version=fx_set.version,
            is_synthetic=fx_set.is_synthetic,
        )

        # 3. Load active human overrides
        active_overrides = await self.list_active_overrides(session, rfq_id)
        override_map: dict[tuple[str, str | None, str], NormalizationOverride] = {
            (o.quotation_id, o.line_item_id, o.field_name): o for o in active_overrides
        }

        # 4. Load quotations (approved or available for leveling)
        # Note: We prioritize approved quotations; if none approved, we include needs_review for preliminary preview
        q_stmt = (
            select(SupplierQuotation)
            .where(
                SupplierQuotation.rfq_id == rfq_id,
                SupplierQuotation.status.in_(
                    [QuotationStatus.APPROVED, QuotationStatus.NEEDS_REVIEW]
                ),
            )
            .options(
                selectinload(SupplierQuotation.extractions).selectinload(
                    ExtractedQuotation.line_items
                ),
                selectinload(SupplierQuotation.extractions).selectinload(ExtractedQuotation.fields),
                selectinload(SupplierQuotation.documents),
            )
            .order_by(SupplierQuotation.created_at)
        )
        quotations = list((await session.execute(q_stmt)).scalars().all())

        suppliers_headers: list[MatrixSupplierHeader] = []
        quotation_extractions: dict[str, ExtractedQuotation] = {}
        all_extra_items: list[MatrixExtraItem] = []
        warnings_summary: list[str] = []

        total_rfq_items = len(rfq.line_items)

        # 5. Process quotation headers & commercial terms
        for q in quotations:
            # Find latest/current extraction
            curr_extraction = next((e for e in q.extractions if e.is_current), None)
            if not curr_extraction and q.extractions:
                curr_extraction = q.extractions[0]

            if not curr_extraction:
                continue

            quotation_extractions[q.id] = curr_extraction

            # Extract commercial metadata fields
            payment_terms_field = next(
                (f for f in curr_extraction.fields if f.field_name == "payment_terms"), None
            )
            raw_payment_terms = payment_terms_field.raw_value if payment_terms_field else None

            # Payment Terms Normalization
            pt_res = normalize_payment_terms(raw_payment_terms)
            pt_override = override_map.get((q.id, None, "payment_terms"))
            pt_display = pt_res.display_text
            pt_code = pt_res.term_code
            if pt_override and "payment_terms" in pt_override.override_value:
                pt_display = str(pt_override.override_value["payment_terms"])
                pt_code = str(pt_override.override_value.get("term_code", "OVERRIDDEN"))

            # Overall Lead Time Normalization
            # Check line items or fields for overall lead time
            lead_time_field = next(
                (f for f in curr_extraction.fields if "lead_time" in f.field_name), None
            )
            raw_overall_lead_time = lead_time_field.raw_value if lead_time_field else None
            if not raw_overall_lead_time:
                # Fallback to max line item lead time
                line_days = [
                    it.lead_time_days
                    for it in curr_extraction.line_items
                    if it.lead_time_days and not it.is_removed
                ]
                if line_days:
                    raw_overall_lead_time = f"{max(line_days)} days"

            lt_res = normalize_lead_time(raw_overall_lead_time)
            lt_override = override_map.get((q.id, None, "lead_time"))
            lt_display = lt_res.display_text
            lt_days = lt_res.canonical_days
            if lt_override and "lead_time_days" in lt_override.override_value:
                lt_days = int(lt_override.override_value["lead_time_days"])
                lt_display = f"{lt_days} d (overridden)"

            # Determine primary quotation currency
            q_currencies = [
                it.currency
                for it in curr_extraction.line_items
                if it.currency and not it.is_removed
            ]
            orig_currency = q_currencies[0].upper() if q_currencies else "USD"

            # Check coverage
            active_items = [it for it in curr_extraction.line_items if not it.is_removed]
            mapped_rfq_item_ids = {
                it.rfq_line_item_id for it in active_items if it.rfq_line_item_id
            }
            quoted_count = len(mapped_rfq_item_ids)
            coverage_pct = (
                round((quoted_count / total_rfq_items) * 100.0, 1) if total_rfq_items > 0 else 0.0
            )

            # Quoted grand total (supplier total)
            quoted_grand_total = sum(float(it.total_price) for it in active_items)
            supp_warnings: list[str] = []

            # Check for non-line-item commercial components (freight, tax, discount, surcharge, customs)
            commercial_fields = [
                f
                for f in curr_extraction.fields
                if f.field_name.lower()
                in {
                    "freight",
                    "tax",
                    "discount",
                    "surcharge",
                    "shipping",
                    "customs",
                    "duty",
                    "duties",
                    "handling",
                    "insurance",
                }
                and f.raw_value
                and f.raw_value.strip()
            ]
            commercial_component_names = [f.field_name for f in commercial_fields]

            # Check if stated grand total differs from sum of line items
            stated_total_field = next(
                (
                    f
                    for f in curr_extraction.fields
                    if f.field_name.lower() in {"stated_grand_total", "grand_total", "total_amount"}
                ),
                None,
            )
            stated_grand_total: float | None = None
            if stated_total_field and stated_total_field.raw_value:
                try:
                    stated_grand_total = float(Decimal(str(stated_total_field.raw_value)))
                except Exception:
                    pass

            has_commercial_variance = False
            if (
                stated_grand_total is not None
                and abs(stated_grand_total - quoted_grand_total) > 0.01
            ):
                has_commercial_variance = True
                supp_warnings.append(
                    f"Stated quotation grand total ({stated_grand_total:.2f} {orig_currency}) differs from line-item sum ({quoted_grand_total:.2f} {orig_currency})."
                )

            has_commercial_components = len(commercial_fields) > 0 or has_commercial_variance
            if commercial_component_names:
                supp_warnings.append(
                    f"Commercial envelope includes non-item components: {', '.join(commercial_component_names)}."
                )

            header = MatrixSupplierHeader(
                quotation_id=q.id,
                supplier_name=q.supplier_name,
                supplier_reference=q.supplier_reference,
                status=q.status.value,
                extraction_version=curr_extraction.extraction_version,
                original_currency=orig_currency,
                rfq_coverage_pct=coverage_pct,
                quoted_items_count=quoted_count,
                total_rfq_items=total_rfq_items,
                quoted_grand_total=quoted_grand_total,
                normalized_line_item_subtotal=0.0,  # will sum in row loop
                normalized_comparable_total=None,  # will set in row loop
                has_unknown_commercial_components=has_commercial_components,
                payment_terms_original=raw_payment_terms or "Not specified",
                payment_terms_normalized=pt_display,
                payment_terms_code=pt_code,
                overall_lead_time_original=str(raw_overall_lead_time or "Not specified"),
                overall_lead_time_normalized=lt_display,
                overall_lead_time_days=lt_days,
                unresolved_count=0,
                warnings_count=len(supp_warnings),
                warnings=supp_warnings,
            )
            suppliers_headers.append(header)

        # 6. Build Required Line Item Rows
        required_rows: list[MatrixRequiredRow] = []
        supplier_subtotals: dict[str, Decimal] = {
            s.quotation_id: Decimal("0.0") for s in suppliers_headers
        }
        supplier_unresolved_counts: dict[str, int] = {s.quotation_id: 0 for s in suppliers_headers}

        for rfq_item in sorted(rfq.line_items, key=lambda x: x.position):
            row_cells: dict[str, MatrixLineItemCell] = {}

            for supp in suppliers_headers:
                qid = supp.quotation_id
                extraction = quotation_extractions.get(qid)
                if not extraction:
                    continue

                # Find line item mapped to this RFQ item
                matched_item = next(
                    (
                        it
                        for it in extraction.line_items
                        if it.rfq_line_item_id == rfq_item.id and not it.is_removed
                    ),
                    None,
                )

                if not matched_item:
                    # Not quoted by this supplier
                    row_cells[qid] = MatrixLineItemCell(
                        is_quoted=False,
                        overall_cell_status=NormalizationStatus.NOT_QUOTED,
                        warnings=[f"Item not quoted by {supp.supplier_name}"],
                    )
                    continue

                # 1. UOM & Price Basis Normalization
                uom_override = (
                    override_map.get((qid, matched_item.id, "uom_factor"))
                    or override_map.get((qid, matched_item.id, "conversion_factor"))
                    or override_map.get((qid, matched_item.id, "uom"))
                )
                explicit_factor = None
                if uom_override:
                    val = uom_override.override_value
                    explicit_factor = (
                        val.get("conversion_factor") or val.get("uom_factor") or val.get("factor")
                    )

                uom_res = normalize_uom_and_price(
                    quoted_quantity=matched_item.quantity,
                    quoted_uom=matched_item.unit,
                    quoted_unit_price=matched_item.unit_price,
                    rfq_uom=rfq_item.unit,
                    explicit_conversion_factor=explicit_factor,
                )

                # 2. Currency Normalization
                item_currency = (
                    matched_item.currency.upper()
                    if matched_item.currency
                    else supp.original_currency
                )
                price_to_convert: Decimal | None = uom_res.normalized_unit_price

                fx_override = override_map.get((qid, matched_item.id, "fx_rate"))
                fx_rate_used: float | None = None
                fx_eff_date: str | None = None
                fx_prov_id: str | None = None
                fx_status: NormalizationStatus = NormalizationStatus.NORMALIZED
                fx_warn: str | None = None
                norm_unit_price: Decimal | None = None

                if fx_override and "fx_rate" in fx_override.override_value:
                    custom_fx_rate = Decimal(str(fx_override.override_value["fx_rate"]))
                    if price_to_convert is not None:
                        norm_unit_price = (price_to_convert * custom_fx_rate).quantize(
                            Decimal("0.0001")
                        )
                    fx_status = NormalizationStatus.HUMAN_OVERRIDDEN
                    fx_rate_used = float(custom_fx_rate)
                    fx_eff_date = str(fx_set.effective_date)
                    fx_prov_id = "human_override"
                    fx_warn = None
                else:
                    if price_to_convert is not None:
                        norm_unit_price, fx_obj, fx_status, fx_warn = convert_currency(
                            amount=price_to_convert,
                            from_currency=item_currency,
                            to_currency=ref_currency,
                            provider=fx_provider,
                            effective_date=fx_set.effective_date,
                        )
                        fx_rate_used = float(fx_obj.rate) if fx_obj else None
                        fx_eff_date = str(fx_obj.effective_date) if fx_obj else None
                        fx_prov_id = fx_obj.provider_id if fx_obj else None
                    else:
                        norm_unit_price = None
                        fx_status = NormalizationStatus.UNRESOLVED
                        fx_warn = "No quoted price available to convert"

                # Check manual direct unit price override
                price_override = override_map.get((qid, matched_item.id, "unit_price"))
                if price_override and "normalized_unit_price" in price_override.override_value:
                    norm_unit_price = Decimal(
                        str(price_override.override_value["normalized_unit_price"])
                    )

                # 3. Normalized Extended Price = normalized_unit_price * rfq_item.quantity
                norm_extended_price = None
                if norm_unit_price is not None:
                    norm_extended_price = (
                        norm_unit_price * Decimal(str(rfq_item.quantity))
                    ).quantize(Decimal("0.0001"))
                    supplier_subtotals[qid] += norm_extended_price

                # 4. Lead time normalization
                lt_line_res = normalize_lead_time(matched_item.lead_time_days)
                lt_line_override = override_map.get((qid, matched_item.id, "lead_time"))
                line_lt_days = lt_line_res.canonical_days
                line_lt_disp = lt_line_res.display_text
                if lt_line_override and "lead_time_days" in lt_line_override.override_value:
                    line_lt_days = int(lt_line_override.override_value["lead_time_days"])
                    line_lt_disp = f"{line_lt_days} d (overridden)"

                # Check math discrepancy
                math_disc = False
                disc_amount = None
                if (
                    matched_item.calculated_total_price is not None
                    and matched_item.total_price is not None
                ):
                    diff = abs(
                        Decimal(str(matched_item.total_price))
                        - Decimal(str(matched_item.calculated_total_price))
                    )
                    if diff > Decimal("0.05"):
                        math_disc = True
                        disc_amount = float(diff)

                # Overall cell status
                cell_warnings: list[str] = []
                if uom_res.warning:
                    cell_warnings.append(uom_res.warning)
                if fx_warn:
                    cell_warnings.append(fx_warn)
                if math_disc:
                    cell_warnings.append(
                        f"Arithmetic discrepancy in quote: quoted total {matched_item.total_price} != calculated {matched_item.calculated_total_price}"
                    )

                overall_status = NormalizationStatus.NORMALIZED
                if (
                    uom_res.status == NormalizationStatus.UNRESOLVED
                    or fx_status == NormalizationStatus.UNRESOLVED
                ):
                    overall_status = NormalizationStatus.UNRESOLVED
                    supplier_unresolved_counts[qid] += 1
                elif uom_override or fx_override or price_override or lt_line_override:
                    overall_status = NormalizationStatus.HUMAN_OVERRIDDEN
                elif (
                    uom_res.status == NormalizationStatus.IDENTICAL
                    and fx_status == NormalizationStatus.IDENTICAL
                ):
                    overall_status = NormalizationStatus.IDENTICAL

                active_cell_override = (
                    price_override or uom_override or fx_override or lt_line_override
                )

                row_cells[qid] = MatrixLineItemCell(
                    is_quoted=True,
                    line_item_id=matched_item.id,
                    quoted_description=matched_item.description_raw,
                    quoted_quantity=float(matched_item.quantity),
                    quoted_unit=matched_item.unit,
                    quoted_unit_price=float(matched_item.unit_price),
                    quoted_total_price=float(matched_item.total_price),
                    calculated_total_price=float(matched_item.calculated_total_price or 0),
                    has_math_discrepancy=math_disc,
                    math_discrepancy_amount=disc_amount,
                    original_currency=item_currency,
                    canonical_quantity=float(uom_res.canonical_quantity)
                    if uom_res.canonical_quantity is not None
                    else None,
                    canonical_unit=uom_res.canonical_uom,
                    uom_conversion_factor=float(uom_res.conversion_factor)
                    if uom_res.conversion_factor is not None
                    else None,
                    uom_status=uom_res.status,
                    uom_warning=uom_res.warning,
                    fx_rate_used=fx_rate_used,
                    fx_effective_date=fx_eff_date,
                    fx_provider_id=fx_prov_id,
                    fx_status=fx_status,
                    fx_warning=fx_warn,
                    normalized_unit_price=float(norm_unit_price)
                    if norm_unit_price is not None
                    else None,
                    normalized_extended_price=float(norm_extended_price)
                    if norm_extended_price is not None
                    else None,
                    line_lead_time_days=line_lt_days,
                    line_lead_time_display=line_lt_disp,
                    line_lead_time_type=lt_line_res.lead_time_type,
                    overall_cell_status=overall_status,
                    is_human_overridden=active_cell_override is not None,
                    override_id=active_cell_override.id if active_cell_override else None,
                    override_reason=active_cell_override.override_reason
                    if active_cell_override
                    else None,
                    warnings=cell_warnings,
                    source_evidence=matched_item.source_evidence,
                    source_page=matched_item.source_page,
                )

            required_rows.append(
                MatrixRequiredRow(
                    rfq_line_item_id=rfq_item.id,
                    position=rfq_item.position,
                    description=rfq_item.description,
                    required_quantity=float(rfq_item.quantity),
                    required_unit=rfq_item.unit,
                    supplier_cells=row_cells,
                )
            )

        # 7. Collect Unmapped / Extra Items
        for supp in suppliers_headers:
            qid = supp.quotation_id
            extraction = quotation_extractions.get(qid)
            if not extraction:
                continue

            for it in extraction.line_items:
                if not it.rfq_line_item_id and not it.is_removed:
                    all_extra_items.append(
                        MatrixExtraItem(
                            line_item_id=it.id,
                            quotation_id=qid,
                            supplier_name=supp.supplier_name,
                            description_raw=it.description_raw,
                            quantity=float(it.quantity),
                            unit=it.unit,
                            unit_price=float(it.unit_price),
                            currency=it.currency,
                            total_price=float(it.total_price),
                            lead_time_days=it.lead_time_days,
                            source_page=it.source_page,
                        )
                    )

        # 8. Update supplier header totals and comparable totals
        for supp in suppliers_headers:
            qid = supp.quotation_id
            subtotal = float(supplier_subtotals.get(qid, Decimal("0.0")))
            unresolved = supplier_unresolved_counts.get(qid, 0)

            supp.normalized_line_item_subtotal = round(subtotal, 2)
            supp.unresolved_count = unresolved

            has_extra = any(ex.quotation_id == qid for ex in all_extra_items)
            if has_extra:
                supp.has_unknown_commercial_components = True

            # Normalized comparable total is only valid if 100% of RFQ items are quoted, resolved, and without unmapped surcharges or non-item commercial components
            if (
                supp.rfq_coverage_pct >= 100.0
                and unresolved == 0
                and not supp.has_unknown_commercial_components
            ):
                supp.normalized_comparable_total = round(subtotal, 2)
            else:
                supp.normalized_comparable_total = None
                if supp.rfq_coverage_pct < 100.0:
                    warnings_summary.append(
                        f"{supp.supplier_name}: Incomplete quotation ({supp.rfq_coverage_pct}% coverage); comparable grand total withheld."
                    )
                if has_extra:
                    warnings_summary.append(
                        f"{supp.supplier_name}: Extra unmapped commercial items present; comparable grand total withheld."
                    )
                if supp.has_unknown_commercial_components and not has_extra:
                    warnings_summary.append(
                        f"{supp.supplier_name}: Non-item commercial components (freight/tax/discount/stated variance) present; comparable grand total withheld."
                    )
                if unresolved > 0:
                    warnings_summary.append(
                        f"{supp.supplier_name}: {unresolved} unresolved normalization value(s); comparable grand total withheld."
                    )

        # 9. Count snapshots
        snap_count_stmt = select(func.count()).select_from(
            select(ComparisonSnapshot.id).where(ComparisonSnapshot.rfq_id == rfq_id).subquery()
        )
        snap_count_res = await session.execute(snap_count_stmt)
        snapshots_count = snap_count_res.scalar_one()

        return ComparisonMatrixResponse(
            rfq_id=rfq.id,
            rfq_title=rfq.title,
            reference_currency=ref_currency,
            normalization_engine_version=NORMALIZATION_ENGINE_VERSION,
            fx_rate_set=RFQFXRateSetRead.model_validate(fx_set) if fx_set else None,
            suppliers=suppliers_headers,
            required_line_items=required_rows,
            extra_line_items=all_extra_items,
            active_overrides_count=len(active_overrides),
            snapshots_count=snapshots_count,
            warnings_summary=list(set(warnings_summary)),
            computed_at=dt.datetime.utcnow(),
        )

    async def create_comparison_snapshot(
        self,
        session: AsyncSession,
        rfq_id: str,
        data: ComparisonSnapshotCreate,
        actor_id: str = "system",
    ) -> ComparisonSnapshotRead:
        """
        Freezes the current comparison matrix into an immutable snapshot.
        Guarantees that historical supplier comparisons remain 100% reproducible.
        """
        matrix = await self.compile_comparison_matrix(session, rfq_id)

        # Get latest snapshot version
        stmt = select(func.max(ComparisonSnapshot.snapshot_version)).where(
            ComparisonSnapshot.rfq_id == rfq_id
        )
        res = await session.execute(stmt)
        max_ver = res.scalar() or 0
        new_version = max_ver + 1

        fx_set_id = matrix.fx_rate_set.id if matrix.fx_rate_set else None

        snapshot = ComparisonSnapshot(
            rfq_id=rfq_id,
            snapshot_version=new_version,
            normalization_engine_version=NORMALIZATION_ENGINE_VERSION,
            reference_currency=matrix.reference_currency,
            fx_rate_set_id=fx_set_id,
            title=data.title or f"Comparison Snapshot v{new_version}",
            matrix_data=matrix.model_dump(mode="json"),
            created_by=actor_id,
        )
        session.add(snapshot)
        await session.flush()

        await record_audit_event(
            db=session,
            rfq_id=rfq_id,
            event_type="COMPARISON_SNAPSHOT_CREATED",
            actor_id=actor_id,
            actor_type=ActorType.USER,
            payload={
                "snapshot_id": snapshot.id,
                "snapshot_version": new_version,
                "title": snapshot.title,
                "reference_currency": snapshot.reference_currency,
                "suppliers_count": len(matrix.suppliers),
                "required_items_count": len(matrix.required_line_items),
            },
        )

        await session.commit()
        await session.refresh(snapshot)
        return ComparisonSnapshotRead.model_validate(snapshot)

    async def list_comparison_snapshots(
        self, session: AsyncSession, rfq_id: str
    ) -> list[ComparisonSnapshotRead]:
        stmt = (
            select(ComparisonSnapshot)
            .where(ComparisonSnapshot.rfq_id == rfq_id)
            .order_by(desc(ComparisonSnapshot.snapshot_version))
        )
        res = await session.execute(stmt)
        snapshots = res.scalars().all()
        return [ComparisonSnapshotRead.model_validate(s) for s in snapshots]

    async def get_comparison_snapshot(
        self, session: AsyncSession, rfq_id: str, snapshot_id: str
    ) -> ComparisonSnapshotRead:
        stmt = select(ComparisonSnapshot).where(
            ComparisonSnapshot.id == snapshot_id, ComparisonSnapshot.rfq_id == rfq_id
        )
        res = await session.execute(stmt)
        snapshot = res.scalar_one_or_none()
        if not snapshot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Comparison snapshot '{snapshot_id}' not found for RFQ '{rfq_id}'",
            )
        return ComparisonSnapshotRead.model_validate(snapshot)


matrix_service = MatrixService()
