"""
Regression tests for OutputValidator._audit_numerics.

The numeric audit exists to catch hallucinated figures: any number in a model's
answer that is not grounded in the retrieved context is an error. Calendar years
are not figures — they are ordinary prose — and flagging them made every answer
that mentioned the current year fail grounding, which in turn disabled the
deterministic LLM-bypass path.
"""
import pytest

from api.services.llm.validator import OutputValidator


CONTEXT = {"total_bill": 158.1, "usage_kwh": 750.0}


@pytest.mark.parametrize("year", [2024, 2025, 2026, 2030, 1998])
def test_calendar_years_are_not_hallucinations(year):
    """A bare 4-digit year is prose, not an unverified numeric claim."""
    text = f"Your {year} bill was $158.10 across 750 kWh."
    discrepancies, _ = OutputValidator._audit_numerics(text, CONTEXT)
    assert discrepancies == [], f"year {year} flagged: {discrepancies}"


def test_grounded_numbers_still_pass():
    """Numbers present in the context remain valid."""
    text = "Your bill was $158.10 across 750 kWh."
    discrepancies, _ = OutputValidator._audit_numerics(text, CONTEXT)
    assert discrepancies == []


def test_ungrounded_number_is_still_flagged():
    """The audit must keep catching invented figures."""
    text = "Your bill was $842.37 this period."
    discrepancies, _ = OutputValidator._audit_numerics(text, CONTEXT)
    assert any("842.37" in d for d in discrepancies), discrepancies


def test_year_sized_dollar_amount_is_still_flagged():
    """A currency amount that happens to look like a year is not exempt."""
    text = "Your annual spend was $2026.00."
    discrepancies, _ = OutputValidator._audit_numerics(text, CONTEXT)
    assert any("2026" in d for d in discrepancies), discrepancies


def test_year_sized_decimal_is_still_flagged():
    """A decimal beginning with year digits is not a year."""
    text = "Total consumption reached 2026.5 kWh."
    discrepancies, _ = OutputValidator._audit_numerics(text, CONTEXT)
    assert any("2026.5" in d for d in discrepancies), discrepancies
