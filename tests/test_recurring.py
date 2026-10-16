import pandas as pd
import pytest

import store


@pytest.fixture(autouse=True)
def data_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "DATA_DIR", tmp_path)
    store.start_empty()
    store.save_accounts(
        pd.DataFrame([{"account": "A", "type": "Savings", "platform": "", "expected_return_pct": 4.0, "notes": ""}])
    )


def add_rule(**kwargs):
    rule = {"account": "A", "amount": 1000.0, "day": 15, "start_date": "2026-01-10", "end_date": None, "last_applied": None}
    store.save_recurring(pd.DataFrame([{**rule, **kwargs}]))


def deposits():
    return store.load().transactions


def test_logs_each_due_month_once():
    add_rule()
    assert store.apply_recurring(pd.Timestamp("2026-04-20")) == 4
    assert deposits()["date"].dt.strftime("%Y-%m-%d").tolist() == ["2026-01-15", "2026-02-15", "2026-03-15", "2026-04-15"]
    assert store.apply_recurring(pd.Timestamp("2026-04-25")) == 0  # nothing new
    assert store.apply_recurring(pd.Timestamp("2026-05-16")) == 1
    assert len(deposits()) == 5


def test_not_due_until_the_day_arrives():
    add_rule(start_date="2026-01-01")
    assert store.apply_recurring(pd.Timestamp("2026-01-14")) == 0
    assert store.apply_recurring(pd.Timestamp("2026-01-15")) == 1


def test_day_31_uses_last_day_of_short_months():
    add_rule(day=31, start_date="2026-01-01")
    store.apply_recurring(pd.Timestamp("2026-03-31"))
    assert deposits()["date"].dt.strftime("%m-%d").tolist() == ["01-31", "02-28", "03-31"]


def test_end_date_stops_deposits():
    add_rule(start_date="2026-01-01", end_date="2026-02-20")
    assert store.apply_recurring(pd.Timestamp("2026-06-01")) == 2


def test_deleting_a_logged_deposit_does_not_bring_it_back():
    add_rule(start_date="2026-01-01")
    store.apply_recurring(pd.Timestamp("2026-02-20"))
    ledger = store.load()
    store.save_transactions(ledger.transactions.iloc[1:])
    assert store.apply_recurring(pd.Timestamp("2026-02-25")) == 0


def test_removing_account_removes_its_rules():
    add_rule()
    store.remove_account(store.load(), "A")
    assert store.load_recurring().empty


def test_starting_point_makes_put_in_equal_current_value():
    import metrics

    store.add_transaction(store.load(), date=pd.Timestamp("2026-01-05"), account="A", type="deposit", amount=100.0, note="")
    store.add_valuations(store.load(), [{"date": pd.Timestamp("2026-06-01"), "account": "A", "value": 900.0}])
    today = pd.Timestamp("2026-06-01")
    gaps = store.start_from_current_value(store.load(), ["A"], today)
    assert gaps == {"A": 800.0}
    ledger = store.load()
    mine = ledger.transactions[ledger.transactions["account"] == "A"]
    assert metrics.net_contributions(mine, None, today) == 900.0
    assert metrics.period_result(ledger.valuations, ledger.transactions, None, today).earned == 0
    assert store.start_from_current_value(ledger, ["A"], today) == {}  # nothing left to correct
