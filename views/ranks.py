"""Momentum Ranks tab."""

import pandas as pd
import streamlit as st

from views.common import _rgb, z_html


def render_momentum(stock_df: pd.DataFrame, b_stats: pd.DataFrame, z_label: str):
    col_hdr, col_mode = st.columns([3, 1])
    with col_hdr:
        st.markdown("""
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:4px">
            <div style="width:3px;height:20px;background:#f59e0b;border-radius:2px"></div>
            <span style="font-size:13px;font-weight:700;color:#e2e8f0">Cross-Basket Momentum Ranks</span>
        </div>
        """, unsafe_allow_html=True)
    with col_mode:
        mode = st.radio("Mode", ["1d", "5d", "20d"], horizontal=True, key="mom_mode", label_visibility="collapsed")

    z_col = "z1d" if mode == "1d" else ("z5d" if mode == "5d" else "z20d")
    valid_df = stock_df.dropna(subset=[z_col]).sort_values(z_col, ascending=False)

    if valid_df.empty:
        st.info("No z-score data yet.")
        return

    top5 = valid_df.head(5)
    bot5 = valid_df.tail(5).iloc[::-1]

    def rank_rows_html(df, is_top):
        rows = ""
        for rank, (_, row) in enumerate(df.iterrows(), 1):
            val = row[z_col]
            color = st.session_state.baskets.get(row["basket"], {}).get("color", "#64748b")
            bar_w = min(100, abs(val) * 28)
            bar_color = "#10b981" if is_top else "#ef4444"
            bar_dir = "left" if is_top else "right"
            rows += f"""
            <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px">
                <span style="width:16px;font-size:9px;color:#475569;font-family:'IBM Plex Mono',monospace;text-align:right">{rank}</span>
                <span style="width:46px;font-size:11px;font-weight:700;color:#e2e8f0;font-family:'IBM Plex Mono',monospace">{row["ticker"]}</span>
                <div style="flex:1;background:#0f172a;border-radius:2px;height:14px;position:relative;overflow:hidden">
                    <div style="position:absolute;{bar_dir}:0;top:0;bottom:0;width:{bar_w}%;background:{bar_color};opacity:0.7;border-radius:2px"></div>
                </div>
                {z_html(val)}
                <span style="background:rgba({_rgb(color)},0.13);color:{color};border:1px solid rgba({_rgb(color)},0.27);border-radius:3px;padding:1px 6px;font-size:9px;font-weight:700">{row["basket"][:6]}</span>
            </div>"""
        return rows

    col_top, col_bot = st.columns(2)
    with col_top:
        st.html(f"""
        <div style="background:#080f1a;border:1px solid #1e293b;border-radius:8px;padding:20px">
            <div style="font-size:10px;font-weight:700;color:#10b981;letter-spacing:0.12em;text-transform:uppercase;margin-bottom:14px">▲ Top z-score ({mode})</div>
            {rank_rows_html(top5, True)}
        </div>
        """)
    with col_bot:
        st.html(f"""
        <div style="background:#080f1a;border:1px solid #1e293b;border-radius:8px;padding:20px">
            <div style="font-size:10px;font-weight:700;color:#ef4444;letter-spacing:0.12em;text-transform:uppercase;margin-bottom:14px">▼ Bottom z-score ({mode})</div>
            {rank_rows_html(bot5, False)}
        </div>
        """)

    st.markdown("<div style='height:20px'/>", unsafe_allow_html=True)

    bz_col = "avgZ1d" if mode == "1d" else ("avgZ5d" if mode == "5d" else "avgZ20d")
    sorted_baskets = b_stats.sort_values(bz_col, ascending=False)

    basket_rows = ""
    for rank, (_, row) in enumerate(sorted_baskets.iterrows(), 1):
        val = row[bz_col]
        color = row["color"]
        bar_w = min(100, abs(val) * 28)
        bar_color = "#10b981" if val >= 0 else "#ef4444"
        bar_dir = "left" if val >= 0 else "right"
        basket_rows += f"""
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px">
            <span style="width:16px;font-size:9px;color:#475569;font-family:'IBM Plex Mono',monospace;text-align:right">{rank}</span>
            <span style="width:4px;height:24px;background:{color};border-radius:2px;flex-shrink:0"></span>
            <span style="width:110px;font-size:11px;font-weight:700;color:#e2e8f0">{row["basket"]}</span>
            <div style="flex:1;background:#0f172a;border-radius:2px;height:14px;position:relative;overflow:hidden">
                <div style="position:absolute;{bar_dir}:0;top:0;bottom:0;width:{bar_w}%;background:{bar_color};opacity:0.7;border-radius:2px"></div>
            </div>
            {z_html(val)}
        </div>"""

    st.html(f"""
    <div style="background:#080f1a;border:1px solid #1e293b;border-radius:8px;padding:20px">
        <div style="font-size:10px;font-weight:700;color:#f59e0b;letter-spacing:0.12em;text-transform:uppercase;margin-bottom:14px">Basket z-score ({mode})</div>
        {basket_rows}
    </div>
    """)
