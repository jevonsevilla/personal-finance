"""Finance hub: run with ``uv run streamlit run hub/app.py``."""

import pandas as pd
import streamlit as st

import store

st.set_page_config(page_title="Finance Hub", page_icon=":material/savings:", layout="wide")

earnings = st.Page("views/earnings.py", title="Earning rate", icon=":material/bolt:", default=True)
portfolio = st.Page("views/portfolio.py", title="Portfolio", icon=":material/account_balance:")
check_in = st.Page("views/check_in.py", title="Check-in", icon=":material/edit_note:")
settings = st.Page("views/settings.py", title="Settings", icon=":material/settings:")

if store.is_initialized():
    if added := store.apply_recurring(pd.Timestamp.today().normalize()):
        st.toast(f"Logged {added} recurring deposit{'s' * (added != 1)}", icon=":material/event_repeat:")
    page = st.navigation({"Investments": [earnings, portfolio, check_in], "Setup": [settings]})
else:
    page = st.navigation(
        [st.Page("views/welcome.py", title="Welcome", icon=":material/waving_hand:", default=True), settings],
        position="hidden",
    )

if flash := st.session_state.pop("flash", None):
    st.success(flash, icon=":material/check_circle:")

page.run()
