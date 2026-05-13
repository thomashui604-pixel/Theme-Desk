"""Theme Desk — Tech Basket Monitor. Streamlit entrypoint."""

from datetime import datetime

import streamlit as st

from analytics import basket_stats, build_stock_stats
from config import FETCH_PERIOD, Z_WINDOWS
from data import fetch_prices, snapshot_today
from views.baskets import render_landing_page
from views.common import inject_css
from views.ranks import render_momentum
from views.rotation import render_rotation
from views.settings import load_default_baskets, render_settings

st.set_page_config(
    page_title="Theme Desk",
    page_icon="⬡",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_css()


def _init_session_state() -> None:
    if "baskets" not in st.session_state:
        st.session_state.baskets = load_default_baskets()
    if "editing_basket" not in st.session_state:
        st.session_state.editing_basket = None
    if "selected_basket" not in st.session_state:
        st.session_state.selected_basket = list(st.session_state.baskets.keys())[0]
    if "z_window" not in st.session_state:
        st.session_state.z_window = 252
    if "expanded_basket" not in st.session_state:
        st.session_state.expanded_basket = None
    if "display_mode" not in st.session_state:
        st.session_state.display_mode = "returns"
    if "preview_period" not in st.session_state:
        st.session_state.preview_period = "5d"


def main():
    _init_session_state()

    col_title, col_badge = st.columns([6, 1])
    with col_title:
        st.markdown("""
        <div style="display:flex;align-items:center;gap:14px;margin-bottom:20px">
            <div style="width:36px;height:36px;background:linear-gradient(135deg,#f59e0b,#ef4444);border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:16px;font-weight:900;color:#000">⬡</div>
            <div>
                <div style="font-size:20px;font-weight:700;letter-spacing:-0.02em;color:#e2e8f0">THEME DESK</div>
                <div style="font-size:10px;color:#475569;letter-spacing:0.1em;text-transform:uppercase">Tech Basket Monitor · Live via yfinance</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    baskets = st.session_state.baskets
    z_window = st.session_state.z_window
    z_label = next(k for k, v in Z_WINDOWS.items() if v == z_window)
    all_tickers = tuple(sorted({t for cfg in baskets.values() for t in cfg["tickers"]}))

    with st.spinner("Fetching market data…"):
        prices_df = fetch_prices(all_tickers, FETCH_PERIOD)

    if prices_df.empty:
        st.error("Could not fetch price data. Check your internet connection.")
        return

    with col_badge:
        current_time = datetime.now().strftime("%H:%M")
        st.markdown(f"""
        <div style="text-align:right;margin-top:8px">
            <span class="live-badge">● Live · {current_time}</span>
        </div>
        """, unsafe_allow_html=True)

    stock_df = build_stock_stats(prices_df, baskets, z_window)
    b_stats = basket_stats(baskets, stock_df)

    snapshot_today(stock_df, b_stats, prices_df)

    tab_baskets, tab_rot, tab_mom, tab_settings = st.tabs([
        "Baskets", "Rotation Map", "Momentum Ranks", "⚙ Settings"
    ])

    with tab_baskets:
        render_landing_page(b_stats, stock_df, z_label)
    with tab_rot:
        render_rotation(b_stats, z_label)
    with tab_mom:
        render_momentum(stock_df, b_stats, z_label)
    with tab_settings:
        render_settings()


if __name__ == "__main__":
    main()
