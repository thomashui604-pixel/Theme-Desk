"""Theme Desk — Tech Basket Monitor. Streamlit entrypoint."""

from datetime import datetime

import streamlit as st

from analytics import basket_stats, build_stock_stats, market_regime, relative_panel
from config import BENCHMARKS, BENCHMARK_LABELS, FETCH_PERIOD, REGIME_BENCHMARK, Z_WINDOWS
from data import fetch_prices
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
    if "benchmark_mode" not in st.session_state:
        st.session_state.benchmark_mode = "absolute"


def _render_regime_badge(spy: "pd.Series | None") -> str:
    regime = market_regime(spy)
    return f"""
    <div style="display:inline-flex;align-items:center;gap:8px;background:#080f1a;border:1px solid rgba({_rgb_from_hex(regime['color'])},0.35);border-radius:6px;padding:6px 12px">
        <span style="width:6px;height:6px;border-radius:50%;background:{regime['color']};box-shadow:0 0 6px {regime['color']}"></span>
        <span style="font-size:11px;font-weight:700;color:{regime['color']};letter-spacing:0.08em">{regime['label']}</span>
        <span style="font-size:9px;color:#475569;font-family:'IBM Plex Mono',monospace">{regime['detail']}</span>
    </div>
    """


def _rgb_from_hex(hex_color: str) -> str:
    h = hex_color.lstrip("#")
    return f"{int(h[0:2], 16)},{int(h[2:4], 16)},{int(h[4:6], 16)}"


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

    bench_tickers = tuple(sorted({v for v in BENCHMARKS.values() if v} | {REGIME_BENCHMARK}))
    combined = tuple(sorted(set(all_tickers) | set(bench_tickers)))

    with st.spinner("Fetching market data…"):
        full_panel = fetch_prices(combined, FETCH_PERIOD)

    if full_panel.empty:
        st.error("Could not fetch price data. Check your internet connection.")
        return

    spy_series = full_panel[REGIME_BENCHMARK] if REGIME_BENCHMARK in full_panel.columns else None
    prices_df = full_panel[[c for c in all_tickers if c in full_panel.columns]]

    # Apply benchmark transform if relative mode is selected.
    bench_mode = st.session_state.benchmark_mode
    bench_ticker = BENCHMARKS.get(bench_mode)
    if bench_ticker and bench_ticker in full_panel.columns:
        prices_df = relative_panel(prices_df, full_panel[bench_ticker])

    with col_badge:
        current_time = datetime.now().strftime("%H:%M")
        st.markdown(f"""
        <div style="text-align:right;margin-top:8px">
            <span class="live-badge">● Live · {current_time}</span>
        </div>
        """, unsafe_allow_html=True)

    # Regime + benchmark toggle row
    col_regime, col_bench = st.columns([4, 2])
    with col_regime:
        st.markdown(_render_regime_badge(spy_series), unsafe_allow_html=True)
    with col_bench:
        bench_keys = list(BENCHMARKS.keys())
        bench_idx = bench_keys.index(bench_mode) if bench_mode in bench_keys else 0
        new_idx = st.selectbox(
            "Benchmark",
            range(len(bench_keys)),
            index=bench_idx,
            format_func=lambda i: f"Mode: {BENCHMARK_LABELS[bench_keys[i]]}",
            key="benchmark_select",
            label_visibility="collapsed",
        )
        if bench_keys[new_idx] != st.session_state.benchmark_mode:
            st.session_state.benchmark_mode = bench_keys[new_idx]
            st.rerun()

    st.markdown("<div style='height:8px'/>", unsafe_allow_html=True)

    stock_df = build_stock_stats(prices_df, baskets, z_window)
    b_stats = basket_stats(baskets, stock_df)

    tab_baskets, tab_rot, tab_mom, tab_settings = st.tabs([
        "Baskets", "Rotation Map", "Momentum Ranks", "⚙ Settings"
    ])

    with tab_baskets:
        render_landing_page(b_stats, stock_df, z_label)
    with tab_rot:
        render_rotation(b_stats, prices_df, baskets, z_window, z_label)
    with tab_mom:
        render_momentum(stock_df, b_stats, z_label)
    with tab_settings:
        render_settings()


if __name__ == "__main__":
    main()
