import pandas as pd
import streamlit as st

import metrics as m
import prices
import store

ledger = store.load()
settings = ledger.settings
today = pd.Timestamp.today().normalize()

st.title("Settings")

# --- Your numbers -----------------------------------------------------------

st.subheader("Your numbers")
st.caption("Used to compare your money's earnings with your pay and your bills.")
with st.form("numbers"):
    cols = st.columns(3)
    currency = cols[0].text_input("Currency symbol", settings["currency"], max_chars=4)
    take_home = cols[1].number_input(
        "Monthly take-home pay", min_value=0.0, value=float(settings["monthly_take_home"]), step=1000.0, format="%.0f"
    )
    expenses = cols[2].number_input(
        "Monthly living expenses", min_value=0.0, value=float(settings["monthly_expenses"]), step=1000.0, format="%.0f"
    )
    hours = cols[0].number_input(
        "Work hours per week", min_value=1.0, max_value=100.0, value=float(settings["work_hours_per_week"]), step=1.0, format="%.0f"
    )
    swr = cols[1].number_input(
        "Safe withdrawal rate (%)",
        min_value=0.5,
        max_value=10.0,
        value=float(settings["safe_withdrawal_rate_pct"]),
        step=0.25,
        help="How much of your portfolio you could spend each year without running out. "
        "4% is the common rule of thumb; lower is more cautious.",
    )
    if st.form_submit_button("Save", type="primary"):
        store.save_settings(
            {
                **settings,
                "currency": currency.strip() or "₱",
                "monthly_take_home": take_home,
                "monthly_expenses": expenses,
                "work_hours_per_week": hours,
                "safe_withdrawal_rate_pct": swr,
            }
        )
        st.session_state["flash"] = "Settings saved."
        st.rerun()

# --- Accounts ---------------------------------------------------------------

st.subheader("Accounts")
st.caption(
    "**Your estimate** is your own assumption. Accounts with live holdings can instead use "
    "their holdings' **past performance**: tick the box, and the **Used %/yr** column "
    "shows the rate the whole app actually uses. Crypto defaults to your estimate, since "
    "its history is too extreme to plan on."
)
if ledger.accounts.empty:
    st.info("No accounts yet. Add your first one below.")
else:
    shown = ledger.accounts.copy()
    shown["use_past_performance"] = [ledger.uses_past_performance(a) for a in shown["account"]]
    shown["used"] = [ledger.expected_rates[a] * 100 for a in shown["account"]]
    edited = st.data_editor(
        shown,
        hide_index=True,
        disabled=["account", "used"],
        column_order=["account", "type", "platform", "expected_return_pct", "use_past_performance", "used", "notes"],
        key="accounts",
        column_config={
            "account": "Account",
            "type": st.column_config.SelectboxColumn("Type", options=list(store.ACCOUNT_TYPES), required=True),
            "platform": "Platform",
            "expected_return_pct": st.column_config.NumberColumn(
                "Your estimate %/yr", min_value=-50.0, max_value=100.0, step=0.1, format="%.2f", required=True
            ),
            "use_past_performance": st.column_config.CheckboxColumn(
                "Use past performance",
                help="Take this account's rate from its live holdings' history. Needs holdings with at least a year of prices.",
            ),
            "used": st.column_config.NumberColumn(
                "Used %/yr", format="%.2f", help="The rate the earning-rate page and projections really use."
            ),
            "notes": "Notes",
        },
    )
    if st.button("Save accounts"):
        store.save_accounts(edited.drop(columns=["used"]))
        st.session_state["flash"] = "Accounts saved."
        st.rerun()

with st.expander("Add an account", icon=":material/add:", expanded=ledger.accounts.empty):
    cols = st.columns(2)
    name = cols[0].text_input("Name", placeholder="e.g. MP2, US ETFs, Emergency fund")
    kind = cols[1].selectbox("Type", list(store.ACCOUNT_TYPES))
    platform = cols[0].text_input("Platform", placeholder="Bank, broker or app")
    rate = cols[1].number_input(
        "Expected return %/yr",
        value=store.ACCOUNT_TYPES[kind],
        step=0.25,
        key=f"rate-{kind}",
        help="A starting assumption for this type. Use your actual rate if you know it, "
        "net of tax (e.g. time deposits after 20% withholding).",
    )
    opening = cols[0].number_input(
        "What it's worth today",
        min_value=0.0,
        step=1000.0,
        format="%.0f",
        help="Recorded as a deposit today, so earnings are counted from here on. To "
        "count past growth, log your past deposits in Check-in instead.",
    )
    if st.button("Add account", type="primary"):
        name = name.strip()
        if not name:
            st.error("Give the account a name.")
        elif name in ledger.account_names:
            st.error(f"You already have an account called {name}.")
        else:
            row = {"account": name, "type": kind, "platform": platform.strip(), "expected_return_pct": rate, "notes": ""}
            store.save_accounts(pd.concat([ledger.accounts, pd.DataFrame([row])]))
            if opening > 0:
                ledger = store.load()
                store.add_transaction(
                    ledger, date=today, account=name, type="deposit", amount=opening, note="Opening balance"
                )
                store.add_valuations(ledger, [{"date": today, "account": name, "value": opening}])
            st.session_state["flash"] = f"Added {name}."
            st.rerun()

if ledger.account_names:
    with st.expander("Remove an account", icon=":material/delete:"):
        doomed = st.selectbox("Account", ledger.account_names, key="remove-account")
        confirmed = st.checkbox(f"Also delete all of {doomed}'s transactions and values")
        if st.button("Remove", disabled=not confirmed):
            store.remove_account(ledger, doomed)
            st.session_state["flash"] = f"Removed {doomed}."
            st.rerun()

# --- Holdings ---------------------------------------------------------------

st.subheader("Live holdings")
st.caption(
    "List the stocks, ETFs or coins in an account with how many you own, using Yahoo "
    "tickers (VOO, SWRD.L, BTC-USD). The hub values that account from live prices and, for "
    "stocks and ETFs, uses their past performance as the expected return. **Check the "
    "name beside each ticker**: Yahoo reuses short tickers, so `SWRD` is a different "
    "company from `SWRD.L`. Only ticker symbols are sent out."
)
if ledger.account_names:
    held = prices.load_holdings()
    cache = prices.load_cache()
    if not held.empty:
        view = prices.holding_table(held, cache)
        st.dataframe(
            view[["account", "ticker", "name", "shares", "currency", "price", "value", "r1y", "cagr"]],
            hide_index=True,
            column_config={
                "account": "Account",
                "ticker": "Ticker",
                "name": "Name on Yahoo",
                "shares": st.column_config.NumberColumn("Shares / coins", format="%.8g"),
                "currency": "Quoted in",
                "price": st.column_config.NumberColumn("Price", format="%.2f"),
                "value": st.column_config.NumberColumn("Value (PHP)", format="localized"),
                "r1y": st.column_config.NumberColumn("Last 12 months", format="%.1f%%"),
                "cagr": st.column_config.NumberColumn(
                    "Per year, up to 10y", format="%.1f%%", help="Annualized total return, dividends included."
                ),
            },
        )
        for account, reasons in prices.missing_history(held, cache).items():
            if ledger.uses_past_performance(account):
                st.caption(f"**{account}**: {', '.join(reasons)}. Those count at your own estimate.")
        for account, info in ledger.past_performance.items():
            st.caption(
                f"**{account}** expects **{info['rate'] * 100:.1f}%/yr** from its holdings' past "
                f"performance (shortest history {info['years']:.1f} years). Past performance is not "
                "a promise of future returns, so treat this as optimistic."
            )

    with st.form("add-holding", clear_on_submit=True):
        cols = st.columns(4)
        h_account = cols[0].selectbox("Account", ledger.account_names)
        h_ticker = cols[1].text_input(
            "Ticker",
            placeholder="VOO or BTC-USD",
            help="Yahoo tickers. London listings end in .L, crypto looks like BTC-USD.",
        ).strip().upper()
        h_shares = cols[2].number_input(
            "Shares or coins", min_value=0.0, step=0.01, format="%.8f", help="Fractions are fine, for example 0.015 BTC."
        )
        h_currency = cols[3].selectbox(
            "Price currency",
            ["USD", "PHP", "EUR", "GBP", "SGD", "HKD"],
            help="Only a fallback. The hub uses the currency Yahoo reports for the ticker.",
        )
        add_holding = st.form_submit_button("Add holding", type="primary")
    if add_holding:
        if not h_ticker or h_shares <= 0:
            st.error("Enter a ticker and a share count above zero.")
        elif (found := prices.lookup(h_ticker)) is None:
            st.error(f"Couldn't find a price for {h_ticker}. Check the Yahoo ticker and your connection.")
        else:
            others = held[~((held["account"] == h_account) & (held["ticker"] == h_ticker))]
            new = pd.DataFrame([{"account": h_account, "ticker": h_ticker, "shares": h_shares, "currency": h_currency}])
            prices.save_holdings(pd.concat([others, new]) if not others.empty else new)
            result = prices.refresh(store.load(), force=True)
            st.session_state["flash"] = (
                f"Added {h_shares:g} × {h_ticker} ({found['name'] or 'name unavailable'}) at "
                f"{found['price']:,.2f} {found['currency']}. {h_account} is now valued from live prices. "
                "If that isn't the instrument you meant, remove it and try another ticker."
                + (f" Couldn't price: {', '.join(result.failed)}." if result.failed else "")
            )
            st.rerun()

    if not held.empty:
        with st.expander("Remove a holding", icon=":material/delete:"):
            labels = [f"{r.account} · {r.ticker}" for r in held.itertuples()]
            pick = st.selectbox("Holding", labels, key="remove-holding")
            if st.button("Remove holding"):
                prices.save_holdings(held.drop(index=labels.index(pick)))
                st.session_state["flash"] = f"Removed {pick}."
                st.rerun()

    with st.expander("Fix what you've put in", icon=":material/tune:"):
        st.caption(
            "**Earned** is value minus what you put in. If an account's put-in doesn't match "
            "what you actually paid (for example you added holdings after creating the account), "
            "earned looks far too high or too low. Enter the real total and the hub adds a "
            "correcting entry, which you can see in Check-in → Edit history."
        )
        fix_account = st.selectbox("Account", ledger.account_names, key="fix-account")
        mine = ledger.transactions[ledger.transactions["account"] == fix_account]
        put_in_now = m.net_contributions(mine, None, today)
        worth_now = float(m.account_values(ledger.valuations, ledger.transactions, today, [fix_account]).iloc[0])
        cols = st.columns(2)
        cols[0].metric("Currently counted as put in", f"{ledger.settings['currency']}{put_in_now:,.0f}")
        cols[1].metric("Currently worth", f"{ledger.settings['currency']}{worth_now:,.0f}")
        target_put_in = st.number_input(
            "What you've really put in, in total", min_value=0.0, value=max(0.0, put_in_now), step=1000.0, format="%.0f"
        )
        first_tx = mine["date"].min() if not mine.empty else today
        since = st.date_input(
            "Roughly since when",
            first_tx.date(),
            max_value=today.date(),
            help="Used for the annual return: an earlier date means the same gain was earned more slowly.",
        )
        gap = target_put_in - put_in_now
        if st.button("Treat current values as my starting point", help="Sets put-in equal to current value for this account, so earnings count from today."):
            store.start_from_current_value(ledger, [fix_account], today)
            st.session_state["flash"] = f"{fix_account}: earnings now count from today."
            st.rerun()
        if st.button("Correct it", disabled=abs(gap) < 0.5):
            store.add_transaction(
                ledger,
                date=pd.Timestamp(since),
                account=fix_account,
                type="deposit" if gap > 0 else "withdrawal",
                amount=abs(gap),
                note="Correction to what was put in",
            )
            st.session_state["flash"] = f"{fix_account}: put-in is now {ledger.settings['currency']}{target_put_in:,.0f}."
            st.rerun()

# --- Recurring investments -------------------------------------------------

st.subheader("Recurring investments")
st.caption(
    "Set it once. Each time the app opens it logs a deposit for every date that has "
    "passed, so your numbers stay current. Months shorter than the day you pick use the last day."
)
names = ledger.account_names
if not names:
    st.info("Add an account first.")
else:
    recurring = store.load_recurring()
    rec_edited = st.data_editor(
        recurring[["account", "amount", "day", "start_date", "end_date"]],
        num_rows="dynamic",
        hide_index=True,
        key="recurring",
        column_config={
            "account": st.column_config.SelectboxColumn("Account", options=names, required=True),
            "amount": st.column_config.NumberColumn("Amount", min_value=1, format="localized", required=True),
            "day": st.column_config.NumberColumn("Day of month", min_value=1, max_value=31, step=1, format="%d", required=True),
            "start_date": st.column_config.DateColumn("Starts", required=True, default=today.date()),
            "end_date": st.column_config.DateColumn("Ends (optional)"),
        },
    )
    if st.button("Save recurring"):
        saved = rec_edited.dropna(subset=["account", "amount", "day", "start_date"]).copy()
        saved["last_applied"] = recurring["last_applied"].reindex(saved.index)
        store.save_recurring(saved)
        added = store.apply_recurring(today)
        st.session_state["flash"] = (
            "Recurring investments saved."
            + (f" Logged {added} deposit{'s' * (added != 1)} that were already due." if added else "")
        )
        st.rerun()

# --- Bills ------------------------------------------------------------------

st.subheader("Bills your money should pay")
st.caption(
    "The earning rate page shows which of these your money's earnings already cover "
    "and how much more you'd need to invest to cover the rest."
)
bills = pd.DataFrame(settings["milestones"], columns=["name", "monthly_cost"])
bills_edited = st.data_editor(
    bills,
    num_rows="dynamic",
    hide_index=True,
    key="bills",
    column_config={
        "name": st.column_config.TextColumn("Bill", required=True),
        "monthly_cost": st.column_config.NumberColumn("Per month", min_value=0, format="localized", required=True),
    },
)
if st.button("Save bills"):
    rows = bills_edited.dropna().to_dict("records")
    store.save_settings({**settings, "milestones": [{"name": r["name"], "monthly_cost": float(r["monthly_cost"])} for r in rows]})
    st.session_state["flash"] = "Bills saved."
    st.rerun()

# --- Data -------------------------------------------------------------------

st.subheader("Your data")
in_repo_data = store.DATA_DIR.resolve().is_relative_to(store.REPO_ROOT / "data")
st.markdown(
    f"Everything is stored as CSV files in `{store.DATA_DIR}`"
    + (", which git ignores. " if in_repo_data else ". ")
    + "You can open the files in Excel. Back the folder up somewhere safe."
)
with st.expander("Start over", icon=":material/restart_alt:"):
    sure = st.checkbox("I understand this replaces all my current data")
    cols = st.columns(2)
    if cols[0].button("Load the sample portfolio", disabled=not sure):
        store.load_sample()
        st.rerun()
    if cols[1].button("Erase everything", disabled=not sure):
        store.start_empty()
        st.rerun()
