from __future__ import annotations

import datetime as dt
from collections.abc import Mapping
from decimal import ROUND_HALF_UP, Decimal
from enum import Enum
from typing import Protocol

from pydantic import BaseModel


class NormalizationStatus(str, Enum):
    NORMALIZED = "normalized"
    IDENTICAL = "identical"
    UNRESOLVED = "unresolved"
    HUMAN_OVERRIDDEN = "human_overridden"
    NOT_QUOTED = "not_quoted"


class FXRateResult(BaseModel):
    rate: Decimal
    from_currency: str
    to_currency: str
    effective_date: dt.date
    provider_id: str
    rate_set_version: int | None = None
    is_synthetic: bool = False
    notes: str | None = None


class FXRateProvider(Protocol):
    def get_rate(
        self,
        from_currency: str,
        to_currency: str,
        effective_date: dt.date | None = None,
    ) -> FXRateResult | None: ...


class StaticFXRateProvider:
    """
    Deterministic static exchange rate provider for tests, CI, and demo fixtures.
    CRITICAL: Rates are fixed/synthetic and must never be treated as live market rates.
    Reciprocal and cross-currency rates are deterministically derived from canonical base rates against USD.
    """

    # Canonical synthetic exchange rates against USD (1 Unit of Foreign Currency = X USD)
    DEFAULT_SYNTHETIC_RATES_USD: dict[str, Decimal] = {
        "USD": Decimal("1.0000"),
        "EUR": Decimal("1.0850"),
        "GBP": Decimal("1.2800"),
        "MAD": Decimal("0.1000"),
        "CAD": Decimal("0.7400"),
        "AUD": Decimal("0.6600"),
        "JPY": Decimal("0.0067"),
        "CHF": Decimal("1.1200"),
        "CNY": Decimal("0.1380"),
    }

    def __init__(
        self,
        rates_to_usd: dict[str, Decimal] | None = None,
        effective_date: dt.date | None = None,
    ):
        self.rates_to_usd = rates_to_usd or self.DEFAULT_SYNTHETIC_RATES_USD
        self.effective_date = effective_date or dt.date(2026, 1, 1)
        self.provider_id = "synthetic_fixed_test_data"

    def get_rate(
        self,
        from_currency: str,
        to_currency: str,
        effective_date: dt.date | None = None,
    ) -> FXRateResult | None:
        from_c = from_currency.strip().upper()
        to_c = to_currency.strip().upper()

        if from_c == to_c:
            return FXRateResult(
                rate=Decimal("1.000000"),
                from_currency=from_c,
                to_currency=to_c,
                effective_date=effective_date or self.effective_date,
                provider_id=self.provider_id,
                is_synthetic=True,
                notes="Same currency identity rate",
            )

        if from_c not in self.rates_to_usd or to_c not in self.rates_to_usd:
            return None

        # Deterministically derive cross rate: (from_c in USD) / (to_c in USD)
        from_in_usd = self.rates_to_usd[from_c]
        to_in_usd = self.rates_to_usd[to_c]

        rate = (from_in_usd / to_in_usd).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)

        return FXRateResult(
            rate=rate,
            from_currency=from_c,
            to_currency=to_c,
            effective_date=effective_date or self.effective_date,
            provider_id=self.provider_id,
            is_synthetic=True,
            notes=f"Synthetic fixed test rate derived via USD ({from_c}={from_in_usd} USD, {to_c}={to_in_usd} USD)",
        )


class RFQFXRateProvider:
    """
    RFQ-specific frozen exchange rate provider.
    Reads rates configured for the specific RFQ rate-set version.
    Derives reciprocal and cross rates deterministically from the canonical rate set.
    """

    def __init__(
        self,
        base_currency: str,
        rates: Mapping[str, float | Decimal],
        effective_date: dt.date,
        provider_id: str = "rfq_frozen_rates",
        rate_set_version: int = 1,
        is_synthetic: bool = False,
    ):
        self.base_currency = base_currency.strip().upper()
        self.rates = {k.strip().upper(): Decimal(str(v)) for k, v in rates.items()}
        self.rates[self.base_currency] = Decimal("1.0000")
        self.effective_date = effective_date
        self.provider_id = provider_id
        self.rate_set_version = rate_set_version
        self.is_synthetic = is_synthetic

    def get_rate(
        self,
        from_currency: str,
        to_currency: str,
        effective_date: dt.date | None = None,
    ) -> FXRateResult | None:
        from_c = from_currency.strip().upper()
        to_c = to_currency.strip().upper()

        if from_c == to_c:
            return FXRateResult(
                rate=Decimal("1.000000"),
                from_currency=from_c,
                to_currency=to_c,
                effective_date=self.effective_date,
                provider_id=self.provider_id,
                rate_set_version=self.rate_set_version,
                is_synthetic=self.is_synthetic,
                notes="Same currency identity rate",
            )

        if from_c not in self.rates or to_c not in self.rates:
            return None

        from_in_base = self.rates[from_c]
        to_in_base = self.rates[to_c]

        if to_in_base == Decimal("0"):
            return None

        derived_rate = (from_in_base / to_in_base).quantize(
            Decimal("0.000001"), rounding=ROUND_HALF_UP
        )

        return FXRateResult(
            rate=derived_rate,
            from_currency=from_c,
            to_currency=to_c,
            effective_date=self.effective_date,
            provider_id=self.provider_id,
            rate_set_version=self.rate_set_version,
            is_synthetic=self.is_synthetic,
            notes=f"Derived from RFQ rate set v{self.rate_set_version} ({from_c}={from_in_base} {self.base_currency})",
        )


def convert_currency(
    amount: Decimal | float,
    from_currency: str,
    to_currency: str,
    provider: FXRateProvider,
    effective_date: dt.date | None = None,
) -> tuple[Decimal | None, FXRateResult | None, NormalizationStatus, str | None]:
    """
    Converts amount from from_currency to to_currency using the given provider.
    Returns (converted_amount, fx_result, status, warning_or_error_message).
    """
    amt_dec = Decimal(str(amount))
    from_c = from_currency.strip().upper()
    to_c = to_currency.strip().upper()

    if from_c == to_c:
        fx_res = provider.get_rate(from_c, to_c, effective_date)
        return amt_dec, fx_res, NormalizationStatus.IDENTICAL, None

    fx_res = provider.get_rate(from_c, to_c, effective_date)
    if not fx_res:
        return (
            None,
            None,
            NormalizationStatus.UNRESOLVED,
            f"No exchange rate available for currency pair {from_c} -> {to_c}",
        )

    converted = (amt_dec * fx_res.rate).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    return converted, fx_res, NormalizationStatus.NORMALIZED, None
