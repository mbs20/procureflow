from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import NamedTuple

from procureflow.services.normalization.currency import NormalizationStatus


class UOMConversionResult(NamedTuple):
    quoted_quantity: Decimal
    quoted_uom: str
    quoted_unit_price: Decimal
    canonical_uom: str
    canonical_quantity: Decimal | None
    conversion_factor: Decimal | None  # 1 quoted_unit = conversion_factor * canonical_unit
    normalized_unit_price: Decimal | None  # quoted_unit_price / conversion_factor
    status: NormalizationStatus
    is_safe: bool
    warning: str | None


# Canonical synonym sets (factor 1.0 within synonym group)
SYNONYM_GROUPS: dict[str, list[str]] = {
    "pcs": ["pcs", "pc", "piece", "pieces", "unit", "units", "ea", "each", "item", "items"],
    "set": ["set", "sets", "kit", "kits"],
    "m": ["m", "meter", "meters", "metre", "metres"],
    "kg": ["kg", "kgs", "kilogram", "kilograms"],
    "l": ["l", "ltr", "liter", "liters", "litre", "litres"],
    "hr": ["hr", "hrs", "hour", "hours"],
    "day": ["day", "days"],
    "month": ["month", "months"],
}

# Inverted lookup map for canonical synonyms
SYNONYM_LOOKUP: dict[str, str] = {}
for canonical, aliases in SYNONYM_GROUPS.items():
    for alias in aliases:
        SYNONYM_LOOKUP[alias.lower()] = canonical

# Safe metric dimension scalings: (from_unit, to_unit) -> factor where 1 from_unit = factor * to_unit
METRIC_SCALINGS: dict[tuple[str, str], Decimal] = {
    # Mass (to kg)
    ("g", "kg"): Decimal("0.001"),
    ("gram", "kg"): Decimal("0.001"),
    ("grams", "kg"): Decimal("0.001"),
    ("kg", "g"): Decimal("1000.0"),
    ("ton", "kg"): Decimal("1000.0"),
    ("tonne", "kg"): Decimal("1000.0"),
    ("t", "kg"): Decimal("1000.0"),
    # Length (to m)
    ("mm", "m"): Decimal("0.001"),
    ("millimeter", "m"): Decimal("0.001"),
    ("millimeters", "m"): Decimal("0.001"),
    ("cm", "m"): Decimal("0.01"),
    ("centimeter", "m"): Decimal("0.01"),
    ("centimeters", "m"): Decimal("0.01"),
    ("km", "m"): Decimal("1000.0"),
    ("m", "mm"): Decimal("1000.0"),
    ("m", "cm"): Decimal("100.0"),
    # Volume (to l)
    ("ml", "l"): Decimal("0.001"),
    ("milliliter", "l"): Decimal("0.001"),
    ("milliliters", "l"): Decimal("0.001"),
    ("l", "ml"): Decimal("1000.0"),
}

# Packaging and compound units that must NEVER be converted to count units without explicit factor
PACKAGING_UNITS: set[str] = {
    "box",
    "boxes",
    "bx",
    "pack",
    "packs",
    "pkg",
    "pkgs",
    "package",
    "packages",
    "carton",
    "cartons",
    "ctn",
    "pallet",
    "pallets",
    "plt",
    "roll",
    "rolls",
    "bundle",
    "bundles",
    "drum",
    "drums",
    "bag",
    "bags",
    "case",
    "cases",
    "container",
    "containers",
}


def normalize_uom_and_price(
    quoted_quantity: Decimal | float,
    quoted_uom: str,
    quoted_unit_price: Decimal | float,
    rfq_uom: str,
    explicit_conversion_factor: Decimal | float | None = None,
) -> UOMConversionResult:
    """
    Normalizes quoted quantity and unit price basis to match the RFQ required UOM.

    CRITICAL RULES:
    1. Preserves quoted values and unit price basis verbatim.
    2. Recognizes safe synonyms (e.g. piece, pieces, units -> pcs).
    3. Handles safe metric scalings (e.g. mm -> m, g -> kg).
    4. Never infers packaging conversion factors (e.g. box -> pcs). If explicit_conversion_factor
       is not provided for packaging units, flags as UNRESOLVED for human review.
    """
    qty_dec = Decimal(str(quoted_quantity))
    price_dec = Decimal(str(quoted_unit_price))
    q_uom_clean = quoted_uom.strip().lower()
    r_uom_clean = rfq_uom.strip().lower()

    # Determine canonical aliases if known
    q_canonical = SYNONYM_LOOKUP.get(q_uom_clean, q_uom_clean)
    r_canonical = SYNONYM_LOOKUP.get(r_uom_clean, r_uom_clean)

    # 1. User provided explicit conversion factor (e.g. 1 box = 24 pcs)
    if explicit_conversion_factor is not None:
        factor = Decimal(str(explicit_conversion_factor))
        if factor <= Decimal("0"):
            return UOMConversionResult(
                quoted_quantity=qty_dec,
                quoted_uom=quoted_uom,
                quoted_unit_price=price_dec,
                canonical_uom=rfq_uom,
                canonical_quantity=None,
                conversion_factor=None,
                normalized_unit_price=None,
                status=NormalizationStatus.UNRESOLVED,
                is_safe=False,
                warning=f"Invalid non-positive conversion factor ({factor})",
            )

        canonical_qty = (qty_dec * factor).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
        norm_price = (price_dec / factor).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
        return UOMConversionResult(
            quoted_quantity=qty_dec,
            quoted_uom=quoted_uom,
            quoted_unit_price=price_dec,
            canonical_uom=rfq_uom,
            canonical_quantity=canonical_qty,
            conversion_factor=factor,
            normalized_unit_price=norm_price,
            status=NormalizationStatus.HUMAN_OVERRIDDEN,
            is_safe=True,
            warning=None,
        )

    # 2. Exact match or safe synonym match (factor 1.0)
    if q_uom_clean == r_uom_clean or q_canonical == r_canonical:
        return UOMConversionResult(
            quoted_quantity=qty_dec,
            quoted_uom=quoted_uom,
            quoted_unit_price=price_dec,
            canonical_uom=r_canonical,
            canonical_quantity=qty_dec,
            conversion_factor=Decimal("1.0000"),
            normalized_unit_price=price_dec,
            status=NormalizationStatus.IDENTICAL
            if q_uom_clean == r_uom_clean
            else NormalizationStatus.NORMALIZED,
            is_safe=True,
            warning=None,
        )

    # 3. Known safe metric dimension scaling (e.g. mm -> m, g -> kg)
    metric_key = (q_uom_clean, r_uom_clean)
    if metric_key in METRIC_SCALINGS:
        factor = METRIC_SCALINGS[metric_key]
        canonical_qty = (qty_dec * factor).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
        norm_price = (price_dec / factor).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
        return UOMConversionResult(
            quoted_quantity=qty_dec,
            quoted_uom=quoted_uom,
            quoted_unit_price=price_dec,
            canonical_uom=r_canonical,
            canonical_quantity=canonical_qty,
            conversion_factor=factor,
            normalized_unit_price=norm_price,
            status=NormalizationStatus.NORMALIZED,
            is_safe=True,
            warning=None,
        )

    # 4. Packaging / compound units mismatch (e.g. box vs pcs)
    if q_uom_clean in PACKAGING_UNITS or r_uom_clean in PACKAGING_UNITS:
        return UOMConversionResult(
            quoted_quantity=qty_dec,
            quoted_uom=quoted_uom,
            quoted_unit_price=price_dec,
            canonical_uom=rfq_uom,
            canonical_quantity=None,
            conversion_factor=None,
            normalized_unit_price=None,
            status=NormalizationStatus.UNRESOLVED,
            is_safe=False,
            warning=f"Packaging unit '{quoted_uom}' cannot be converted to '{rfq_uom}' without an explicitly confirmed conversion factor.",
        )

    # 5. Incompatible or unknown unit conversion
    return UOMConversionResult(
        quoted_quantity=qty_dec,
        quoted_uom=quoted_uom,
        quoted_unit_price=price_dec,
        canonical_uom=rfq_uom,
        canonical_quantity=None,
        conversion_factor=None,
        normalized_unit_price=None,
        status=NormalizationStatus.UNRESOLVED,
        is_safe=False,
        warning=f"Incompatible unit dimension: cannot convert '{quoted_uom}' to '{rfq_uom}'.",
    )
