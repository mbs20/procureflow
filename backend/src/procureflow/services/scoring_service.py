from __future__ import annotations

import datetime as dt
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

import structlog
from fastapi import HTTPException, status
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from procureflow.models.audit import ActorType
from procureflow.models.normalization import ComparisonSnapshot
from procureflow.models.scoring import ScoringConfiguration, ScoringRun
from procureflow.schemas.scoring import (
    BreakevenResult,
    CriterionConfig,
    CriterionDirection,
    CriterionScoreBreakdown,
    CrossoverPoint,
    EligibilityStatus,
    MissingValuePolicy,
    ScoringConfigurationCreate,
    ScoringConfigurationResponse,
    ScoringRunCreate,
    ScoringRunResponse,
    SensitivityPoint,
    SensitivityRequest,
    SensitivityResponse,
    SupplierScore,
)
from procureflow.services.audit_service import record_audit_event

logger = structlog.get_logger(__name__)

SCORING_ENGINE_VERSION = "1.0.0"
PRECISION_2DP = Decimal("0.01")
PRECISION_4DP = Decimal("0.0001")


def to_decimal(val: Any) -> Decimal:
    """Safely converts float, int, str, or Decimal to Decimal."""
    if isinstance(val, Decimal):
        return val
    if val is None:
        raise ValueError("Cannot convert None to Decimal")
    return Decimal(str(val))


class MissingValueError(Exception):
    """Raised when a required criterion cannot be evaluated under BLOCK_SCORING."""

    pass


class ScoringService:
    """
    Authoritative deterministic scoring engine for ProcureFlow.
    Operates strictly on immutable ComparisonSnapshots using Python Decimal.
    Evaluates knockouts prior to relative normalization.
    Provides mathematically sound sensitivity sweeps and bisection breakeven search.
    """

    async def create_configuration(
        self,
        session: AsyncSession,
        rfq_id: str,
        data: ScoringConfigurationCreate,
        actor_id: str = "evaluator",
    ) -> ScoringConfigurationResponse:
        """
        Creates a new immutable version of ScoringConfiguration for an RFQ.
        """
        # Determine next version
        stmt = select(func.max(ScoringConfiguration.version)).where(
            ScoringConfiguration.rfq_id == rfq_id
        )
        res = await session.execute(stmt)
        max_ver = res.scalar() or 0
        new_version = max_ver + 1

        # Mark previous active configurations as inactive
        update_stmt = select(ScoringConfiguration).where(
            ScoringConfiguration.rfq_id == rfq_id,
            ScoringConfiguration.is_active == True,  # noqa: E712
        )
        active_res = await session.execute(update_stmt)
        for prev_cfg in active_res.scalars().all():
            prev_cfg.is_active = False

        config = ScoringConfiguration(
            rfq_id=rfq_id,
            version=new_version,
            name=data.name,
            description=data.description,
            engine_version=data.engine_version or SCORING_ENGINE_VERSION,
            is_active=True,
            config_payload=data.model_dump(mode="json"),
            created_by=actor_id,
        )
        session.add(config)
        await session.flush()

        await record_audit_event(
            db=session,
            rfq_id=rfq_id,
            event_type="SCORING_CONFIGURATION_CREATED",
            actor_id=actor_id,
            actor_type=ActorType.USER,
            payload={
                "configuration_id": config.id,
                "version": new_version,
                "name": config.name,
                "criteria_count": len(data.criteria),
            },
        )

        await session.commit()
        await session.refresh(config)
        return ScoringConfigurationResponse.model_validate(config)

    async def get_configuration(
        self, session: AsyncSession, rfq_id: str, configuration_id: str
    ) -> ScoringConfigurationResponse:
        stmt = select(ScoringConfiguration).where(
            ScoringConfiguration.id == configuration_id,
            ScoringConfiguration.rfq_id == rfq_id,
        )
        res = await session.execute(stmt)
        cfg = res.scalar_one_or_none()
        if not cfg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Scoring configuration '{configuration_id}' not found for RFQ '{rfq_id}'",
            )
        return ScoringConfigurationResponse.model_validate(cfg)

    async def get_active_configuration(
        self, session: AsyncSession, rfq_id: str
    ) -> ScoringConfigurationResponse:
        stmt = (
            select(ScoringConfiguration)
            .where(
                ScoringConfiguration.rfq_id == rfq_id,
                ScoringConfiguration.is_active == True,  # noqa: E712
            )
            .order_by(desc(ScoringConfiguration.version))
        )
        res = await session.execute(stmt)
        cfg = res.scalar_one_or_none()
        if not cfg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No active scoring configuration found for RFQ '{rfq_id}'. Please create one first.",
            )
        return ScoringConfigurationResponse.model_validate(cfg)

    async def list_configurations(
        self, session: AsyncSession, rfq_id: str
    ) -> list[ScoringConfigurationResponse]:
        stmt = (
            select(ScoringConfiguration)
            .where(ScoringConfiguration.rfq_id == rfq_id)
            .order_by(desc(ScoringConfiguration.version))
        )
        res = await session.execute(stmt)
        return [ScoringConfigurationResponse.model_validate(c) for c in res.scalars().all()]

    async def get_snapshot(
        self, session: AsyncSession, rfq_id: str, snapshot_id: str
    ) -> ComparisonSnapshot:
        stmt = select(ComparisonSnapshot).where(
            ComparisonSnapshot.id == snapshot_id,
            ComparisonSnapshot.rfq_id == rfq_id,
        )
        res = await session.execute(stmt)
        snapshot = res.scalar_one_or_none()
        if not snapshot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Comparison snapshot '{snapshot_id}' not found for RFQ '{rfq_id}'",
            )
        return snapshot

    # --------------------------------------------------------------------------
    # CORE CALCULATION ENGINE
    # --------------------------------------------------------------------------

    def resolve_supplier_criterion_value(
        self,
        supplier: dict[str, Any],
        matrix_data: dict[str, Any],
        criterion: CriterionConfig,
    ) -> tuple[Decimal, str]:
        """
        Resolves a single criterion's raw value from the snapshot matrix_data for a supplier.
        Returns (resolved_decimal_value, source_path_string).
        """
        field = criterion.source_field
        quotation_id = supplier["quotation_id"]

        # 1. Direct supplier header fields
        if field in supplier and supplier[field] is not None:
            raw_val = supplier[field]
            source_path = f"suppliers[{quotation_id}].{field}"

            # If categorical map is provided, map string to Decimal
            if criterion.categorical_map is not None:
                str_val = str(raw_val).strip().upper()
                # Check for exact key or case-insensitive match
                matched = None
                for k, v in criterion.categorical_map.items():
                    if k.strip().upper() == str_val:
                        matched = to_decimal(v)
                        break
                if matched is None:
                    raise MissingValueError(
                        f"Supplier '{supplier.get('supplier_name')}' categorical value '{raw_val}' "
                        f"is not mapped in criterion '{criterion.name}' categorical_map."
                    )
                return matched, f"{source_path} (mapped from '{raw_val}')"

            try:
                return to_decimal(raw_val), source_path
            except (ValueError, TypeError) as e:
                raise MissingValueError(
                    f"Supplier '{supplier.get('supplier_name')}' field '{field}' has non-numeric value '{raw_val}': {e}"
                ) from e

        # 2. Check for normalized comparable total specifically
        if field == "normalized_comparable_total":
            val = supplier.get("normalized_comparable_total")
            if val is None:
                # Fallback to normalized_line_item_subtotal if comparable total is safe or note variance
                subtotal = supplier.get("normalized_line_item_subtotal")
                if subtotal is not None:
                    return to_decimal(
                        subtotal
                    ), f"suppliers[{quotation_id}].normalized_line_item_subtotal (fallback)"
                raise MissingValueError(
                    f"Supplier '{supplier.get('supplier_name')}' has no normalized comparable total or subtotal."
                )
            return to_decimal(val), f"suppliers[{quotation_id}].normalized_comparable_total"

        # 3. Line-item specific resolution (e.g. line_item_id in field)
        if field.startswith("line_item:"):
            target_item_id = field.split(":", 1)[1]
            rows = matrix_data.get("required_line_items", [])
            for row in rows:
                if row.get("rfq_line_item_id") == target_item_id:
                    cells = row.get("cells", {})
                    cell = cells.get(quotation_id)
                    if cell and cell.get("normalized_extended_price") is not None:
                        val = cell["normalized_extended_price"]
                        return (
                            to_decimal(val),
                            f"required_line_items[{target_item_id}].cells[{quotation_id}].normalized_extended_price",
                        )
                    raise MissingValueError(
                        f"Supplier '{supplier.get('supplier_name')}' did not quote required line item '{target_item_id}'."
                    )

        # Unresolved
        raise MissingValueError(
            f"Criterion '{criterion.name}' source field '{field}' not found or null for supplier '{supplier.get('supplier_name')}'."
        )

    def evaluate_scoring(
        self,
        snapshot_matrix_data: dict[str, Any],
        config: ScoringConfigurationCreate,
        candidate_price_override: tuple[str, Decimal] | None = None,
    ) -> list[SupplierScore]:
        """
        Deterministic execution pipeline:
        1. Resolve criterion inputs for all suppliers.
        2. Evaluate knockout criteria -> Mark knockout_failed.
        3. Filter eligible supplier population.
        4. Derive min/max extremes strictly from eligible population.
        5. Compute relative normalized scores (0 - 100) using Python Decimal.
        6. Apply weights and calculate composite score.
        7. Apply deterministic standard competitive ranking (preserving ties).
        """
        suppliers = snapshot_matrix_data.get("suppliers", [])
        if not suppliers:
            return []

        # Step 1 & 2: Resolve inputs and check knockouts
        supplier_records: list[dict[str, Any]] = []
        for s in suppliers:
            qid = s["quotation_id"]
            name = s.get("supplier_name", qid)
            elig_status = EligibilityStatus.ELIGIBLE
            knockout_reasons: list[str] = []
            criterion_values: dict[str, tuple[Decimal, str]] = {}

            for crit in config.criteria:
                try:
                    # Apply candidate price override if simulating breakeven
                    if (
                        candidate_price_override
                        and qid == candidate_price_override[0]
                        and crit.source_type == "price"
                    ):
                        val = candidate_price_override[1]
                        src = "simulation_candidate_price_override"
                    else:
                        val, src = self.resolve_supplier_criterion_value(
                            s, snapshot_matrix_data, crit
                        )
                    criterion_values[crit.criterion_id] = (val, src)

                    # Evaluate knockout if configured
                    if crit.is_knockout and crit.knockout_threshold is not None:
                        thresh = crit.knockout_threshold
                        if crit.direction == CriterionDirection.LOWER_IS_BETTER and val > thresh:
                            elig_status = EligibilityStatus.KNOCKOUT_FAILED
                            knockout_reasons.append(
                                f"Value {val} exceeds maximum knockout threshold {thresh} on '{crit.name}'"
                            )
                        elif crit.direction == CriterionDirection.HIGHER_IS_BETTER and val < thresh:
                            elig_status = EligibilityStatus.KNOCKOUT_FAILED
                            knockout_reasons.append(
                                f"Value {val} is below minimum knockout threshold {thresh} on '{crit.name}'"
                            )

                except MissingValueError as mve:
                    if config.missing_value_policy == MissingValuePolicy.BLOCK_SCORING:
                        raise HTTPException(
                            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail=f"Scoring blocked due to missing value: {mve}",
                        ) from mve
                    # If other policies were supported, handle here; for now, BLOCK_SCORING is enforced
                    elig_status = EligibilityStatus.MISSING_VALUE_BLOCKED
                    knockout_reasons.append(str(mve))

            supplier_records.append(
                {
                    "quotation_id": qid,
                    "supplier_name": name,
                    "status": elig_status,
                    "knockout_reasons": knockout_reasons,
                    "criterion_values": criterion_values,
                }
            )

        # Step 3: Determine eligible cohort
        eligible_records = [
            r for r in supplier_records if r["status"] == EligibilityStatus.ELIGIBLE
        ]

        # Step 4: Derive min/max extremes strictly from eligible population
        criteria_extremes: dict[str, tuple[Decimal, Decimal]] = {}
        for crit in config.criteria:
            cid = crit.criterion_id
            eligible_vals = [
                r["criterion_values"][cid][0]
                for r in eligible_records
                if cid in r["criterion_values"]
            ]
            if eligible_vals:
                min_v = min(eligible_vals)
                max_v = max(eligible_vals)
            else:
                min_v = Decimal("0.00")
                max_v = Decimal("0.00")
            criteria_extremes[cid] = (min_v, max_v)

        # Step 5 & 6: Compute normalized scores and weighted contributions
        results: list[SupplierScore] = []
        for r in supplier_records:
            qid = r["quotation_id"]
            name = r["supplier_name"]
            st = r["status"]
            reasons = r["knockout_reasons"]
            breakdowns: list[CriterionScoreBreakdown] = []
            total_score = Decimal("0.00")

            if st == EligibilityStatus.ELIGIBLE:
                for crit in config.criteria:
                    cid = crit.criterion_id
                    raw_val, src_path = r["criterion_values"][cid]
                    min_v, max_v = criteria_extremes[cid]
                    weight = crit.weight

                    # Zero-variance or single eligible supplier: full score
                    if max_v == min_v:
                        norm_score = Decimal("100.00")
                        formula = (
                            f"Zero variance in eligible population (min=max={min_v}) -> 100.00"
                        )
                    else:
                        if crit.direction == CriterionDirection.LOWER_IS_BETTER:
                            # (max - x) / (max - min) * 100
                            norm_score = (max_v - raw_val) / (max_v - min_v) * Decimal("100.00")
                            formula = f"(max ({max_v}) - val ({raw_val})) / (max ({max_v}) - min ({min_v})) * 100"
                        else:
                            # (x - min) / (max - min) * 100
                            norm_score = (raw_val - min_v) / (max_v - min_v) * Decimal("100.00")
                            formula = f"(val ({raw_val}) - min ({min_v})) / (max ({max_v}) - min ({min_v})) * 100"

                    # Clamp normalized score to [0.00, 100.00] for safety
                    norm_score = max(Decimal("0.00"), min(Decimal("100.00"), norm_score))
                    weighted_contrib = norm_score * weight
                    total_score += weighted_contrib

                    breakdowns.append(
                        CriterionScoreBreakdown(
                            criterion_id=cid,
                            criterion_name=crit.name,
                            raw_value=raw_val,
                            source_path=src_path,
                            direction=crit.direction,
                            min_value=min_v,
                            max_value=max_v,
                            normalized_score=norm_score.quantize(
                                PRECISION_4DP, rounding=ROUND_HALF_UP
                            ),
                            weight=weight,
                            weighted_contribution=weighted_contrib.quantize(
                                PRECISION_4DP, rounding=ROUND_HALF_UP
                            ),
                            formula_audit=f"{formula} = {norm_score.quantize(PRECISION_2DP, rounding=ROUND_HALF_UP)} | Weighted: {weighted_contrib.quantize(PRECISION_4DP, rounding=ROUND_HALF_UP)}",
                            is_knockout_applied=False,
                        )
                    )
                total_score = total_score.quantize(PRECISION_4DP, rounding=ROUND_HALF_UP)
            else:
                # Ineligible / knockout failed
                for crit in config.criteria:
                    cid = crit.criterion_id
                    raw_val, src_path = r["criterion_values"].get(
                        cid, (Decimal("0.00"), "unresolved")
                    )
                    min_v, max_v = criteria_extremes.get(cid, (Decimal("0.00"), Decimal("0.00")))
                    breakdowns.append(
                        CriterionScoreBreakdown(
                            criterion_id=cid,
                            criterion_name=crit.name,
                            raw_value=raw_val,
                            source_path=src_path,
                            direction=crit.direction,
                            min_value=min_v,
                            max_value=max_v,
                            normalized_score=Decimal("0.00"),
                            weight=crit.weight,
                            weighted_contribution=Decimal("0.00"),
                            formula_audit="Knockout failed or ineligible -> 0.00",
                            is_knockout_applied=True,
                            notes="; ".join(reasons),
                        )
                    )

            results.append(
                SupplierScore(
                    quotation_id=qid,
                    supplier_name=name,
                    eligibility_status=st,
                    knockout_reasons=reasons,
                    total_score=total_score,
                    rank=None,  # Assigned in ranking step
                    criteria_breakdown=breakdowns,
                )
            )

        # Step 7: Deterministic Standard Competitive Ranking (1224)
        eligible_scores = [s for s in results if s.eligibility_status == EligibilityStatus.ELIGIBLE]
        # Sort descending by total_score, then quotation_id for stable ordering
        eligible_scores.sort(key=lambda x: (-x.total_score, x.quotation_id))

        current_rank = 1
        for idx, item in enumerate(eligible_scores):
            if idx > 0 and item.total_score == eligible_scores[idx - 1].total_score:
                item.rank = eligible_scores[idx - 1].rank
            else:
                item.rank = current_rank
            current_rank = idx + 2

        return results

    # --------------------------------------------------------------------------
    # SCORING RUN PERSISTENCE
    # --------------------------------------------------------------------------

    async def execute_and_save_run(
        self,
        session: AsyncSession,
        rfq_id: str,
        data: ScoringRunCreate,
        actor_id: str = "evaluator",
    ) -> ScoringRunResponse:
        """
        Executes a deterministic scoring run against an immutable ComparisonSnapshot
        and freezes the result in an append-only ScoringRun.
        """
        # Load snapshot
        snapshot = await self.get_snapshot(session, rfq_id, data.snapshot_id)

        # Load configuration
        if data.configuration_id:
            cfg_record = await self.get_configuration(session, rfq_id, data.configuration_id)
        else:
            cfg_record = await self.get_active_configuration(session, rfq_id)

        config_data = ScoringConfigurationCreate.model_validate(cfg_record.config_payload)

        # Execute scoring
        scores = self.evaluate_scoring(snapshot.matrix_data, config_data)

        # Get next run number
        stmt = select(func.max(ScoringRun.run_number)).where(ScoringRun.rfq_id == rfq_id)
        res = await session.execute(stmt)
        max_run = res.scalar() or 0
        new_run_num = max_run + 1

        results_payload = {
            "rfq_id": rfq_id,
            "snapshot_id": snapshot.id,
            "snapshot_version": snapshot.snapshot_version,
            "configuration_id": cfg_record.id,
            "configuration_version": cfg_record.version,
            "configuration_name": cfg_record.name,
            "engine_version": SCORING_ENGINE_VERSION,
            "evaluated_at": dt.datetime.utcnow().isoformat(),
            "eligible_suppliers_count": sum(
                1 for s in scores if s.eligibility_status == EligibilityStatus.ELIGIBLE
            ),
            "knockout_suppliers_count": sum(
                1 for s in scores if s.eligibility_status == EligibilityStatus.KNOCKOUT_FAILED
            ),
            "suppliers": [s.model_dump(mode="json") for s in scores],
        }

        run = ScoringRun(
            rfq_id=rfq_id,
            configuration_id=cfg_record.id,
            snapshot_id=snapshot.id,
            run_number=new_run_num,
            name=data.name or f"Scoring Run #{new_run_num} ({cfg_record.name})",
            notes=data.notes,
            results_payload=results_payload,
            created_by=actor_id,
        )
        session.add(run)
        await session.flush()

        await record_audit_event(
            db=session,
            rfq_id=rfq_id,
            event_type="SCORING_RUN_EXECUTED",
            actor_id=actor_id,
            actor_type=ActorType.USER,
            payload={
                "run_id": run.id,
                "run_number": new_run_num,
                "snapshot_id": snapshot.id,
                "configuration_id": cfg_record.id,
                "eligible_count": results_payload["eligible_suppliers_count"],
            },
        )

        await session.commit()
        await session.refresh(run)
        return ScoringRunResponse.model_validate(run)

    async def list_runs(self, session: AsyncSession, rfq_id: str) -> list[ScoringRunResponse]:
        stmt = (
            select(ScoringRun)
            .where(ScoringRun.rfq_id == rfq_id)
            .order_by(desc(ScoringRun.run_number))
        )
        res = await session.execute(stmt)
        return [ScoringRunResponse.model_validate(r) for r in res.scalars().all()]

    async def get_run(self, session: AsyncSession, rfq_id: str, run_id: str) -> ScoringRunResponse:
        stmt = select(ScoringRun).where(ScoringRun.id == run_id, ScoringRun.rfq_id == rfq_id)
        res = await session.execute(stmt)
        run = res.scalar_one_or_none()
        if not run:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Scoring run '{run_id}' not found for RFQ '{rfq_id}'",
            )
        return ScoringRunResponse.model_validate(run)

    # --------------------------------------------------------------------------
    # SENSITIVITY ANALYSIS & BISECTION BREAKEVEN
    # --------------------------------------------------------------------------

    def redistribute_weights(
        self,
        base_criteria: list[CriterionConfig],
        swept_cid: str,
        new_weight: Decimal,
        locked_cids: list[str],
    ) -> list[CriterionConfig]:
        """
        Redistributes criteria weights proportionally when swept_cid changes:
        - swept_cid gets new_weight.
        - locked_cids retain their baseline weight.
        - unlocked criteria receive the remaining (1 - new_weight - sum(locked))
          proportional to their baseline share.
        Enforces sum = 1.0000.
        """
        locked_set = set(locked_cids) - {swept_cid}

        # Calculate locked sum
        locked_sum = sum(c.weight for c in base_criteria if c.criterion_id in locked_set)
        max_allowed_swept = max(Decimal("0.00"), Decimal("1.0000") - locked_sum)
        new_weight = max(Decimal("0.00"), min(max_allowed_swept, new_weight))

        remaining_pool = Decimal("1.0000") - new_weight - locked_sum
        remaining_pool = max(Decimal("0.00"), remaining_pool)

        unlocked_criteria = [
            c
            for c in base_criteria
            if c.criterion_id != swept_cid and c.criterion_id not in locked_set
        ]
        base_unlocked_sum = sum(c.weight for c in unlocked_criteria)

        updated: list[CriterionConfig] = []
        assigned_sum = Decimal("0.00")

        for c in base_criteria:
            crit_copy = c.model_copy()
            if c.criterion_id == swept_cid:
                crit_copy.weight = new_weight
            elif c.criterion_id in locked_set:
                crit_copy.weight = c.weight
            else:
                if base_unlocked_sum > Decimal("0.00"):
                    proportional_w = (c.weight / base_unlocked_sum) * remaining_pool
                else:
                    proportional_w = remaining_pool / Decimal(len(unlocked_criteria))
                crit_copy.weight = proportional_w.quantize(PRECISION_4DP, rounding=ROUND_HALF_UP)
            assigned_sum += crit_copy.weight
            updated.append(crit_copy)

        # Micro-adjustment to guarantee exact 1.0000 sum
        diff = Decimal("1.0000") - assigned_sum
        if diff != Decimal("0.00") and unlocked_criteria:
            # Adjust on first unlocked criterion
            for u in updated:
                if u.criterion_id not in locked_set and u.criterion_id != swept_cid:
                    u.weight = max(Decimal("0.00"), u.weight + diff)
                    break

        return updated

    def compute_bisection_breakeven(
        self,
        snapshot_matrix_data: dict[str, Any],
        config: ScoringConfigurationCreate,
        candidate_id: str,
        target_rank: int = 1,
        tolerance: Decimal = Decimal("0.01"),
        max_steps: int = 50,
    ) -> BreakevenResult:
        """
        Bounded numerical bisection search for exact candidate price to achieve target_rank.
        Recomputes full eligible population, min/max bounds, and all scores at each candidate price.
        """
        # Find candidate and price criterion
        price_crit = next((c for c in config.criteria if c.source_type == "price"), None)
        if not price_crit:
            return BreakevenResult(
                candidate_id=candidate_id,
                candidate_name=candidate_id,
                target_rank=target_rank,
                current_price=Decimal("0.00"),
                feasible=False,
                convergence_steps=0,
                evaluated_scores={},
                notes="RFQ scoring configuration does not define a price criterion.",
            )

        # Baseline evaluation
        baseline_scores = self.evaluate_scoring(snapshot_matrix_data, config)
        cand_score = next((s for s in baseline_scores if s.quotation_id == candidate_id), None)
        if not cand_score:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Candidate supplier '{candidate_id}' not found in snapshot.",
            )

        if cand_score.eligibility_status != EligibilityStatus.ELIGIBLE:
            return BreakevenResult(
                candidate_id=candidate_id,
                candidate_name=cand_score.supplier_name,
                target_rank=target_rank,
                current_price=Decimal("0.00"),
                feasible=False,
                convergence_steps=0,
                evaluated_scores={},
                notes=f"Candidate failed knockout criteria: {'; '.join(cand_score.knockout_reasons)}",
            )

        # Candidate current price
        cand_breakdown = next(
            b for b in cand_score.criteria_breakdown if b.criterion_id == price_crit.criterion_id
        )
        current_p = to_decimal(cand_breakdown.raw_value)

        # If already at or better than target_rank
        if cand_score.rank is not None and cand_score.rank <= target_rank:
            return BreakevenResult(
                candidate_id=candidate_id,
                candidate_name=cand_score.supplier_name,
                target_rank=target_rank,
                current_price=current_p,
                required_price=current_p,
                delta_price=Decimal("0.00"),
                delta_pct=Decimal("0.00"),
                feasible=True,
                convergence_steps=0,
                evaluated_scores={s.supplier_name: s.total_score for s in baseline_scores},
                notes="Candidate is already at target rank.",
            )

        # Test zero price feasibility
        zero_scores = self.evaluate_scoring(
            snapshot_matrix_data, config, candidate_price_override=(candidate_id, Decimal("0.00"))
        )
        cand_at_zero = next(s for s in zero_scores if s.quotation_id == candidate_id)
        if cand_at_zero.rank is None or cand_at_zero.rank > target_rank:
            return BreakevenResult(
                candidate_id=candidate_id,
                candidate_name=cand_score.supplier_name,
                target_rank=target_rank,
                current_price=current_p,
                feasible=False,
                convergence_steps=1,
                evaluated_scores={s.supplier_name: s.total_score for s in zero_scores},
                notes=f"Infeasible: Even at $0.00 price, candidate achieves rank {cand_at_zero.rank} due to non-price criteria weights.",
            )

        # Bisection search between 0.00 and current_p
        p_low = Decimal("0.00")
        p_high = current_p
        steps = 0
        last_eval_scores: dict[str, Decimal] = {}

        while (p_high - p_low) > tolerance and steps < max_steps:
            steps += 1
            p_mid = (p_low + p_high) / Decimal("2.00")
            test_scores = self.evaluate_scoring(
                snapshot_matrix_data, config, candidate_price_override=(candidate_id, p_mid)
            )
            c_test = next(s for s in test_scores if s.quotation_id == candidate_id)
            last_eval_scores = {s.supplier_name: s.total_score for s in test_scores}

            if c_test.rank is not None and c_test.rank <= target_rank:
                # p_mid is low enough to achieve rank; try higher price to find boundary
                p_low = p_mid
            else:
                # p_mid is too expensive; must go lower
                p_high = p_mid

        required_p = p_low.quantize(PRECISION_2DP, rounding=ROUND_HALF_UP)
        delta_p = (current_p - required_p).quantize(PRECISION_2DP, rounding=ROUND_HALF_UP)
        delta_pct = (
            (delta_p / current_p * Decimal("100.00")).quantize(
                PRECISION_2DP, rounding=ROUND_HALF_UP
            )
            if current_p > Decimal("0.00")
            else Decimal("0.00")
        )

        return BreakevenResult(
            candidate_id=candidate_id,
            candidate_name=cand_score.supplier_name,
            target_rank=target_rank,
            current_price=current_p,
            required_price=required_p,
            delta_price=delta_p,
            delta_pct=delta_pct,
            feasible=True,
            convergence_steps=steps,
            evaluated_scores=last_eval_scores,
            notes=f"Converged in {steps} steps with tolerance {tolerance}.",
        )

    async def run_sensitivity_analysis(
        self,
        session: AsyncSession,
        rfq_id: str,
        req: SensitivityRequest,
    ) -> SensitivityResponse:
        """
        Executes in-memory sensitivity sweeps across criteria weights and computes breakeven.
        Does not mutate or persist any configuration or snapshot data.
        """
        snapshot = await self.get_snapshot(session, rfq_id, req.snapshot_id)

        if req.configuration_id:
            cfg_record = await self.get_configuration(session, rfq_id, req.configuration_id)
        else:
            cfg_record = await self.get_active_configuration(session, rfq_id)

        base_config = ScoringConfigurationCreate.model_validate(cfg_record.config_payload)
        swept_cid = req.swept_criterion_id

        # Verify criterion exists
        swept_crit = next((c for c in base_config.criteria if c.criterion_id == swept_cid), None)
        if not swept_crit:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Swept criterion '{swept_cid}' not found in configuration '{cfg_record.id}'",
            )

        points: list[SensitivityPoint] = []
        crossover_points: list[CrossoverPoint] = []
        prev_top_supplier: str | None = None

        locked_set = set(req.locked_criterion_ids) - {swept_cid}
        locked_sum = sum(c.weight for c in base_config.criteria if c.criterion_id in locked_set)
        max_allowed_w = max(Decimal("0.00"), Decimal("1.0000") - locked_sum)

        # Sweep weight from 0.00 to max_allowed_w in step_size
        step = req.step_size
        current_w = Decimal("0.00")

        while current_w <= max_allowed_w + Decimal("0.0001"):
            clamped_w = min(max_allowed_w, current_w)
            redistributed_criteria = self.redistribute_weights(
                base_config.criteria,
                swept_cid,
                clamped_w,
                req.locked_criterion_ids,
            )
            sim_config = base_config.model_copy(update={"criteria": redistributed_criteria})
            scores = self.evaluate_scoring(snapshot.matrix_data, sim_config)

            score_map = {s.supplier_name: s.total_score for s in scores}
            rank_map = {s.supplier_name: s.rank for s in scores}
            weight_map = {c.criterion_id: c.weight for c in redistributed_criteria}

            points.append(
                SensitivityPoint(
                    weight=clamped_w,
                    redistributed_weights=weight_map,
                    supplier_scores=score_map,
                    rankings=rank_map,
                )
            )

            # Check for rank 1 crossover
            eligible_scores = [s for s in scores if s.rank == 1]
            if eligible_scores:
                curr_top = eligible_scores[0].supplier_name
                if prev_top_supplier and curr_top != prev_top_supplier:
                    crossover_points.append(
                        CrossoverPoint(
                            weight=clamped_w,
                            supplier_a=prev_top_supplier,
                            supplier_b=curr_top,
                            score_at_crossover=eligible_scores[0].total_score,
                        )
                    )
                prev_top_supplier = curr_top

            current_w += step

        # Breakeven calculation if requested
        breakeven_res = None
        if req.include_breakeven and req.breakeven_candidate_id:
            breakeven_res = self.compute_bisection_breakeven(
                snapshot.matrix_data,
                base_config,
                candidate_id=req.breakeven_candidate_id,
            )

        redistribution_rule_desc = (
            f"When criterion '{swept_crit.name}' changes to w, locked criteria {req.locked_criterion_ids} "
            f"remain unchanged, and remaining unlocked criteria scale proportionally to their baseline share."
        )

        return SensitivityResponse(
            swept_criterion_id=swept_cid,
            weight_redistribution_rule=redistribution_rule_desc,
            points=points,
            crossover_points=crossover_points,
            breakeven=breakeven_res,
        )


scoring_service = ScoringService()
