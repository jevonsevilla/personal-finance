import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import metrics as m
import prices
import store
import ui

PROJECTION_YEARS = 20
EXPECTED, ACTUAL = "Expected rates", "Actual returns"

ledger = store.load()
settings = ledger.settings
money = ui.Money(settings["currency"])
c = ui.colors()
today = pd.Timestamp.today().normalize()
vals, tx = ledger.valuations, ledger.transactions

st.title("Earning rate")

if vals.empty and tx.empty:
    st.info(
        "No investments logged yet. Add your accounts in **Settings**, then log "
        "deposits and values in **Check-in**."
    )
    st.page_link("views/settings.py", label="Add an account", icon=":material/add:")
    st.stop()

if not prices.load_holdings().empty:

    @st.fragment(run_every=prices.REFRESH_SECONDS)
    def live_prices() -> None:
        if prices.refresh(store.load()).changed:
            st.rerun()

    live_prices()

# --- Current position -------------------------------------------------------

values = m.account_values(vals, tx, today, ledger.account_names)
total = float(values.sum())
expected_rate = m.run_rate(values, ledger.expected_rates).per_year / total if total else 0.0

first = m.first_activity(vals, tx)
window_start = m.trailing_window_start(vals, tx, today)
window_label = "last 12 months" if window_start is not None else "since you started"
trailing = m.period_result(vals, tx, window_start, today)
actual_rate = m.annualized_return(vals, tx, window_start, today)

basis = st.segmented_control(
    "Rate basis",
    [EXPECTED, ACTUAL],
    default=EXPECTED,
    label_visibility="collapsed",
    help=(
        "**Expected rates** apply each account's expected return (set in Settings) "
        "to what it's worth today. **Actual returns** apply the annual return your "
        f"portfolio really made over the {window_label}."
    ),
)
if basis == ACTUAL and actual_rate is None:
    st.caption(
        f"Actual returns need {m.MIN_DAYS_FOR_ANNUALIZED} days of history, "
        "so this is showing expected rates for now."
    )
    basis = EXPECTED
basis = basis or EXPECTED
rate = actual_rate if basis == ACTUAL else expected_rate
earning = m.EarningRate(total * rate)

n_accounts = int((values > 0).sum())
ui.earning_hero(
    earning.per_day,
    earning.per_second,
    f"{ui.pct(rate)} a year on {money(total)} across {n_accounts} account"
    f"{'s' * (n_accounts != 1)} · {basis.lower()}",
    money,
)

cols = st.columns(4)
cols[0].metric("Per hour", money(earning.per_hour, 2), border=True)
cols[1].metric("Per week", money(earning.per_day * 7), border=True)
cols[2].metric("Per month", money(earning.per_month), border=True)
cols[3].metric("Per year", money(earning.per_year), border=True)
st.caption(
    "Your money earns around the clock, weekends included. These are averages: "
    "real markets move in jumps, not a smooth line."
)

# --- Reality check ----------------------------------------------------------

st.subheader("Reality check")
lifetime = m.period_result(vals, tx, None, today)
lifetime_rate = m.annualized_return(vals, tx, None, today)

cols = st.columns(3)
cols[0].metric(
    f"Actually earned, {window_label}",
    money(trailing.earned),
    delta=f"{ui.pct(actual_rate)} a year" if actual_rate is not None else None,
    border=True,
    help="How much your accounts grew beyond the money you put in. Includes "
    "gains you haven't sold yet.",
)
months_in_window = max(1.0, (today - (window_start or first)).days / m.DAYS_PER_MONTH)
cols[1].metric(
    f"Cash income, {window_label}",
    money(trailing.income),
    delta=f"{money(trailing.income / months_in_window)}/mo in dividends & interest",
    delta_color="off",
    delta_arrow="off",
    border=True,
    help="Dividends and interest actually paid into your accounts.",
)
cols[2].metric(
    "Earned since you started",
    money(lifetime.earned),
    delta=f"on {money(lifetime.net_contributed)} you put in",
    delta_color="off",
    delta_arrow="off",
    border=True,
)
if actual_rate is not None:
    gap = actual_rate - expected_rate
    verdict = "ahead of" if gap >= 0 else "behind"
    st.caption(
        f"Your expected rates average {ui.pct(expected_rate)} a year. Over the "
        f"{window_label} you actually made {ui.pct(actual_rate)}, which is "
        f"{abs(gap) * 100:.1f} percentage points {verdict} plan."
    )

# --- History ----------------------------------------------------------------

dates = m.period_ends(first, today)
history = m.value_history(vals, tx, dates, ledger.account_names)
if basis == ACTUAL:
    power = history.sum(axis=1) * rate / 12
else:
    power = (history * ledger.expected_rates.reindex(history.columns).fillna(0)).sum(axis=1) / 12

left, right = st.columns(2)
with left:
    st.markdown("**Monthly earning power**")
    st.caption(f"What your portfolio earned per month at each point, at {basis.lower()}")
    fig = go.Figure(
        go.Scatter(
            x=power.index,
            y=power.values,
            mode="lines",
            line=dict(color=c["accent"], width=2),
            fill="tozeroy",
            fillcolor=ui.wash(c["accent"]),
            name="Earning power",
            hovertemplate=f"{money.symbol}%{{y:,.0f}}/mo<extra></extra>",
        )
    )
    ui.end_label(fig, power.index[-1], power.iloc[-1], f"{money(power.iloc[-1])}/mo", c["accent"])
    fig.update_layout(showlegend=False)
    ui.show_chart(ui.style_chart(fig, money, height=300))

breakdown = m.monthly_breakdown(vals, tx, today)
with right:
    st.markdown("**What your money actually earned each month**")
    st.caption("Value change minus deposits, including unrealized gains and losses")
    fig = go.Figure(
        go.Bar(
            x=breakdown.index.to_period("M").to_timestamp(),
            y=breakdown["earned"],
            marker=dict(
                color=[c["accent"] if v >= 0 else c["negative"] for v in breakdown["earned"]],
                cornerradius=4,
            ),
            customdata=breakdown[["income", "growth"]],
            hovertemplate=(
                f"<b>{money.symbol}%{{y:,.0f}}</b> earned<br>"
                f"{money.symbol}%{{customdata[0]:,.0f}} income · "
                f"{money.symbol}%{{customdata[1]:,.0f}} price change<extra></extra>"
            ),
        )
    )
    fig.update_layout(showlegend=False, hovermode="closest")
    ui.show_chart(ui.style_chart(fig, money, height=300))

with st.expander("Monthly numbers"):
    table = breakdown.assign(earning_power=power.to_numpy())
    table.index = table.index.strftime("%b %Y")
    st.dataframe(
        table.iloc[::-1],
        column_config={
            "value": st.column_config.NumberColumn("Value", format="localized"),
            "contributed": st.column_config.NumberColumn("You put in", format="localized"),
            "earned": st.column_config.NumberColumn("Earned", format="localized"),
            "income": st.column_config.NumberColumn("Income", format="localized"),
            "growth": st.column_config.NumberColumn("Price change", format="localized"),
            "earning_power": st.column_config.NumberColumn("Earning power /mo", format="localized"),
        },
    )

# --- Invest more, earn more -------------------------------------------------

st.subheader("Invest more, earn more")
account_rates = ledger.expected_rates.reindex(values.index).fillna(0.0)
if account_rates.max() <= 0:
    st.info("Projections need a positive rate. Set expected returns on your accounts in Settings.")
    st.stop()

# What you already put into each account each month: your recurring rules if you have
# them, otherwise your average over the window (skipping the first month so opening
# balances don't count).
rules = store.load_recurring()
rules = rules[rules["end_date"].isna() | (rules["end_date"] >= today)]
recurring_per_month = rules.groupby("account")["amount"].sum()
pace_start = window_start or (first + pd.Timedelta(days=31))
pace_months = (today - pace_start).days / m.DAYS_PER_MONTH


def usual_monthly(account: str) -> float:
    if account in recurring_per_month.index:
        return float(recurring_per_month[account])
    if pace_months < 1:
        return 0.0
    mine = tx[tx["account"] == account]
    return max(0.0, m.net_contributions(mine, pace_start, today) / pace_months)


def nice(amount: float, step: float = 500) -> float:
    return max(0.0, float(round(amount / step) * step))


with st.expander("What you put into each account per month", expanded=False):
    st.caption(
        "Starts from your recurring investments, or your average over the "
        f"{window_label}. Change any of these to plan ahead."
    )
    contributions = {}
    cols = st.columns(min(3, len(values)))
    for i, account in enumerate(values.index):
        contributions[account] = cols[i % len(cols)].number_input(
            f"{account} ({ui.pct(account_rates[account])}/yr)",
            min_value=0.0,
            value=nice(usual_monthly(account)),
            step=1000.0,
            format="%.0f",
            key=f"contrib-{account}",
        )
monthly = pd.Series(contributions)

best = account_rates.idxmax()
cols = st.columns(2)
target_account = cols[0].selectbox(
    "Add to which account?",
    list(values.index),
    index=list(values.index).index(best),
    format_func=lambda a: f"{a} · {ui.pct(account_rates[a])}/yr",
    help="The extra money earns at this account's rate. Starts on the account with the highest expected return.",
)
extra = cols[1].number_input(
    "What if you added per month",
    min_value=0.0,
    value=max(1000.0, nice(monthly.sum() * 0.25, 1000)),
    step=1000.0,
    format="%.0f",
)

st.markdown(
    f"Every **{money(10_000)}** you put into **{target_account}** earns about "
    f"**{money(10_000 * account_rates[target_account] / 12, 2)} a month**, "
    "every month, for as long as it stays invested."
)

months = PROJECTION_YEARS * 12
boosted_monthly = monthly.copy()
boosted_monthly[target_account] += extra
base_values = m.project_accounts(values, monthly, account_rates, months)
boost_values = m.project_accounts(values, boosted_monthly, account_rates, months)
future = pd.date_range(today, periods=months + 1, freq="ME")[1:]
base = m.earning_power(base_values, account_rates).set_axis(future)
boosted = m.earning_power(boost_values, account_rates).set_axis(future)

cols = st.columns(3)
for col, years in zip(cols, (1, 5, 10)):
    i = years * 12 - 1
    col.metric(
        f"Earning power in {years} year{'s' * (years > 1)}",
        f"{money(boosted.iloc[i])}/mo",
        delta=f"{money(boosted.iloc[i] - base.iloc[i], signed=True)}/mo from the extra {money(extra)}",
        border=True,
    )

fig = go.Figure()
for series, label, color in (
    (boosted, f"Adding {money(extra)}/mo to {target_account}", c["second"]),
    (base, f"Investing as you do now ({money(monthly.sum())}/mo)", c["accent"]),
):
    fig.add_trace(
        go.Scatter(
            x=series.index,
            y=series.values,
            mode="lines",
            name=label,
            line=dict(color=color, width=2),
            hovertemplate=f"{money.symbol}%{{y:,.0f}}/mo",
        )
    )
    ui.end_label(
        fig, series.index[-1], series.iloc[-1], f"{money.compact(series.iloc[-1])}/mo", color, "middle right"
    )
st.markdown("**Projected monthly earning power**")
st.caption(
    "Each account grows at its own expected rate. Contributions land at each month end."
)
ui.show_chart(ui.style_chart(fig, money, height=320).update_layout(margin=dict(r=90)))

# Where would the same extra money do the most?
ten_years = 10 * 12 - 1
gains = {}
for account in values.index:
    plan = monthly.copy()
    plan[account] += extra
    plan_values = m.project_accounts(values, plan, account_rates, ten_years + 1)
    gains[account] = m.earning_power(plan_values, account_rates).iloc[ten_years] - base.iloc[ten_years]
gains = pd.Series(gains).sort_values()
st.markdown(f"**Where {money(extra)} a month helps most**")
st.caption("Added earning power after 10 years, depending on which account the extra goes into.")
fig = go.Figure(
    go.Bar(
        x=gains.values,
        y=gains.index,
        orientation="h",
        marker=dict(
            color=[c["second"] if a == target_account else c["accent"] for a in gains.index],
            cornerradius=4,
        ),
        text=[f"+{money(v)}/mo · {ui.pct(account_rates[a])}/yr" for a, v in gains.items()],
        textposition="outside",
        cliponaxis=False,
        hovertemplate=f"%{{y}}: +{money.symbol}%{{x:,.0f}}/mo<extra></extra>",
    )
)
ui.style_chart(fig, money, height=30 + 40 * len(gains))
fig.update_layout(showlegend=False, hovermode="closest", bargap=0.55, margin=dict(r=170))
fig.update_xaxes(showgrid=False, showticklabels=False, zeroline=False)
fig.update_yaxes(showgrid=False, tickprefix="", zeroline=False)
ui.show_chart(fig)

# --- Freedom and milestones -------------------------------------------------

expenses = float(settings["monthly_expenses"])
swr = float(settings["safe_withdrawal_rate_pct"]) / 100
left, right = st.columns(2)

with left:
    st.subheader("Freedom number")
    if expenses <= 0 or swr <= 0:
        st.info("Add your monthly expenses in **Settings** to see how close you are.")
    else:
        target = expenses * 12 / swr
        st.progress(
            min(1.0, total / target),
            text=f"{ui.pct(total / target)} of {money(target)}",
        )
        st.caption(
            f"The portfolio that could fund {money(expenses)}/month of expenses "
            f"by withdrawing {ui.pct(swr)} a year."
        )
        now_m = m.months_until_accounts(values, monthly, account_rates, target)
        more_m = m.months_until_accounts(values, boosted_monthly, account_rates, target)
        if now_m == 0:
            st.success("You've reached it. Your portfolio could cover your expenses.")
        else:
            st.markdown(
                f"Investing {money(monthly.sum())}/month you get there in **{ui.duration(now_m)}**."
            )
            if now_m is not None and more_m is not None and more_m < now_m:
                st.markdown(
                    f"Adding {money(extra)}/month to {target_account} gets you there in **{ui.duration(more_m)}**, "
                    f"which is **{ui.duration(now_m - more_m)} sooner**."
                )
        st.markdown(
            f"Right now your money's earnings cover **{ui.pct(earning.per_month / expenses, 0)}** "
            "of your monthly expenses."
        )

with right:
    st.subheader("What your money pays for")
    bills = [(b["name"], float(b["monthly_cost"])) for b in settings["milestones"] if b.get("monthly_cost")]
    if expenses > 0:
        bills.append(("All your monthly expenses", expenses))
    if not bills:
        st.info("Add bills like rent or groceries in **Settings** to track which ones your money covers.")
    for name, cost in sorted(bills, key=lambda b: b[1]):
        covered = earning.per_month / cost
        if covered >= 1:
            note = "✓ covered"
        else:
            needed = m.capital_needed(cost, rate) - total
            note = f"{ui.pct(covered, 0)} · invest {money.compact(needed)} more to cover it"
        st.progress(min(1.0, covered), text=f"**{name}** ({money(cost)}/mo) · {note}")

# --- Your money vs your job -------------------------------------------------

take_home = float(settings["monthly_take_home"])
hours = float(settings["work_hours_per_week"])
if take_home > 0 and hours > 0:
    st.subheader("Your money vs your job")
    wage = take_home * 12 / (52 * hours)
    replaced = earning.per_month / wage
    cols = st.columns(3)
    cols[0].metric("Your job pays", f"{money(wage)}/hr", help=f"Take-home pay over {hours:.0f} hours a week.", border=True)
    cols[1].metric("Your money pays", f"{money(earning.per_hour, 2)}/hr", help="Every hour, day and night.", border=True)
    cols[2].metric("Work your money does for you", f"{replaced:,.0f} hrs/mo", border=True)
    workdays = replaced / (hours / 5)
    st.caption(
        f"Each month your money earns what you'd make in about {workdays:,.1f} "
        f"workdays, or {ui.pct(earning.per_month / take_home, 0)} of your take-home pay."
    )
