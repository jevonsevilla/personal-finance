"""Investment math for the finance hub.

Conventions used throughout:
- ``deposit`` / ``withdrawal`` move your own money into or out of an account.
- ``dividend`` / ``interest`` are earnings paid *into* the account. If you move
  them out to spend, log a withdrawal as well.
- A valuation is an account's total value on its date, including every
  transaction dated that same day.
- Rates are decimals (0.07 == 7% a year).
"""

from dataclasses import dataclass
from datetime import date, datetime

import numpy as np
import pandas as pd

DAYS_PER_YEAR = 365
HOURS_PER_YEAR = DAYS_PER_YEAR * 24
SECONDS_PER_YEAR = HOURS_PER_YEAR * 3600
DAYS_PER_MONTH = DAYS_PER_YEAR / 12

FLOW_SIGNS = {"deposit": 1.0, "withdrawal": -1.0}
INCOME_TYPES = ("dividend", "interest")
TRANSACTION_TYPES = (*FLOW_SIGNS, *INCOME_TYPES)
VALUE_EFFECT = {**FLOW_SIGNS, **{t: 1.0 for t in INCOME_TYPES}}

# Annualizing a few weeks of returns produces meaningless numbers.
MIN_DAYS_FOR_ANNUALIZED = 90

DateLike = date | datetime | pd.Timestamp | str


@dataclass(frozen=True)
class EarningRate:
    """An amount earned per year, expressed per unit of time."""

    per_year: float

    @property
    def per_month(self) -> float:
        return self.per_year / 12

    @property
    def per_day(self) -> float:
        return self.per_year / DAYS_PER_YEAR

    @property
    def per_hour(self) -> float:
        return self.per_year / HOURS_PER_YEAR

    @property
    def per_second(self) -> float:
        return self.per_year / SECONDS_PER_YEAR


@dataclass(frozen=True)
class PeriodResult:
    """What a set of accounts did between two dates (start exclusive)."""

    start_value: float
    end_value: float
    net_contributed: float
    income: float

    @property
    def earned(self) -> float:
        """Change in value that did not come from your own deposits."""
        return self.end_value - self.start_value - self.net_contributed

    @property
    def growth(self) -> float:
        """Earnings from price changes, i.e. everything that wasn't paid out."""
        return self.earned - self.income


def _ts(value: DateLike) -> pd.Timestamp:
    return pd.Timestamp(value).normalize()


def _between(df: pd.DataFrame, start: DateLike | None, end: DateLike) -> pd.DataFrame:
    mask = df["date"] <= _ts(end)
    if start is not None:
        mask &= df["date"] > _ts(start)
    return df[mask]


def first_activity(
    valuations: pd.DataFrame, transactions: pd.DataFrame
) -> pd.Timestamp | None:
    dates = pd.concat([valuations["date"], transactions["date"]])
    return None if dates.empty else dates.min()


def account_values(
    valuations: pd.DataFrame,
    transactions: pd.DataFrame,
    on: DateLike,
    accounts: list[str] | None = None,
) -> pd.Series:
    """Estimated value of each account on ``on``, indexed by account name.

    Starts from each account's latest valuation on or before ``on`` and adds the
    deposits, withdrawals and income logged after it. An account that was never
    valued is worth the sum of its transactions.
    """
    on = _ts(on)
    vals = valuations[valuations["date"] <= on].sort_values("date")
    latest = vals.groupby("account").tail(1).set_index("account")

    tx = transactions[transactions["date"] <= on]
    valued_on = tx["account"].map(latest["date"])
    tx = tx[valued_on.isna() | (tx["date"] > valued_on)]
    change = (tx["amount"] * tx["type"].map(VALUE_EFFECT).fillna(0)).groupby(
        tx["account"]
    ).sum()

    values = latest["value"].add(change, fill_value=0.0)
    if accounts is not None:
        values = values.reindex(accounts, fill_value=0.0)
    return values.astype(float)


def portfolio_value(
    valuations: pd.DataFrame, transactions: pd.DataFrame, on: DateLike
) -> float:
    return float(account_values(valuations, transactions, on).sum())


def net_contributions(
    transactions: pd.DataFrame, start: DateLike | None, end: DateLike
) -> float:
    """Deposits minus withdrawals in (start, end]."""
    tx = _between(transactions, start, end)
    return float((tx["amount"] * tx["type"].map(FLOW_SIGNS).fillna(0)).sum())


def income(transactions: pd.DataFrame, start: DateLike | None, end: DateLike) -> float:
    """Dividends and interest received in (start, end]."""
    tx = _between(transactions, start, end)
    return float(tx.loc[tx["type"].isin(INCOME_TYPES), "amount"].sum())


def period_result(
    valuations: pd.DataFrame,
    transactions: pd.DataFrame,
    start: DateLike | None,
    end: DateLike,
) -> PeriodResult:
    """Value change and its sources over (start, end]; ``start=None`` means ever."""
    start_value = (
        0.0 if start is None else portfolio_value(valuations, transactions, start)
    )
    return PeriodResult(
        start_value=start_value,
        end_value=portfolio_value(valuations, transactions, end),
        net_contributed=net_contributions(transactions, start, end),
        income=income(transactions, start, end),
    )


def xirr(cashflows: list[tuple[DateLike, float]]) -> float | None:
    """Annual rate that makes the cash flows' net present value zero.

    Use the investor's point of view: money you put in is negative, money you
    take out (including what you could withdraw today) is positive.
    """
    flows = [(_ts(d), float(a)) for d, a in cashflows if a]
    if not any(a > 0 for _, a in flows) or not any(a < 0 for _, a in flows):
        return None

    t0 = min(d for d, _ in flows)
    timed = [((d - t0).days / DAYS_PER_YEAR, a) for d, a in flows]

    def npv(rate: float) -> float:
        return sum(a / (1 + rate) ** t for t, a in timed)

    lo, hi = -0.9999, 10.0
    f_lo, f_hi = npv(lo), npv(hi)
    while f_lo * f_hi > 0 and hi < 1e6:
        hi *= 10
        f_hi = npv(hi)
    if f_lo * f_hi > 0:
        return None

    # Bisection: slower than Newton but never diverges.
    for _ in range(200):
        mid = (lo + hi) / 2
        f_mid = npv(mid)
        if f_lo * f_mid <= 0:
            hi = mid
        else:
            lo, f_lo = mid, f_mid
        if hi - lo < 1e-10:
            break
    return (lo + hi) / 2


def annualized_return(
    valuations: pd.DataFrame,
    transactions: pd.DataFrame,
    start: DateLike | None,
    end: DateLike,
) -> float | None:
    """Money-weighted annual return (XIRR) over (start, end].

    Returns None when the period has under ``MIN_DAYS_FOR_ANNUALIZED`` days of
    history, because annualizing a few weeks of returns is noise.
    """
    end = _ts(end)
    flows: list[tuple[DateLike, float]] = []
    if start is not None:
        flows.append((start, -portfolio_value(valuations, transactions, start)))

    tx = _between(transactions, start, end)
    tx = tx[tx["type"].isin(FLOW_SIGNS)]
    flows += [
        (d, -a * FLOW_SIGNS[t]) for d, a, t in zip(tx["date"], tx["amount"], tx["type"])
    ]
    flows.append((end, portfolio_value(valuations, transactions, end)))

    begun = [_ts(d) for d, a in flows if a]
    if not begun or (end - min(begun)).days < MIN_DAYS_FOR_ANNUALIZED:
        return None
    return xirr(flows)


def trailing_window_start(
    valuations: pd.DataFrame,
    transactions: pd.DataFrame,
    end: DateLike,
    days: int = DAYS_PER_YEAR,
) -> pd.Timestamp | None:
    """Start of the trailing window, or None if history is shorter than it."""
    first = first_activity(valuations, transactions)
    start = _ts(end) - pd.Timedelta(days=days)
    return None if first is None or start < first else start


def run_rate(values: pd.Series, rates: pd.Series) -> EarningRate:
    """What the accounts earn per year at their annual ``rates``."""
    aligned = rates.reindex(values.index).fillna(0.0)
    return EarningRate(float((values * aligned).sum()))


def period_ends(first: DateLike, end: DateLike) -> pd.DatetimeIndex:
    """Every month end from ``first`` up to ``end``, with ``end`` itself last."""
    end = _ts(end)
    ends = pd.date_range(_ts(first), end, freq="ME")
    if ends.empty or ends[-1] < end:
        ends = ends.append(pd.DatetimeIndex([end]))
    return ends


def value_history(
    valuations: pd.DataFrame,
    transactions: pd.DataFrame,
    dates: pd.DatetimeIndex,
    accounts: list[str],
) -> pd.DataFrame:
    """Account values (columns) on each of ``dates`` (index)."""
    return pd.DataFrame(
        [account_values(valuations, transactions, d, accounts) for d in dates],
        index=dates,
        columns=accounts,
    )


def monthly_breakdown(
    valuations: pd.DataFrame, transactions: pd.DataFrame, end: DateLike
) -> pd.DataFrame:
    """Per-month value, contributions and earnings up to ``end``."""
    first = first_activity(valuations, transactions)
    if first is None:
        return pd.DataFrame(
            columns=["value", "contributed", "earned", "income", "growth"]
        )

    rows, prev = [], None
    for month_end in period_ends(first, end):
        result = period_result(valuations, transactions, prev, month_end)
        rows.append(
            {
                "date": month_end,
                "value": result.end_value,
                "contributed": result.net_contributed,
                "earned": result.earned,
                "income": result.income,
                "growth": result.growth,
            }
        )
        prev = month_end
    return pd.DataFrame(rows).set_index("date")


def account_summary(
    accounts: list[str],
    valuations: pd.DataFrame,
    transactions: pd.DataFrame,
    end: DateLike,
) -> pd.DataFrame:
    """Lifetime value, contributions, earnings and return for each account."""
    rows = []
    for account in accounts:
        vals = valuations[valuations["account"] == account]
        tx = transactions[transactions["account"] == account]
        result = period_result(vals, tx, None, end)
        rows.append(
            {
                "account": account,
                "value": result.end_value,
                "net_contributed": result.net_contributed,
                "earned": result.earned,
                "income": result.income,
                "annualized_return": annualized_return(vals, tx, None, end),
                "last_valued": vals["date"].max() if not vals.empty else pd.NaT,
            }
        )
    return pd.DataFrame(rows).set_index("account")


def monthly_rate(annual_rate: float) -> float:
    return (1 + max(annual_rate, -0.99)) ** (1 / 12) - 1


def project_values(
    start_value: float, monthly_contribution: float, annual_rate: float, months: int
) -> list[float]:
    """Value at the end of each future month, investing at each month end."""
    growth = 1 + monthly_rate(annual_rate)
    values, value = [], start_value
    for _ in range(months):
        value = value * growth + monthly_contribution
        values.append(value)
    return values


def months_until(
    start_value: float,
    monthly_contribution: float,
    annual_rate: float,
    target: float,
    max_months: int = 100 * 12,
) -> int | None:
    """Months until the portfolio reaches ``target``; None if not within limit."""
    if start_value >= target:
        return 0
    growth = 1 + monthly_rate(annual_rate)
    value = start_value
    for month in range(1, max_months + 1):
        value = value * growth + monthly_contribution
        if value >= target:
            return month
    return None


def capital_needed(per_month: float, annual_rate: float) -> float | None:
    """Portfolio size whose earnings at ``annual_rate`` cover ``per_month``."""
    return None if annual_rate <= 0 else per_month * 12 / annual_rate


def project_accounts(
    start_values: pd.Series, monthly: pd.Series, rates: pd.Series, months: int
) -> pd.DataFrame:
    """Each account's value at the end of every future month (rows) at its own rate.

    ``start_values``, ``monthly`` (contribution per month) and ``rates`` (annual, decimal)
    are all indexed by account name.
    """
    accounts = start_values.index
    growth = np.array([1 + monthly_rate(r) for r in rates.reindex(accounts).fillna(0.0)])
    add = monthly.reindex(accounts).fillna(0.0).to_numpy()
    value = start_values.to_numpy(dtype=float)
    out = np.empty((months, len(accounts)))
    for i in range(months):
        value = value * growth + add
        out[i] = value
    return pd.DataFrame(out, index=range(1, months + 1), columns=accounts)


def earning_power(values: pd.DataFrame, rates: pd.Series) -> pd.Series:
    """Monthly earnings of the portfolio at each row, with every account at its own rate."""
    return (values * rates.reindex(values.columns).fillna(0.0)).sum(axis=1) / 12


def months_until_accounts(
    start_values: pd.Series,
    monthly: pd.Series,
    rates: pd.Series,
    target: float,
    max_months: int = 100 * 12,
) -> int | None:
    """Months until the whole portfolio is worth ``target``; None if not within the limit."""
    if start_values.sum() >= target:
        return 0
    totals = project_accounts(start_values, monthly, rates, max_months).sum(axis=1)
    reached = totals[totals >= target]
    return None if reached.empty else int(reached.index[0])
