import streamlit as st

import store

st.title("Welcome to your finance hub")
st.markdown(
    """
    This hub tracks your investments and shows the one number that matters most
    for staying motivated: **how fast your money earns money**, per hour, day,
    month and year.

    It works with any account, including stocks, funds, MP2, time deposits and
    savings. Once a month you type in what each account is worth, and the hub
    works out what you put in versus what your money earned on its own.

    Your data stays on this computer, in `data/hub/`.
    """
)

cols = st.columns(2)
with cols[0].container(border=True):
    st.markdown("**Explore with sample data**")
    st.caption("A made-up portfolio, so you can see every page in action. You can erase it later.")
    if st.button("Load sample portfolio", type="primary"):
        store.load_sample()
        st.rerun()
with cols[1].container(border=True):
    st.markdown("**Start with my own numbers**")
    st.caption("Begin empty, then add your accounts and what they're worth today.")
    if st.button("Start fresh"):
        store.start_empty()
        st.switch_page("views/settings.py")
