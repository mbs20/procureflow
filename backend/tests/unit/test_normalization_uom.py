from decimal import Decimal

from procureflow.services.normalization.currency import NormalizationStatus
from procureflow.services.normalization.uom import normalize_uom_and_price


def test_uom_synonyms_count():
    # 'piece' -> 'pcs'
    res = normalize_uom_and_price(
        quoted_quantity=100,
        quoted_uom="piece",
        quoted_unit_price=12.50,
        rfq_uom="pcs",
    )
    assert res.status == NormalizationStatus.NORMALIZED
    assert res.canonical_uom == "pcs"
    assert res.canonical_quantity == Decimal("100")
    assert res.conversion_factor == Decimal("1.0000")
    assert res.normalized_unit_price == Decimal("12.50")
    assert res.is_safe is True


def test_uom_metric_scaling_mass():
    # Quoted: 500 g at 5.00 USD/g. RFQ requires kg.
    # 500 g = 0.5 kg. Price = 5.00 / 0.001 = 5000.00 USD/kg.
    res = normalize_uom_and_price(
        quoted_quantity=500,
        quoted_uom="g",
        quoted_unit_price=5.00,
        rfq_uom="kg",
    )
    assert res.status == NormalizationStatus.NORMALIZED
    assert res.canonical_quantity == Decimal("0.5000")
    assert res.conversion_factor == Decimal("0.001")
    assert res.normalized_unit_price == Decimal("5000.0000")


def test_uom_price_basis_explicit_packaging_override():
    # Quoted: 10 boxes at 240.00 USD / box. RFQ requires 240 pcs.
    # Without explicit factor -> UNRESOLVED
    unresolved = normalize_uom_and_price(
        quoted_quantity=10,
        quoted_uom="box",
        quoted_unit_price=240.00,
        rfq_uom="pcs",
    )
    assert unresolved.status == NormalizationStatus.UNRESOLVED
    assert unresolved.canonical_quantity is None
    assert unresolved.normalized_unit_price is None
    assert "Packaging unit 'box' cannot be converted" in unresolved.warning

    # With confirmed explicit factor 1 box = 24 pcs
    # 10 boxes * 24 = 240 pcs. Price = 240 / 24 = 10.00 USD/pcs.
    resolved = normalize_uom_and_price(
        quoted_quantity=10,
        quoted_uom="box",
        quoted_unit_price=240.00,
        rfq_uom="pcs",
        explicit_conversion_factor=24.0,
    )
    assert resolved.status == NormalizationStatus.HUMAN_OVERRIDDEN
    assert resolved.canonical_quantity == Decimal("240.0000")
    assert resolved.normalized_unit_price == Decimal("10.0000")
    assert resolved.conversion_factor == Decimal("24.0")


def test_uom_incompatible_dimensions():
    # Length to Mass (m to kg)
    res = normalize_uom_and_price(
        quoted_quantity=10,
        quoted_uom="meter",
        quoted_unit_price=50.0,
        rfq_uom="kg",
    )
    assert res.status == NormalizationStatus.UNRESOLVED
    assert "Incompatible unit dimension" in res.warning
