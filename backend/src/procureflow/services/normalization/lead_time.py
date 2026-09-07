from __future__ import annotations

import re
from typing import NamedTuple

from procureflow.services.normalization.currency import NormalizationStatus


class LeadTimeType(str):
    CALENDAR_DAYS = "calendar_days"
    BUSINESS_DAYS = "business_days"
    WEEKS = "weeks"
    MONTHS = "months"
    RANGE = "range"
    STOCK_AVAILABILITY = "stock_availability"
    AMBIGUOUS = "ambiguous"


class LeadTimeNormalizationResult(NamedTuple):
    original_text: str
    lead_time_type: str
    canonical_days: int | None
    min_days: int | None
    max_days: int | None
    comparison_policy: str | None
    display_text: str
    status: NormalizationStatus
    warning: str | None


def normalize_lead_time(raw_lead_time: str | int | None) -> LeadTimeNormalizationResult:
    """
    Normalizes supplier lead time expressions according to strict procurement rules.

    CRITICAL RULES:
    1. Preserves original supplier wording.
    2. Maintains explicit distinction between calendar days, business days, weeks, months,
       ranges, stock availability, and ambiguous terms.
    3. Never silently assumes business days = calendar days.
    4. Never treats 'in stock' as 0 delivery days without shipping notice.
    5. Conservative range policy (upper bound) is explicitly labeled as comparison policy.
    """
    if raw_lead_time is None:
        return LeadTimeNormalizationResult(
            original_text="Not specified",
            lead_time_type=LeadTimeType.AMBIGUOUS,
            canonical_days=None,
            min_days=None,
            max_days=None,
            comparison_policy=None,
            display_text="Not specified",
            status=NormalizationStatus.UNRESOLVED,
            warning="Lead time not specified in quotation",
        )

    # If raw lead time was stored as an integer from extraction
    if isinstance(raw_lead_time, (int, float)):
        days_int = int(raw_lead_time)
        return LeadTimeNormalizationResult(
            original_text=f"{days_int} days",
            lead_time_type=LeadTimeType.CALENDAR_DAYS,
            canonical_days=days_int,
            min_days=days_int,
            max_days=days_int,
            comparison_policy="Direct calendar day count",
            display_text=f"{days_int} d",
            status=NormalizationStatus.NORMALIZED,
            warning=None,
        )

    text = str(raw_lead_time).strip()
    lower_text = text.lower()

    if not lower_text or lower_text in (
        "none",
        "null",
        "tbd",
        "n/a",
        "to be agreed",
        "upon request",
        "call",
    ):
        return LeadTimeNormalizationResult(
            original_text=text,
            lead_time_type=LeadTimeType.AMBIGUOUS,
            canonical_days=None,
            min_days=None,
            max_days=None,
            comparison_policy=None,
            display_text=text or "Not specified",
            status=NormalizationStatus.UNRESOLVED,
            warning=f"Ambiguous or conditional lead time: '{text}'",
        )

    # Stock availability (In stock, Ex-stock, Immediate availability)
    if re.search(
        r"\b(ex[\s-]?stock|in[\s-]?stock|stock|immediate|ready[\s-]to[\s-]ship)\b", lower_text
    ):
        return LeadTimeNormalizationResult(
            original_text=text,
            lead_time_type=LeadTimeType.STOCK_AVAILABILITY,
            canonical_days=0,
            min_days=0,
            max_days=0,
            comparison_policy="Stock availability (0 manufacturing days; freight/dispatch lead time not included)",
            display_text=f"Ex-stock ({text})",
            status=NormalizationStatus.NORMALIZED,
            warning="Stock availability indicates manufacturing readiness; does not guarantee 0 transit days.",
        )

    # Ambiguous conditional expressions (ARO, upon receipt of order, etc.)
    if re.search(
        r"\b(aro|receipt\s+of\s+order|after\s+order|order\s+confirmation|subject\s+to|depending\s+on)\b",
        lower_text,
    ) and not re.search(r"\d+", lower_text):
        return LeadTimeNormalizationResult(
            original_text=text,
            lead_time_type=LeadTimeType.AMBIGUOUS,
            canonical_days=None,
            min_days=None,
            max_days=None,
            comparison_policy=None,
            display_text=text,
            status=NormalizationStatus.UNRESOLVED,
            warning=f"Conditional lead time without explicit duration: '{text}'",
        )

    # Range of weeks (e.g. "2-3 weeks", "2 to 4 wks")
    range_weeks_match = re.search(r"(\d+)\s*(?:-|to|–)\s*(\d+)\s*(?:weeks?|wks?|w)\b", lower_text)
    if range_weeks_match:
        w_min = int(range_weeks_match.group(1))
        w_max = int(range_weeks_match.group(2))
        d_min = w_min * 7
        d_max = w_max * 7
        return LeadTimeNormalizationResult(
            original_text=text,
            lead_time_type=LeadTimeType.RANGE,
            canonical_days=d_max,
            min_days=d_min,
            max_days=d_max,
            comparison_policy=f"Conservative comparison policy: upper bound of range ({d_max} calendar days)",
            display_text=f"{w_min}–{w_max} wks ({d_min}–{d_max} d, max: {d_max} d)",
            status=NormalizationStatus.NORMALIZED,
            warning=None,
        )

    # Range of days (e.g. "10-15 days", "10 to 14 calendar days")
    range_days_match = re.search(
        r"(\d+)\s*(?:-|to|–)\s*(\d+)\s*(?:cal(?:endar)?\s*)?days?\b", lower_text
    )
    if range_days_match and "business" not in lower_text and "working" not in lower_text:
        d_min = int(range_days_match.group(1))
        d_max = int(range_days_match.group(2))
        return LeadTimeNormalizationResult(
            original_text=text,
            lead_time_type=LeadTimeType.RANGE,
            canonical_days=d_max,
            min_days=d_min,
            max_days=d_max,
            comparison_policy=f"Conservative comparison policy: upper bound of range ({d_max} calendar days)",
            display_text=f"{d_min}–{d_max} d (max: {d_max} d)",
            status=NormalizationStatus.NORMALIZED,
            warning=None,
        )

    # Range of business days (e.g. "10-15 business days")
    range_bdays_match = re.search(
        r"(\d+)\s*(?:-|to|–)\s*(\d+)\s*(?:business|working)\s*days?\b", lower_text
    )
    if range_bdays_match:
        bd_min = int(range_bdays_match.group(1))
        bd_max = int(range_bdays_match.group(2))
        return LeadTimeNormalizationResult(
            original_text=text,
            lead_time_type=LeadTimeType.BUSINESS_DAYS,
            canonical_days=None,
            min_days=bd_min,
            max_days=bd_max,
            comparison_policy="Preserved as business days; not converted to calendar days without explicit working calendar",
            display_text=f"{bd_min}–{bd_max} business days",
            status=NormalizationStatus.NORMALIZED,
            warning="Business days preserved distinct from calendar days.",
        )

    # Single weeks (e.g. "3 weeks", "4 wks")
    single_week_match = re.search(r"(\d+)\s*(?:weeks?|wks?|w)\b", lower_text)
    if single_week_match:
        w_val = int(single_week_match.group(1))
        d_val = w_val * 7
        return LeadTimeNormalizationResult(
            original_text=text,
            lead_time_type=LeadTimeType.WEEKS,
            canonical_days=d_val,
            min_days=d_val,
            max_days=d_val,
            comparison_policy=f"7 calendar days per week ({w_val} wks = {d_val} d)",
            display_text=f"{w_val} wks ({d_val} d)",
            status=NormalizationStatus.NORMALIZED,
            warning=None,
        )

    # Single business days (e.g. "10 business days", "10 working days")
    single_bday_match = re.search(r"(\d+)\s*(?:business|working)\s*days?\b", lower_text)
    if single_bday_match:
        bd_val = int(single_bday_match.group(1))
        return LeadTimeNormalizationResult(
            original_text=text,
            lead_time_type=LeadTimeType.BUSINESS_DAYS,
            canonical_days=None,
            min_days=bd_val,
            max_days=bd_val,
            comparison_policy="Preserved as business days; not converted to calendar days without explicit calendar",
            display_text=f"{bd_val} business days",
            status=NormalizationStatus.NORMALIZED,
            warning="Business days preserved distinct from calendar days.",
        )

    # Months (e.g. "2 months")
    months_match = re.search(r"(\d+)\s*(?:months?|mths?)\b", lower_text)
    if months_match:
        m_val = int(months_match.group(1))
        return LeadTimeNormalizationResult(
            original_text=text,
            lead_time_type=LeadTimeType.MONTHS,
            canonical_days=None,
            min_days=None,
            max_days=None,
            comparison_policy="Preserved as months; not converted to fixed 30-day buckets as authoritative value",
            display_text=f"{m_val} month(s)",
            status=NormalizationStatus.NORMALIZED,
            warning="Monthly lead time preserved without fixed day count assumption.",
        )

    # Single calendar days (e.g. "14 days", "14 d", "14 calendar days")
    single_day_match = re.search(r"(\d+)\s*(?:cal(?:endar)?\s*)?days?\b", lower_text)
    if single_day_match:
        d_val = int(single_day_match.group(1))
        return LeadTimeNormalizationResult(
            original_text=text,
            lead_time_type=LeadTimeType.CALENDAR_DAYS,
            canonical_days=d_val,
            min_days=d_val,
            max_days=d_val,
            comparison_policy="Direct calendar day count",
            display_text=f"{d_val} d",
            status=NormalizationStatus.NORMALIZED,
            warning=None,
        )

    # Fallback for plain digits
    if lower_text.isdigit():
        d_val = int(lower_text)
        return LeadTimeNormalizationResult(
            original_text=text,
            lead_time_type=LeadTimeType.CALENDAR_DAYS,
            canonical_days=d_val,
            min_days=d_val,
            max_days=d_val,
            comparison_policy="Direct calendar day count",
            display_text=f"{d_val} d",
            status=NormalizationStatus.NORMALIZED,
            warning=None,
        )

    # Unrecognized / complex
    return LeadTimeNormalizationResult(
        original_text=text,
        lead_time_type=LeadTimeType.AMBIGUOUS,
        canonical_days=None,
        min_days=None,
        max_days=None,
        comparison_policy=None,
        display_text=text,
        status=NormalizationStatus.UNRESOLVED,
        warning=f"Unrecognized lead time format: '{text}'",
    )
