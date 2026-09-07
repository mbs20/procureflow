from decimal import Decimal

from procureflow.services.normalization.currency import NormalizationStatus
from procureflow.services.normalization.payment_terms import normalize_payment_terms


def test_payment_terms_net_30():
    res = normalize_payment_terms("Net 30 days")
    assert res.status == NormalizationStatus.NORMALIZED
    assert res.term_code == "NET_30"
    assert res.net_days == 30
    assert res.display_text == "Net 30"


def test_payment_terms_100_advance():
    res = normalize_payment_terms("100% advance payment required")
    assert res.status == NormalizationStatus.NORMALIZED
    assert res.term_code == "ADVANCE_100"
    assert res.advance_percentage == Decimal("100.0")
    assert res.display_text == "100% Advance Payment"


def test_payment_terms_partial_advance():
    res = normalize_payment_terms("30% advance, 70% before delivery")
    assert res.status == NormalizationStatus.NORMALIZED
    assert res.term_code == "ADVANCE_PARTIAL"
    assert res.advance_percentage == Decimal("30")


def test_payment_terms_cod():
    res = normalize_payment_terms("Cash on Delivery")
    assert res.status == NormalizationStatus.NORMALIZED
    assert res.term_code == "COD"


def test_payment_terms_ambiguous_preserved():
    # 'payment upon receipt' must NOT be forced into COD
    res = normalize_payment_terms("Payment upon receipt of shipping notice")
    assert res.status == NormalizationStatus.UNRESOLVED
    assert res.term_code == "CUSTOM"
    assert "Payment upon receipt of shipping notice" in res.display_text
