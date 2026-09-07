from procureflow.services.normalization.currency import NormalizationStatus
from procureflow.services.normalization.lead_time import (
    LeadTimeType,
    normalize_lead_time,
)


def test_lead_time_calendar_days():
    res = normalize_lead_time("14 days")
    assert res.status == NormalizationStatus.NORMALIZED
    assert res.lead_time_type == LeadTimeType.CALENDAR_DAYS
    assert res.canonical_days == 14
    assert res.display_text == "14 d"


def test_lead_time_weeks():
    res = normalize_lead_time("3 weeks")
    assert res.status == NormalizationStatus.NORMALIZED
    assert res.lead_time_type == LeadTimeType.WEEKS
    assert res.canonical_days == 21
    assert "3 wks (21 d)" in res.display_text


def test_lead_time_range_upper_bound_policy():
    res = normalize_lead_time("2-3 weeks")
    assert res.status == NormalizationStatus.NORMALIZED
    assert res.lead_time_type == LeadTimeType.RANGE
    assert res.min_days == 14
    assert res.max_days == 21
    assert res.canonical_days == 21
    assert "Conservative comparison policy" in res.comparison_policy


def test_lead_time_business_days_distinct():
    # Business days must NOT be silently turned into 14 calendar days
    res = normalize_lead_time("10 business days")
    assert res.status == NormalizationStatus.NORMALIZED
    assert res.lead_time_type == LeadTimeType.BUSINESS_DAYS
    assert res.min_days == 10
    assert res.max_days == 10
    assert "10 business days" in res.display_text
    assert "Business days preserved distinct from calendar days" in res.warning


def test_lead_time_stock_availability():
    res = normalize_lead_time("In Stock")
    assert res.status == NormalizationStatus.NORMALIZED
    assert res.lead_time_type == LeadTimeType.STOCK_AVAILABILITY
    assert res.canonical_days == 0
    assert "Stock availability" in res.comparison_policy
    assert "does not guarantee 0 transit days" in res.warning


def test_lead_time_ambiguous():
    res = normalize_lead_time("Upon receipt of order")
    assert res.status == NormalizationStatus.UNRESOLVED
    assert res.lead_time_type == LeadTimeType.AMBIGUOUS
    assert res.canonical_days is None
    assert "Conditional lead time" in res.warning
