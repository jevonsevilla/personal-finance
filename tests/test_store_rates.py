import pandas as pd
import pytest

import prices
import store


@pytest.fixture(autouse=True)
def data_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "DATA_DIR", tmp_path)
    store.start_empty()


def accounts(*rows):
    cols = ["account", "type", "platform", "expected_return_pct", "use_past_performance", "notes"]
    store.save_accounts(pd.DataFrame(rows, columns=cols))


def cache_with(ticker, cagr, price=100.0):
    prices._cache_path().write_text(
        __import__("json").dumps(
            {"fetched_at": 0, "quotes": {ticker: price}, "history": {ticker: {"cagr": cagr, "years": 10, "at": 0}}}
        )
    )


def holding(account, ticker):
    prices.save_holdings(pd.DataFrame([{"account": account, "ticker": ticker, "shares": 1, "currency": "PHP"}]))


def test_stock_account_uses_past_performance_by_default():
    accounts(("S", "Stocks", "", 8.0, None, ""))
    holding("S", "AAA"); cache_with("AAA", 0.15)
    ledger = store.load()
    assert ledger.expected_rates["S"] == pytest.approx(0.15)


def test_account_can_opt_out_to_its_own_estimate():
    accounts(("S", "Stocks", "", 8.0, False, ""))
    holding("S", "AAA"); cache_with("AAA", 0.15)
    ledger = store.load()
    assert ledger.expected_rates["S"] == pytest.approx(0.08)
    assert "S" not in ledger.past_performance


def test_crypto_always_uses_your_own_estimate():
    accounts(("C", "Crypto", "Binance", 10.0, None, ""))
    holding("C", "BTC-USD"); cache_with("BTC-USD", 1.2)
    ledger = store.load()
    assert ledger.expected_rates["C"] == pytest.approx(0.10)
    assert "C" not in ledger.past_performance
    accounts(("C", "Crypto", "Binance", 10.0, True, ""))  # even if you tick the box
    assert store.load().expected_rates["C"] == pytest.approx(0.10)


def test_crypto_in_a_stock_account_counts_at_your_estimate_not_its_history():
    accounts(("S", "ETF / Index fund", "IBKR", 6.0, None, ""))
    prices.save_holdings(pd.DataFrame([
        {"account": "S", "ticker": "AAA", "shares": 1, "currency": "PHP"},
        {"account": "S", "ticker": "BTC-USD", "shares": 1, "currency": "PHP"},
    ]))
    prices._cache_path().write_text(__import__("json").dumps({
        "fetched_at": 0,
        "quotes": {"AAA": 300.0, "BTC-USD": 100.0},
        "history": {"AAA": {"cagr": 0.12, "years": 10, "at": 0}, "BTC-USD": {"cagr": 1.2, "years": 10, "at": 0}},
    }))
    # (300 * 12% + 100 * 6%) / 400 = 10.5%, not dragged up by Bitcoin's 120%
    assert store.load().expected_rates["S"] == pytest.approx(0.105)


def test_explains_why_history_is_missing():
    holding("S", "NEW")
    cache = {"fetched_at": 0, "quotes": {"NEW": 5.0}, "history": {"NEW": {"cagr": None, "years": 0.3, "at": 0}}}
    assert prices.missing_history(prices.load_holdings(), cache) == {"S": ["NEW has only 0.3 years of history"]}
