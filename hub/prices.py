"""Live prices for holdings, fetched from Yahoo Finance via yfinance.

Only ticker symbols leave your machine; share counts and amounts stay local.
Quotes are cached in ``prices.json`` so a failed fetch falls back to the last known price.
"""

import json
import re
import time
from dataclasses import dataclass, field

import pandas as pd

import store

REFRESH_SECONDS = 60
# Yahoo lists coins as BTC-USD, ETH-EUR, ...; their history is far too extreme to plan on.
CRYPTO_TICKER = re.compile(r"^[A-Z0-9]{2,10}-(USD|USDT|EUR|GBP|PHP|SGD)$")
HISTORY_REFRESH_SECONDS = 24 * 3600
HISTORY_PERIOD = "10y"
MIN_HISTORY_DAYS = 365
# A few good years can flatter a fund, so its own record only sets the expected return past this.
MIN_FORECAST_YEARS = 5
HOLDING_COLUMNS = ["account", "ticker", "shares", "currency"]
# Yahoo quotes some markets in minor units (pence, cents): price / 100 in the major currency.
MINOR_UNITS = {"GBp": "GBP", "GBX": "GBP", "ZAc": "ZAR", "ILA": "ILS"}


def _cache_path():
    return store.DATA_DIR / "prices.json"


def load_cache() -> dict:
    path = _cache_path()
    cache = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    return {"fetched_at": 0, "quotes": {}, "currencies": {}, "names": {}, "history": {}, **cache}


def _fx_symbol(currency: str, home: str) -> str:
    return f"{currency}{home}=X"


def is_crypto(ticker: str) -> bool:
    return bool(CRYPTO_TICKER.match(ticker))


def _quote(symbol: str) -> tuple[float, str | None] | None:
    """(price, currency) in major currency units, or None if Yahoo has nothing."""
    import yfinance as yf

    try:
        info = yf.Ticker(symbol).fast_info
        price, currency = info["last_price"], info["currency"]
    except Exception:
        return None
    if not price or price <= 0:
        return None
    if currency in MINOR_UNITS:
        price, currency = price / 100, MINOR_UNITS[currency]
    return float(price), currency


def fetch_quotes(symbols: list[str]) -> tuple[dict[str, float], dict[str, str]]:
    """Latest prices and the currency each one is quoted in. Failures are left out."""
    prices, currencies = {}, {}
    for symbol in symbols:
        if (quote := _quote(symbol)) is not None:
            prices[symbol] = quote[0]
            if quote[1]:
                currencies[symbol] = quote[1]
    return prices, currencies


def fetch_name(symbol: str) -> str | None:
    import yfinance as yf

    try:
        info = yf.Ticker(symbol).info or {}
    except Exception:
        return None
    return info.get("longName") or info.get("shortName")


def lookup(symbol: str) -> dict | None:
    """Price, currency and name for one ticker, so you can check it's the right instrument."""
    if (quote := _quote(symbol)) is None:
        return None
    return {"price": quote[0], "currency": quote[1], "name": fetch_name(symbol)}


def fetch_history(symbol: str) -> dict | None:
    """Total-return stats (dividends reinvested) over the longest span up to 10 years."""
    import yfinance as yf

    try:
        close = yf.Ticker(symbol).history(period=HISTORY_PERIOD, auto_adjust=True)["Close"].dropna()
    except Exception:
        return None
    if len(close) < 2 or close.iloc[0] <= 0:
        return None
    days = (close.index[-1] - close.index[0]).days
    years = days / 365.25
    entry = {"cagr": None, "r1y": None, "years": years, "at": time.time()}
    if days >= MIN_HISTORY_DAYS:
        entry["cagr"] = float((close.iloc[-1] / close.iloc[0]) ** (1 / years) - 1)
        year_ago = close.index.searchsorted(close.index[-1] - pd.Timedelta(days=365))
        entry["r1y"] = float(close.iloc[-1] / close.iloc[year_ago] - 1)
    return entry


def load_holdings() -> pd.DataFrame:
    df = store._read_csv("holdings.csv", HOLDING_COLUMNS)
    df["shares"] = pd.to_numeric(df["shares"])
    df["ticker"] = df["ticker"].str.strip().str.upper()
    df["currency"] = df["currency"].fillna("USD").str.strip().str.upper()
    return df.dropna(subset=["account", "ticker", "shares"])


def save_holdings(df: pd.DataFrame) -> None:
    store.DATA_DIR.mkdir(parents=True, exist_ok=True)
    df.reindex(columns=HOLDING_COLUMNS).to_csv(store.DATA_DIR / "holdings.csv", index=False)


def _currency(row, currencies: dict) -> str:
    """What the price is really quoted in: Yahoo's answer, else what you picked."""
    return currencies.get(row.ticker) or row.currency


def _fx(currency: str, quotes: dict, home: str) -> float | None:
    return 1.0 if currency == home else quotes.get(_fx_symbol(currency, home))


def account_values(
    holdings: pd.DataFrame, quotes: dict, home: str, currencies: dict | None = None
) -> dict[str, float]:
    """Home-currency value per account; accounts missing any price are left out."""
    currencies = currencies or {}
    values, missing = {}, set()
    for row in holdings.itertuples():
        price, fx = quotes.get(row.ticker), _fx(_currency(row, currencies), quotes, home)
        if price is None or fx is None:
            missing.add(row.account)
            continue
        values[row.account] = values.get(row.account, 0.0) + row.shares * price * fx
    return {a: v for a, v in values.items() if a not in missing}


def holding_table(holdings: pd.DataFrame, cache: dict, home: str = "PHP") -> pd.DataFrame:
    """One row per holding with live value and market performance, for display."""
    rows = []
    for row in holdings.itertuples():
        hist = cache["history"].get(row.ticker) or {}
        currency = _currency(row, cache.get("currencies", {}))
        price = cache["quotes"].get(row.ticker)
        fx = _fx(currency, cache["quotes"], home)
        rows.append(
            {
                "account": row.account,
                "ticker": row.ticker,
                "name": cache.get("names", {}).get(row.ticker),
                "shares": row.shares,
                "currency": currency,
                "price": price,
                "value": row.shares * price * fx if price is not None and fx is not None else None,
                "r1y": None if hist.get("r1y") is None else hist["r1y"] * 100,
                "cagr": None if hist.get("cagr") is None else hist["cagr"] * 100,
                "years": hist.get("years"),
            }
        )
    return pd.DataFrame(rows)


def historical_rates(
    holdings: pd.DataFrame,
    cache: dict,
    home: str = "PHP",
    manual: dict | None = None,
) -> dict[str, dict]:
    """Past-performance annual return per account, weighted by what each holding is worth.

    Holdings with under ``MIN_FORECAST_YEARS`` of history, and all crypto, count at the account's own
    estimate (``manual``) instead of dragging the whole account back to it. An account
    where nothing has usable history is left out entirely.
    """
    manual = manual or {}
    currencies = cache.get("currencies", {})
    out = {}
    for account, group in holdings.groupby("account"):
        weights, rates, years, fallback = [], [], [], []
        for row in group.itertuples():
            price = cache["quotes"].get(row.ticker)
            fx = _fx(_currency(row, currencies), cache["quotes"], home)
            if price is None or fx is None:
                weights = None
                break
            weights.append(row.shares * price * fx)
            hist = cache["history"].get(row.ticker) or {}
            if is_crypto(row.ticker) or hist.get("cagr") is None or hist["years"] < MIN_FORECAST_YEARS:
                rates.append(manual.get(account, 0.0))
                fallback.append(row.ticker)
            else:
                rates.append(hist["cagr"])
                years.append(hist["years"])
        if weights is None or not years or sum(weights) <= 0:
            continue
        out[account] = {
            "rate": sum(w * r for w, r in zip(weights, rates)) / sum(weights),
            "years": min(years),
            "fallback": fallback,
        }
    return out


def missing_history(holdings: pd.DataFrame, cache: dict, home: str = "PHP") -> dict[str, list[str]]:
    """Per account, what keeps holdings from using past performance, in plain words."""
    out = {}
    for account, group in holdings.groupby("account"):
        reasons = []
        for row in group.itertuples():
            price = cache["quotes"].get(row.ticker)
            fx = _fx(_currency(row, cache.get("currencies", {})), cache["quotes"], home)
            hist = cache["history"].get(row.ticker)
            if price is None or fx is None:
                reasons.append(f"{row.ticker} has no price yet")
            elif is_crypto(row.ticker):
                continue
            elif hist is None:
                reasons.append(f"{row.ticker} history hasn't loaded yet")
            elif hist.get("cagr") is None or hist["years"] < MIN_FORECAST_YEARS:
                reasons.append(f"{row.ticker} has only {hist['years']:.1f} years of history")
        if reasons:
            out[account] = reasons
    return out


@dataclass
class RefreshResult:
    changed: bool = False
    failed: list[str] = field(default_factory=list)


def refresh(ledger: "store.Ledger", home: str = "PHP", force: bool = False) -> RefreshResult:
    """Update quotes (every minute) and history (daily), then write today's valuations."""
    holdings = load_holdings()
    if holdings.empty:
        return RefreshResult()
    cache = load_cache()
    now = time.time()
    tickers = sorted(set(holdings["ticker"]))
    quotes_stale = force or now - cache["fetched_at"] >= REFRESH_SECONDS
    needs_history = [
        t for t in tickers if force or now - (cache["history"].get(t) or {}).get("at", 0) >= HISTORY_REFRESH_SECONDS
    ]
    needs_names = [t for t in tickers if t not in cache["names"]]
    if not (quotes_stale or needs_history or needs_names):
        return RefreshResult()

    if quotes_stale:
        prices, currencies = fetch_quotes(tickers)
        cache["quotes"].update(prices)
        cache["currencies"].update(currencies)
        # Only now do we know every holding's real currency, and so which FX rates to get.
        wanted = {_currency(r, cache["currencies"]) for r in holdings.itertuples()} - {home}
        fx_prices, _ = fetch_quotes([_fx_symbol(c, home) for c in sorted(wanted)])
        cache["quotes"].update(fx_prices)
        cache["fetched_at"] = now
    for ticker in needs_history:
        if (hist := fetch_history(ticker)) is not None:
            cache["history"][ticker] = hist
    for ticker in needs_names:
        if (name := fetch_name(ticker)) is not None:
            cache["names"][ticker] = name
    store.DATA_DIR.mkdir(parents=True, exist_ok=True)
    _cache_path().write_text(json.dumps(cache), encoding="utf-8")

    failed = sorted(t for t in tickers if t not in cache["quotes"])
    today = pd.Timestamp.today().normalize()
    known = set(ledger.account_names)
    rows = [
        {"date": today, "account": a, "value": round(v, 2)}
        for a, v in account_values(holdings, cache["quotes"], home, cache["currencies"]).items()
        if a in known
    ]
    if rows:
        store.add_valuations(ledger, rows)
    return RefreshResult(changed=bool(rows), failed=failed)
