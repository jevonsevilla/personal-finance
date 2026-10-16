import pandas as pd
import pytest

import prices


def holdings(*rows):
    return pd.DataFrame(rows, columns=prices.HOLDING_COLUMNS)


def test_values_convert_foreign_currency_to_home():
    h = holdings(("US ETFs", "VOO", 10, "USD"), ("US ETFs", "VTI", 5, "USD"))
    values = prices.account_values(h, {"VOO": 500.0, "VTI": 300.0, "USDPHP=X": 60.0}, "PHP")
    assert values["US ETFs"] == pytest.approx((10 * 500 + 5 * 300) * 60)


def test_home_currency_needs_no_fx_rate():
    h = holdings(("Local", "FMETF.PS", 100, "PHP"))
    assert prices.account_values(h, {"FMETF.PS": 120.0}, "PHP") == {"Local": 12_000.0}


def test_account_with_a_missing_price_is_skipped_not_understated():
    h = holdings(("A", "VOO", 1, "USD"), ("A", "XXXX", 1, "USD"), ("B", "VOO", 1, "USD"))
    values = prices.account_values(h, {"VOO": 500.0, "USDPHP=X": 60.0}, "PHP")
    assert "A" not in values and values["B"] == 30_000.0


def cache(history, quotes):
    return {"fetched_at": 0, "quotes": quotes, "history": history}


def test_past_performance_is_weighted_by_holding_value():
    h = holdings(("A", "BIG", 1, "PHP"), ("A", "SMALL", 1, "PHP"))
    c = cache(
        {"BIG": {"cagr": 0.10, "years": 10}, "SMALL": {"cagr": 0.20, "years": 6}},
        {"BIG": 300.0, "SMALL": 100.0},
    )
    result = prices.historical_rates(h, c, "PHP")["A"]
    assert result["rate"] == pytest.approx(0.125)  # (300*10% + 100*20%) / 400
    assert result["years"] == 6


def test_holding_without_history_counts_at_your_estimate_instead_of_blocking_the_account():
    h = holdings(("A", "OLD", 1, "PHP"), ("A", "NEW", 1, "PHP"), ("B", "ONLYNEW", 1, "PHP"))
    c = cache(
        {
            "OLD": {"cagr": 0.12, "years": 9},
            "NEW": {"cagr": None, "years": 0.1},
            "ONLYNEW": {"cagr": None, "years": 0.1},
        },
        {"OLD": 100.0, "NEW": 100.0, "ONLYNEW": 10.0},
    )
    result = prices.historical_rates(h, c, "PHP", manual={"A": 0.04, "B": 0.04})
    assert result["A"]["rate"] == pytest.approx(0.08)  # half at 12%, half at your 4%
    assert result["A"]["fallback"] == ["NEW"]
    assert "B" not in result  # nothing usable, so it keeps your estimate outright


def test_uses_the_currency_yahoo_reports_over_the_one_you_picked():
    h = holdings(("A", "XYZ.L", 10, "USD"))
    quotes = {"XYZ.L": 20.0, "GBPPHP=X": 75.0, "USDPHP=X": 60.0}
    assert prices.account_values(h, quotes, "PHP", {"XYZ.L": "GBP"}) == {"A": 10 * 20 * 75}
    assert prices.account_values(h, quotes, "PHP") == {"A": 10 * 20 * 60}


def test_a_young_fund_does_not_set_the_expected_return():
    h = holdings(("A", "OLD", 1, "PHP"), ("A", "YOUNG", 1, "PHP"))
    c = cache(
        {"OLD": {"cagr": 0.08, "years": 10}, "YOUNG": {"cagr": 0.25, "years": 2.9}},
        {"OLD": 100.0, "YOUNG": 100.0},
    )
    result = prices.historical_rates(h, c, "PHP", manual={"A": 0.06})["A"]
    assert result["rate"] == pytest.approx(0.07)  # YOUNG counts at your 6%, not its 25%
    assert result["fallback"] == ["YOUNG"]
