import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import metrics as m
import prices
import store
import ui

STALE_AFTER_DAYS = 45

ledger = store.load()
money = ui.Money(ledger.settings["currency"])
c = ui.colors()
today = pd.Timestamp.today().normalize()
vals, tx = ledger.valuations, ledger.transactions

st.title("Portfolio")

if vals.empty and tx.empty:
    st.info("Nothing to show yet. Log a deposit or a value in **Check-in** first.")
    st.stop()

lifetime = m.period_result(vals, tx, None, today)
lifetime_rate = m.annualized_return(vals, tx, None, today)

cols = st.columns(4)
cols[0].metric("Total value", money(lifetime.end_value), border=True)
cols[1].metric("You put in", money(lifetime.net_contributed), help="Deposits minus withdrawals.", border=True)
cols[2].metric(
    "Your money earned",
    money(lifetime.earned),
    delta=ui.pct(lifetime.earned / lifetime.net_contributed) if lifetime.net_contributed > 0 else None,
    border=True,
)
cols[3].metric(
    "Annual return",
    ui.pct(lifetime_rate),
    help="Money-weighted (XIRR) since your first transaction, so the timing of "
    "your deposits is taken into account.",
    border=True,
)

# --- Value vs what you put in ----------------------------------------------

breakdown = m.monthly_breakdown(vals, tx, today)
contributed = breakdown["contributed"].cumsum()

if len(breakdown) < 2:
    st.info("The value-over-time chart appears once you have more than one month of history.")
else:
    st.markdown("**Value vs what you put in**")
    st.caption("The gap between the lines is what your money earned for you")
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=breakdown.index,
            y=breakdown["value"],
            name="Value",
            mode="lines",
            line=dict(color=c["accent"], width=2),
            fill="tozeroy",
            fillcolor=ui.wash(c["accent"]),
            hovertemplate=f"{money.symbol}%{{y:,.0f}}",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=contributed.index,
            y=contributed.values,
            name="You put in",
            mode="lines",
            line=dict(color=c["context"], width=2),
            hovertemplate=f"{money.symbol}%{{y:,.0f}}",
        )
    )
    ui.end_label(fig, breakdown.index[-1], breakdown["value"].iloc[-1], money.compact(breakdown["value"].iloc[-1]), c["accent"])
    ui.show_chart(ui.style_chart(fig, money, height=340))

# --- Accounts ---------------------------------------------------------------

summary = m.account_summary(ledger.account_names, vals, tx, today)
accounts = ledger.accounts.set_index("account")
summary["type"] = accounts["type"]
summary["platform"] = accounts["platform"]
summary["expected_pct"] = ledger.expected_rates * 100
summary["basis"] = [
    "Past performance" if name in ledger.past_performance else "Your estimate" for name in summary.index
]
summary["earns_per_month"] = summary["value"] * ledger.expected_rates / 12
summary["share"] = summary["value"] / summary["value"].sum() * 100
summary["actual_pct"] = summary["annualized_return"] * 100
summary = summary.sort_values("value", ascending=False)

st.subheader("Accounts")
whole = ["value", "net_contributed", "earned", "earns_per_month"]
st.dataframe(
    summary.assign(**{col: summary[col].round() for col in whole}).reset_index(),
    hide_index=True,
    column_order=[
        "account", "type", "platform", "value", "share", "net_contributed", "earned",
        "actual_pct", "expected_pct", "basis", "earns_per_month", "last_valued",
    ],
    column_config={
        "account": st.column_config.TextColumn("Account"),
        "type": "Type",
        "platform": "Platform",
        "value": st.column_config.NumberColumn("Value", format="localized"),
        "share": st.column_config.ProgressColumn(
            "Share", format="%.0f%%", min_value=0, max_value=100, width="small"
        ),
        "net_contributed": st.column_config.NumberColumn("You put in", format="localized"),
        "earned": st.column_config.NumberColumn("Earned", format="localized"),
        "actual_pct": st.column_config.NumberColumn(
            "Actual %/yr", format="%.1f%%", help="Money-weighted return since the account's first transaction."
        ),
        "expected_pct": st.column_config.NumberColumn("Expected %/yr", format="%.1f%%"),
        "basis": st.column_config.TextColumn(
            "Expected based on",
            help="Accounts with live holdings use their holdings' annualized return over up to 10 years.",
        ),
        "earns_per_month": st.column_config.NumberColumn(
            "Earns /mo", format="localized", help="Value × expected rate ÷ 12."
        ),
        "last_valued": st.column_config.DateColumn("Last valued", format="MMM D, YYYY"),
    },
)

held = prices.load_holdings()
backed = set(held["account"])
off = [
    a for a in summary.index
    if a in backed and summary.loc[a, "value"] > 0 and summary.loc[a, "net_contributed"] < 0.25 * summary.loc[a, "value"]
]
if off:
    st.warning(
        f"**Earned looks too high for {', '.join(off)}.** What you've put in is far below what the holdings are "
        "worth, usually because the account was created before its holdings. Set the real total in "
        "**Settings → Live holdings → Fix what you've put in**, or start counting from today.",
        icon=":material/error:",
    )
    if st.button("Treat current values as my starting point"):
        store.start_from_current_value(ledger, off, today)
        st.rerun()

stale = summary[(today - summary["last_valued"]).dt.days > STALE_AFTER_DAYS].index.tolist()
never = summary[summary["last_valued"].isna() & (summary["value"] > 0)].index.tolist()
if stale or never:
    st.caption(
        "Update these in **Check-in** to keep your numbers honest: "
        + ", ".join(stale + never)
    )

# --- Holdings ---------------------------------------------------------------

held = prices.load_holdings()
if not held.empty:
    st.subheader("Holdings")
    st.caption(
        "Market performance of each holding (dividends included), not your own gain: "
        "the hub doesn't know the price you paid."
    )
    cache = prices.load_cache()
    table = prices.holding_table(held, cache)
    table["share"] = table["value"] / table["value"].sum() * 100
    table["value"] = table["value"].round()
    st.dataframe(
        table.sort_values("value", ascending=False),
        hide_index=True,
        column_order=["ticker", "name", "account", "value", "share", "r1y", "cagr", "years"],
        column_config={
            "ticker": "Ticker",
            "name": "Name",
            "account": "Account",
            "value": st.column_config.NumberColumn("Value", format="localized"),
            "share": st.column_config.ProgressColumn("Share", format="%.0f%%", min_value=0, max_value=100, width="small"),
            "r1y": st.column_config.NumberColumn("Last 12 months", format="%.1f%%"),
            "cagr": st.column_config.NumberColumn(
                "Per year", format="%.1f%%", help="Annualized total return over the history shown."
            ),
            "years": st.column_config.NumberColumn("History (yrs)", format="%.1f"),
        },
    )
    short = table[table["years"].notna() & (table["years"] < prices.MIN_FORECAST_YEARS) & ~table["ticker"].map(prices.is_crypto)]
    if not short.empty:
        st.caption(
            f"Under {prices.MIN_FORECAST_YEARS} years of history, so they count at your own estimate, not their past performance: "
            + ", ".join(f"{t} ({n or 'unknown'})" for t, n in zip(short["ticker"], short["name"]))
            + ". A short stretch of history can flatter a fund, which is why it isn't used."
        )

# --- Allocation -------------------------------------------------------------


def allocation_chart(totals: pd.Series) -> None:
    totals = totals[totals > 0].sort_values()
    shares = totals / totals.sum()
    fig = go.Figure(
        go.Bar(
            x=totals.values,
            y=totals.index,
            orientation="h",
            marker=dict(color=c["accent"], cornerradius=4),
            text=[f"{s:.0%} · {money.compact(v)}" for s, v in zip(shares, totals)],
            textposition="outside",
            cliponaxis=False,
            hovertemplate=f"%{{y}}: {money.symbol}%{{x:,.0f}}<extra></extra>",
        )
    )
    ui.style_chart(fig, money, height=30 + 40 * len(totals))
    fig.update_layout(showlegend=False, hovermode="closest", bargap=0.55, margin=dict(r=110))
    fig.update_xaxes(showgrid=False, showticklabels=False, zeroline=False)
    fig.update_yaxes(showgrid=False, tickprefix="", zeroline=False)
    ui.show_chart(fig)


st.subheader("Where your money is")
st.caption("Spreading money across types and institutions limits the damage if one has a bad year.")
left, right = st.columns(2)
with left:
    st.markdown("**By type**")
    allocation_chart(summary.groupby("type")["value"].sum())
with right:
    st.markdown("**By platform**")
    allocation_chart(summary.assign(platform=summary["platform"].replace("", "Unspecified")).groupby("platform")["value"].sum())
