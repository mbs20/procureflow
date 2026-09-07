from __future__ import annotations

import re
from decimal import Decimal
from typing import NamedTuple

from procureflow.services.normalization.currency import NormalizationStatus


class PaymentTermsNormalizationResult(NamedTuple):
    original_text: str
    term_code: str  # e.g. "NET_30", "ADVANCE_100", "ADVANCE_PARTIAL", "COD", "LC", "CUSTOM"
    net_days: int | None
    advance_percentage: Decimal | None
    display_text: str
    status: NormalizationStatus
    warning: str | None


def normalize_payment_terms(raw_terms: str | None) -> PaymentTermsNormalizationResult:
    """
    Classifies supplier payment terms conservatively.

    CRITICAL RULES:
    1. Preserves exact original supplier text.
    2. Does not force ambiguous or complex terms into misleading numeric codes.
    3. 'Payment upon receipt' is preserved as CUSTOM/UNRESOLVED unless COD is explicit.
    4. Deterministically recognizes standard Net-N, 100% Advance, and clear Partial Advance.
    """
    if raw_terms is None:
        return PaymentTermsNormalizationResult(
            original_text="Not specified",
            term_code="CUSTOM",
            net_days=None,
            advance_percentage=None,
            display_text="Not specified",
            status=NormalizationStatus.UNRESOLVED,
            warning="Payment terms not specified in quotation",
        )

    text = str(raw_terms).strip()
    lower_text = text.lower()

    if not lower_text or lower_text in (
        "none",
        "null",
        "tbd",
        "n/a",
        "as agreed",
        "standard terms",
        "to be discussed",
    ):
        return PaymentTermsNormalizationResult(
            original_text=text,
            term_code="CUSTOM",
            net_days=None,
            advance_percentage=None,
            display_text=text or "Not specified",
            status=NormalizationStatus.UNRESOLVED,
            warning=f"Unspecified or ambiguous payment terms: '{text}'",
        )

    # 1. Net N terms (e.g. Net 30, Net 60, 30 days net, Net 30 days from invoice)
    net_match = re.search(r"\b(?:net\s*(\d+)|(\d+)\s*days?\s*net)\b", lower_text)
    if net_match:
        days_str = net_match.group(1) or net_match.group(2)
        days_int = int(days_str)
        return PaymentTermsNormalizationResult(
            original_text=text,
            term_code=f"NET_{days_int}",
            net_days=days_int,
            advance_percentage=None,
            display_text=f"Net {days_int}",
            status=NormalizationStatus.NORMALIZED,
            warning=None,
        )

    # 2. 100% Advance / Prepayment
    if re.search(
        r"\b(100%\s*advance|100%\s*prepayment|full\s*advance|full\s*prepayment|payment\s*in\s*advance|prepayment\s*in\s*full)\b",
        lower_text,
    ):
        return PaymentTermsNormalizationResult(
            original_text=text,
            term_code="ADVANCE_100",
            net_days=0,
            advance_percentage=Decimal("100.0"),
            display_text="100% Advance Payment",
            status=NormalizationStatus.NORMALIZED,
            warning=None,
        )

    # 3. Partial Advance (e.g. 30% advance / 70% before shipment)
    partial_adv_match = re.search(r"(\d+)\s*%\s*(?:advance|deposit|prepayment|upfront)", lower_text)
    if partial_adv_match:
        pct_val = Decimal(partial_adv_match.group(1))
        return PaymentTermsNormalizationResult(
            original_text=text,
            term_code="ADVANCE_PARTIAL",
            net_days=None,
            advance_percentage=pct_val,
            display_text=f"{pct_val}% Advance / Balance Terms",
            status=NormalizationStatus.NORMALIZED,
            warning="Partial advance terms require verification of remaining milestone schedule.",
        )

    # 4. Explicit Cash on Delivery (COD)
    if re.search(r"\b(cod|cash\s+on\s+delivery)\b", lower_text):
        return PaymentTermsNormalizationResult(
            original_text=text,
            term_code="COD",
            net_days=0,
            advance_percentage=Decimal("0.0"),
            display_text="Cash on Delivery (COD)",
            status=NormalizationStatus.NORMALIZED,
            warning=None,
        )

    # 5. Letter of Credit (LC)
    if re.search(r"\b(letter\s+of\s+credit|lc\s+at\s+sight|irrevocable\s+lc|l/c)\b", lower_text):
        return PaymentTermsNormalizationResult(
            original_text=text,
            term_code="LC",
            net_days=None,
            advance_percentage=None,
            display_text="Letter of Credit (LC)",
            status=NormalizationStatus.NORMALIZED,
            warning="Documentary credit terms apply.",
        )

    # 6. Ambiguous terms like 'payment upon receipt', 'milestone payments', 'retention' -> CUSTOM / UNRESOLVED
    return PaymentTermsNormalizationResult(
        original_text=text,
        term_code="CUSTOM",
        net_days=None,
        advance_percentage=None,
        display_text=text,
        status=NormalizationStatus.UNRESOLVED,
        warning=f"Non-standard or ambiguous contractual payment terms preserved verbatim: '{text}'",
    )
