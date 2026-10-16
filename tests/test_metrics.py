import pandas as pd
import pytest

import metrics as m


def frames(transactions=(), valuations=()):
    tx = pd.DataFrame(list(transactions), columns=["date", "account", "type", "amount"])
    vals = pd.DataFrame(list(valuations), columns=["date", "account", "value"])
    tx["date"] = pd.to_datetime(tx["date"])
    vals["date"] = pd.to_datetime(vals["date"])
    return vals, tx


def test_earning_rate_units():
    rate = m.EarningRate(365_000)
    assert rate.per_day == pytest.approx(1_000)
    assert rate.per_month == pytest.approx(365_000 / 12)
    assert rate.per_hour == pytest.approx(1_000 / 24)


def test_value_rolls_forward_from_last_valuation():
    vals, tx = frames(
        [
            ("2025-01-01", "A", "deposit", 100),
            ("2025-01-31", "A", "deposit", 50),  # same day as valuation: already included
            ("2025-02-10", "A", "deposit", 20),
            ("2025-02-15", "A", "dividend", 5),
            ("2025-02-20", "A", "withdrawal", 10),
        ],
        [("2025-01-31", "A", 160)],
    )
    assert m.account_values(vals, tx, "2025-01-31")["A"] == 160
    assert m.account_values(vals, tx, "2025-02-28")["A"] == 160 + 20 + 5 - 10


def test_never_valued_account_is_worth_its_transactions():
    vals, tx = frames([("2025-01-01", "A", "deposit", 100), ("2025-01-02", "B", "deposit", 7)])
    values = m.account_values(vals, tx, "2025-02-01", accounts=["A", "B", "C"])
    assert values.to_dict() == {"A": 100, "B": 7, "C": 0}


def test_period_result_splits_contributions_income_and_growth():
    vals, tx = frames(
        [
            ("2025-01-01", "A", "deposit", 1_000),
            ("2025-06-01", "A", "deposit", 500),
            ("2025-06-30", "A", "interest", 30),
        ],
        [("2025-01-01", "A", 1_000), ("2025-12-31", "A", 1_600)],
    )
    result = m.period_result(vals, tx, "2025-01-01", "2025-12-31")
    assert result.start_value == 1_000
    assert result.net_contributed == 500
    assert result.earned == pytest.approx(100)
    assert result.income == 30
    assert result.growth == pytest.approx(70)


def test_xirr_matches_simple_annual_growth():
    assert m.xirr([("2024-01-01", -1_000), ("2025-01-01", 1_100)]) == pytest.approx(0.0997, abs=1e-3)


def test_xirr_needs_money_in_and_out():
    assert m.xirr([("2024-01-01", -1_000)]) is None
    assert m.xirr([("2024-01-01", 1_000), ("2025-01-01", 1_100)]) is None


def test_annualized_return_ignores_short_history():
    vals, tx = frames([("2025-01-01", "A", "deposit", 1_000)], [("2025-01-20", "A", 1_050)])
    assert m.annualized_return(vals, tx, None, "2025-01-20") is None


def test_annualized_return_accounts_for_deposit_timing():
    # 1,000 in at the start and 1,000 more halfway; ending at 2,150.
    vals, tx = frames(
        [("2024-01-01", "A", "deposit", 1_000), ("2024-07-01", "A", "deposit", 1_000)],
        [("2025-01-01", "A", 2_150)],
    )
    rate = m.annualized_return(vals, tx, None, "2025-01-01")
    # More than the simple 7.5% because half the money was only invested for half a year.
    assert 0.09 < rate < 0.11


def test_run_rate_uses_each_accounts_rate():
    values = pd.Series({"A": 100_000.0, "B": 50_000.0})
    rates = pd.Series({"A": 0.08, "B": 0.04})
    assert m.run_rate(values, rates).per_year == pytest.approx(10_000)


def test_monthly_breakdown_earnings_add_up():
    vals, tx = frames(
        [("2025-01-05", "A", "deposit", 1_000), ("2025-02-05", "A", "deposit", 1_000)],
        [("2025-01-31", "A", 1_010), ("2025-02-28", "A", 2_040)],
    )
    breakdown = m.monthly_breakdown(vals, tx, "2025-02-28")
    assert breakdown["earned"].tolist() == pytest.approx([10, 30])
    assert breakdown["contributed"].sum() == 2_000


def test_projection_and_time_to_target():
    assert m.project_values(1_000, 100, 0.0, 3) == pytest.approx([1_100, 1_200, 1_300])
    assert m.months_until(0, 100, 0.0, 1_000) == 10
    assert m.months_until(5_000, 0, 0.05, 1_000) == 0
    assert m.months_until(0, 0, 0.05, 1_000) is None


def test_capital_needed():
    assert m.capital_needed(1_000, 0.06) == pytest.approx(200_000)
    assert m.capital_needed(1_000, 0) is None


def test_each_account_grows_at_its_own_rate():
    values = pd.Series({"A": 1_000.0, "B": 1_000.0})
    rates = pd.Series({"A": 0.0, "B": 0.12})
    projected = m.project_accounts(values, pd.Series({"A": 100.0, "B": 0.0}), rates, 12)
    assert projected["A"].iloc[-1] == pytest.approx(2_200)  # contributions only
    assert projected["B"].iloc[-1] == pytest.approx(1_120, rel=1e-6)  # 12% over a year
    assert m.earning_power(projected, rates).iloc[-1] == pytest.approx(1_120 * 0.12 / 12, rel=1e-6)


def test_extra_money_earns_more_in_the_higher_rate_account():
    values = pd.Series({"A": 1_000.0, "B": 1_000.0})
    rates = pd.Series({"A": 0.02, "B": 0.10})
    none = pd.Series({"A": 0.0, "B": 0.0})
    base = m.earning_power(m.project_accounts(values, none, rates, 60), rates).iloc[-1]
    into = lambda acct: m.earning_power(
        m.project_accounts(values, none.add(pd.Series({acct: 500.0}), fill_value=0), rates, 60), rates
    ).iloc[-1] - base
    assert into("B") > into("A") > 0


def test_months_until_accounts():
    values = pd.Series({"A": 0.0, "B": 0.0})
    assert m.months_until_accounts(values, pd.Series({"A": 50.0, "B": 50.0}), pd.Series({"A": 0.0, "B": 0.0}), 1_000) == 10
    assert m.months_until_accounts(values, pd.Series({"A": 0.0, "B": 0.0}), pd.Series({"A": 0.05, "B": 0.05}), 1_000) is None
    assert m.months_until_accounts(pd.Series({"A": 2_000.0}), pd.Series({"A": 0.0}), pd.Series({"A": 0.0}), 1_000) == 0
