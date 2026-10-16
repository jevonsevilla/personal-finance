"""Reads and writes the hub's data: plain CSV/JSON files you can also edit by hand.

Files live in ``data/hub/`` (gitignored) unless ``FINANCE_HUB_DATA`` points
elsewhere.
"""

import json
import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

import metrics
from metrics import TRANSACTION_TYPES

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("FINANCE_HUB_DATA", REPO_ROOT / "data" / "hub"))
SAMPLE_DIR = Path(__file__).resolve().parent / "sample"

ACCOUNT_COLUMNS = ["account", "type", "platform", "expected_return_pct", "use_past_performance", "notes"]
TRANSACTION_COLUMNS = ["date", "account", "type", "amount", "note"]
VALUATION_COLUMNS = ["date", "account", "value"]
RECURRING_COLUMNS = ["account", "amount", "day", "start_date", "end_date", "last_applied"]
RECURRING_NOTE = "Recurring"

# Starting assumptions only: edit each account's rate to match what you expect.
ACCOUNT_TYPES = {
    "Stocks": 8.0,
    "ETF / Index fund": 8.0,
    "Mutual fund / UITF": 6.0,
    "Bonds": 6.0,
    "MP2": 7.0,
    "Time deposit": 4.5,
    "Savings": 4.0,
    "Crypto": 0.0,
    "Real estate": 4.0,
    "Cash": 0.0,
    "Other": 0.0,
}

DEFAULT_SETTINGS = {
    "currency": "₱",
    "monthly_take_home": 0.0,
    "monthly_expenses": 0.0,
    "work_hours_per_week": 40.0,
    "safe_withdrawal_rate_pct": 4.0,
    "milestones": [],
}


@dataclass
class Ledger:
    accounts: pd.DataFrame
    transactions: pd.DataFrame
    valuations: pd.DataFrame
    settings: dict
    # Accounts whose expected return comes from their holdings' past performance.
    past_performance: dict = field(default_factory=dict)

    @property
    def account_names(self) -> list[str]:
        return self.accounts["account"].tolist()

    def uses_past_performance(self, account: str) -> bool:
        """Whether this account takes its expected return from its holdings' history.

        Defaults to yes, except for crypto: its history is far too extreme to plan on.
        """
        row = self.accounts[self.accounts["account"] == account]
        if row.empty:
            return False
        flag = row.iloc[0]["use_past_performance"]
        return bool(flag) if pd.notna(flag) else row.iloc[0]["type"] != "Crypto"

    @property
    def expected_rates(self) -> pd.Series:
        """Expected annual return per account, as a decimal."""
        rates = self.accounts.set_index("account")["expected_return_pct"].fillna(0) / 100
        for account, info in self.past_performance.items():
            if account in rates.index:
                rates[account] = info["rate"]
        return rates


def _path(name: str) -> Path:
    return DATA_DIR / name


def is_initialized() -> bool:
    return _path("accounts.csv").exists()


def _read_csv(name: str, columns: list[str]) -> pd.DataFrame:
    path = _path(name)
    if not path.exists():
        return pd.DataFrame(columns=columns)
    df = pd.read_csv(path, dtype={"account": str, "note": str, "notes": str})
    return df.reindex(columns=columns)


def _with_dates(df: pd.DataFrame) -> pd.DataFrame:
    df["date"] = pd.to_datetime(df["date"]).dt.normalize()
    return df.sort_values("date", kind="stable").reset_index(drop=True)


def load() -> Ledger:
    accounts = _read_csv("accounts.csv", ACCOUNT_COLUMNS)
    accounts["expected_return_pct"] = pd.to_numeric(accounts["expected_return_pct"])
    accounts["use_past_performance"] = accounts["use_past_performance"].map(
        lambda v: None if pd.isna(v) else str(v).strip().lower() == "true"
    )
    accounts[["platform", "notes"]] = accounts[["platform", "notes"]].fillna("")

    transactions = _with_dates(_read_csv("transactions.csv", TRANSACTION_COLUMNS))
    transactions["type"] = transactions["type"].str.strip().str.lower()
    transactions["amount"] = pd.to_numeric(transactions["amount"]).abs()
    transactions["note"] = transactions["note"].fillna("")
    transactions = transactions[transactions["type"].isin(TRANSACTION_TYPES)]

    valuations = _with_dates(_read_csv("valuations.csv", VALUATION_COLUMNS))
    valuations["value"] = pd.to_numeric(valuations["value"])

    import prices  # here, not at the top: prices imports this module

    manual = (accounts.set_index("account")["expected_return_pct"].fillna(0) / 100).to_dict()
    past = prices.historical_rates(prices.load_holdings(), prices.load_cache(), manual=manual)
    ledger = Ledger(accounts, transactions, valuations, load_settings())
    ledger.past_performance = {a: i for a, i in past.items() if ledger.uses_past_performance(a)}
    return ledger


def load_settings() -> dict:
    path = _path("settings.json")
    saved = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    return {**DEFAULT_SETTINGS, **saved}


def _write_csv(df: pd.DataFrame, name: str, columns: list[str]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    out = df.reindex(columns=columns).copy()
    if "date" in out:
        out["date"] = pd.to_datetime(out["date"]).dt.strftime("%Y-%m-%d")
        out = out.sort_values(["date", "account"], kind="stable")
    out.to_csv(_path(name), index=False)


def save_accounts(df: pd.DataFrame) -> None:
    _write_csv(df, "accounts.csv", ACCOUNT_COLUMNS)


def save_transactions(df: pd.DataFrame) -> None:
    _write_csv(df, "transactions.csv", TRANSACTION_COLUMNS)


def save_valuations(df: pd.DataFrame) -> None:
    _write_csv(df, "valuations.csv", VALUATION_COLUMNS)


def load_recurring() -> pd.DataFrame:
    df = _read_csv("recurring.csv", RECURRING_COLUMNS)
    for col in ("start_date", "end_date", "last_applied"):
        df[col] = pd.to_datetime(df[col])
    df["amount"] = pd.to_numeric(df["amount"])
    df["day"] = pd.to_numeric(df["day"]).astype("Int64")
    return df


def save_recurring(df: pd.DataFrame) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    out = df.reindex(columns=RECURRING_COLUMNS).copy()
    for col in ("start_date", "end_date", "last_applied"):
        out[col] = pd.to_datetime(out[col]).dt.strftime("%Y-%m-%d")
    out.to_csv(_path("recurring.csv"), index=False)


def _occurrences(rule, through: pd.Timestamp) -> list[pd.Timestamp]:
    """Dates this rule is due after its last run, up to ``through``."""
    end = through if pd.isna(rule.end_date) else min(through, rule.end_date)
    after = rule.start_date - pd.Timedelta(days=1)
    if pd.notna(rule.last_applied):
        after = max(after, rule.last_applied)
    dates = []
    for month in pd.period_range(rule.start_date, end, freq="M"):
        due = month.to_timestamp() + pd.Timedelta(days=min(int(rule.day), month.days_in_month) - 1)
        if after < due <= end:
            dates.append(due)
    return dates


def apply_recurring(today: pd.Timestamp) -> int:
    """Log a deposit for every recurring investment that has come due. Returns how many."""
    rules = load_recurring()
    if rules.empty:
        return 0
    rows = []
    for i, rule in rules.iterrows():
        if pd.isna(rule["account"]) or pd.isna(rule["amount"]) or pd.isna(rule["day"]) or pd.isna(rule["start_date"]):
            continue
        due = _occurrences(rule, today)
        rows += [
            {"date": d, "account": rule["account"], "type": "deposit", "amount": rule["amount"], "note": RECURRING_NOTE}
            for d in due
        ]
        if due:
            rules.at[i, "last_applied"] = due[-1]
    if rows:
        existing = _read_csv("transactions.csv", TRANSACTION_COLUMNS)
        new = pd.DataFrame(rows)
        save_transactions(new if existing.empty else pd.concat([existing, new]))
        save_recurring(rules)
    return len(rows)


def save_settings(settings: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    _path("settings.json").write_text(
        json.dumps(settings, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def add_transaction(ledger: Ledger, **row) -> None:
    save_transactions(pd.concat([ledger.transactions, pd.DataFrame([row])]))


def add_valuations(ledger: Ledger, rows: list[dict]) -> None:
    """Record valuations, replacing any existing one for the same account and day."""
    new = _with_dates(pd.DataFrame(rows, columns=VALUATION_COLUMNS))
    replaced = set(zip(new["date"], new["account"]))
    old = ledger.valuations
    kept = old[[key not in replaced for key in zip(old["date"], old["account"])]]
    save_valuations(pd.concat([kept, new]))


STARTING_POINT_NOTE = "Starting point: current value"


def start_from_current_value(ledger: Ledger, accounts: list[str], today: pd.Timestamp) -> dict[str, float]:
    """Make each account's put-in equal its current value, so earnings count from today.

    Adds a deposit (or withdrawal) for the difference. Returns the signed gap per account
    that needed one.
    """
    rows, gaps = [], {}
    for account in accounts:
        mine = ledger.transactions[ledger.transactions["account"] == account]
        put_in = metrics.net_contributions(mine, None, today)
        worth = float(metrics.account_values(ledger.valuations, ledger.transactions, today, [account]).iloc[0])
        gap = worth - put_in
        if abs(gap) < 0.5:
            continue
        gaps[account] = gap
        rows.append(
            {
                "date": today,
                "account": account,
                "type": "deposit" if gap > 0 else "withdrawal",
                "amount": round(abs(gap), 2),
                "note": STARTING_POINT_NOTE,
            }
        )
    if rows:
        new = pd.DataFrame(rows)
        save_transactions(new if ledger.transactions.empty else pd.concat([ledger.transactions, new]))
    return gaps


def remove_account(ledger: Ledger, account: str) -> None:
    """Delete an account together with all of its transactions and valuations."""
    save_accounts(ledger.accounts[ledger.accounts["account"] != account])
    save_transactions(ledger.transactions[ledger.transactions["account"] != account])
    save_valuations(ledger.valuations[ledger.valuations["account"] != account])
    rules = load_recurring()
    save_recurring(rules[rules["account"] != account])
    holdings = _read_csv("holdings.csv", ["account", "ticker", "shares", "currency"])
    holdings[holdings["account"] != account].to_csv(_path("holdings.csv"), index=False)


def start_empty() -> None:
    save_accounts(pd.DataFrame(columns=ACCOUNT_COLUMNS))
    save_transactions(pd.DataFrame(columns=TRANSACTION_COLUMNS))
    save_valuations(pd.DataFrame(columns=VALUATION_COLUMNS))
    save_recurring(pd.DataFrame(columns=RECURRING_COLUMNS))
    save_settings(DEFAULT_SETTINGS)


def load_sample() -> None:
    """Replace the current data with the bundled sample portfolio."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    for stale in ("recurring.csv", "holdings.csv", "prices.json"):
        _path(stale).unlink(missing_ok=True)
    for file in SAMPLE_DIR.iterdir():
        shutil.copy(file, _path(file.name))
