import datetime as dt
from decimal import Decimal

from procureflow.services.normalization.currency import (
    NormalizationStatus,
    RFQFXRateProvider,
    StaticFXRateProvider,
    convert_currency,
)


def test_static_fx_provider_same_currency():
    prov = StaticFXRateProvider()
    res = prov.get_rate("USD", "USD")
    assert res is not None
    assert res.rate == Decimal("1.000000")
    assert res.is_synthetic is True


def test_static_fx_provider_synthetic_conversions():
    prov = StaticFXRateProvider()

    # 1 EUR = 1.0850 USD
    res_eur = prov.get_rate("EUR", "USD")
    assert res_eur is not None
    assert res_eur.rate == Decimal("1.085000")
    assert res_eur.is_synthetic is True

    # 1 MAD = 0.1000 USD
    res_mad = prov.get_rate("MAD", "USD")
    assert res_mad is not None
    assert res_mad.rate == Decimal("0.100000")

    # Derived reciprocal: 1 USD in EUR = 1 / 1.0850 ≈ 0.921659
    res_usd_eur = prov.get_rate("USD", "EUR")
    assert res_usd_eur is not None
    assert abs(res_usd_eur.rate - Decimal("0.921659")) < Decimal("0.0001")


def test_static_fx_provider_unknown_currency():
    prov = StaticFXRateProvider()
    res = prov.get_rate("XYZ", "USD")
    assert res is None


def test_convert_currency_unresolved():
    prov = StaticFXRateProvider()
    converted, fx_res, status, warning = convert_currency(
        amount=100.0,
        from_currency="UNKNOWN_CURRENCY",
        to_currency="USD",
        provider=prov,
    )
    assert status == NormalizationStatus.UNRESOLVED
    assert converted is None
    assert fx_res is None
    assert "No exchange rate available" in warning


def test_rfq_fx_rate_provider_versioning_and_cross_rates():
    rates = {
        "EUR": 1.0850,
        "MAD": 0.1000,
        "GBP": 1.2500,
    }
    prov = RFQFXRateProvider(
        base_currency="USD",
        rates=rates,
        effective_date=dt.date(2026, 3, 1),
        rate_set_version=2,
        is_synthetic=False,
    )

    # Base currency identity
    res_usd = prov.get_rate("USD", "USD")
    assert res_usd.rate == Decimal("1.000000")
    assert res_usd.rate_set_version == 2

    # EUR to USD
    res_eur = prov.get_rate("EUR", "USD")
    assert res_eur.rate == Decimal("1.085000")

    # Cross rate: EUR to MAD = 1.0850 / 0.1000 = 10.85
    res_eur_mad = prov.get_rate("EUR", "MAD")
    assert res_eur_mad.rate == Decimal("10.850000")
