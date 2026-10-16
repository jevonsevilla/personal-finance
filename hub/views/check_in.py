import pandas as pd
import streamlit as st

import metrics as m
import store
import ui

TYPE_HELP = {
    "deposit": "money you put in",
    "withdrawal": "money you took out",
    "dividend": "earnings paid into the account",
    "interest": "earnings paid into the account",
}

ledger = store.load()
money = ui.Money(ledger.settings["currency"])
today = pd.Timestamp.today().normalize()
names = ledger.account_names

st.title("Check-in")

if not names:
    st.info("Add an account in **Settings** first.")
    st.page_link("views/settings.py", label="Add an account", icon=":material/add:")
    st.stop()

values_tab, log_tab, history_tab = st.tabs(["Update values", "Log a transaction", "Edit history"])

with values_tab:
    st.caption(
        "Once a month, open each app or statement and type in what each account is "
        "worth. Leave a row blank to skip it."
    )
    on = pd.Timestamp(st.date_input("Values as of", today, max_value=today))
    estimates = m.account_values(ledger.valuations, ledger.transactions, on, names)
    last_valued = ledger.valuations.groupby("account")["date"].max().reindex(names)
    table = pd.DataFrame(
        {
            "account": names,
            "estimate": estimates.to_numpy(),
            "last_valued": last_valued.to_numpy(),
            "value": pd.Series([float("nan")] * len(names), dtype=float),
        }
    )
    edited = st.data_editor(
        table,
        key=f"check-in-{on.date()}",
        hide_index=True,
        placeholder="",
        disabled=["account", "estimate", "last_valued"],
        column_config={
            "account": "Account",
            "estimate": st.column_config.NumberColumn(
                "Expected now",
                format="localized",
                help="Last value plus deposits, withdrawals and income logged since.",
            ),
            "last_valued": st.column_config.DateColumn("Last valued", format="MMM D, YYYY"),
            "value": st.column_config.NumberColumn(
                "Value today", min_value=0, format="localized", required=False
            ),
        },
    )
    if st.button("Save values", type="primary"):
        filled = edited.dropna(subset=["value"])
        if filled.empty:
            st.warning("Type a value for at least one account.")
        else:
            store.add_valuations(
                ledger,
                [{"date": on, "account": r.account, "value": r.value} for r in filled.itertuples()],
            )
            earned = float((filled["value"] - filled["estimate"]).sum())
            st.session_state["flash"] = (
                f"Saved {len(filled)} value{'s' * (len(filled) != 1)}. Since their last "
                f"check-in those accounts earned **{money(earned, signed=True)}**."
            )
            st.rerun()

with log_tab:
    with st.form("transaction", clear_on_submit=True):
        cols = st.columns(2)
        when = cols[0].date_input("Date", today, max_value=today)
        account = cols[1].selectbox("Account", names)
        kind = cols[0].selectbox(
            "Type",
            m.TRANSACTION_TYPES,
            format_func=lambda t: f"{t.capitalize()} ({TYPE_HELP[t]})",
        )
        amount = cols[1].number_input("Amount", min_value=0.0, step=1000.0, format="%.2f")
        note = st.text_input("Note", placeholder="Optional")
        submitted = st.form_submit_button("Add transaction", type="primary")

    if submitted:
        if amount <= 0:
            st.error("Enter an amount above zero.")
        else:
            store.add_transaction(
                ledger, date=pd.Timestamp(when), account=account, type=kind, amount=amount, note=note
            )
            if kind == "deposit":
                boost = amount * ledger.expected_rates.get(account, 0) / 12
                message = (
                    f"Deposit logged. That adds about **{money(boost, 2)}/month** "
                    "to your earning power."
                )
            elif kind in m.INCOME_TYPES:
                message = f"Logged **{money(amount, 2)}** your money paid you."
            else:
                message = "Withdrawal logged."
            st.session_state["flash"] = message
            st.rerun()

with history_tab:
    st.caption("Fix typos or delete rows here. Changes are saved only when you click Save.")
    tx_edited = st.data_editor(
        ledger.transactions.iloc[::-1],
        num_rows="dynamic",
        hide_index=True,
        key="tx-history",
        placeholder="",
        column_config={
            "date": st.column_config.DateColumn("Date", required=True),
            "account": st.column_config.SelectboxColumn("Account", options=names, required=True),
            "type": st.column_config.SelectboxColumn("Type", options=m.TRANSACTION_TYPES, required=True),
            "amount": st.column_config.NumberColumn("Amount", min_value=0, format="localized", required=True),
            "note": "Note",
        },
    )
    if st.button("Save transactions"):
        store.save_transactions(tx_edited.dropna(subset=["date", "account", "type", "amount"]))
        st.session_state["flash"] = "Transactions saved."
        st.rerun()

    val_edited = st.data_editor(
        ledger.valuations.iloc[::-1],
        num_rows="dynamic",
        hide_index=True,
        key="val-history",
        column_config={
            "date": st.column_config.DateColumn("Date", required=True),
            "account": st.column_config.SelectboxColumn("Account", options=names, required=True),
            "value": st.column_config.NumberColumn("Value", min_value=0, format="localized", required=True),
        },
    )
    if st.button("Save values history"):
        store.save_valuations(val_edited.dropna(subset=["date", "account", "value"]))
        st.session_state["flash"] = "Values saved."
        st.rerun()
