"""Today tab — what changed since yesterday across baskets."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from analytics import leadership_flips, momentum_history, zscore_crossings


def _basket_cumret(prices_df: pd.DataFrame, tickers: list, window: int = 126) -> pd.Series:
    members = [t for t in tickers if t in prices_df.columns]
    if not members:
        return pd.Series(dtype=float)
    rets = prices_df[members].pct_change().dropna(how="all").tail(window)
    if rets.empty:
        return pd.Series(dtype=float)
    mean_rets = rets.mean(axis=1)
    return (1 + mean_rets).cumprod() * 100
from views.common import PLOTLY_LAYOUT, _color, _rgb, _sign, pct_html, z_html


def _section_header(title: str, accent: str = "#f59e0b"):
    st.markdown(f"""
    <div style="display:flex;align-items:center;gap:10px;margin:18px 0 8px 0">
        <div style="width:3px;height:18px;background:{accent};border-radius:2px"></div>
        <span style="font-size:14px;font-weight:700;color:#e2e8f0;letter-spacing:0.06em;text-transform:uppercase">{title}</span>
    </div>
    """, unsafe_allow_html=True)


def _movers_card(df: pd.DataFrame, is_top: bool, baskets: dict):
    label = "▲ TOP MOVERS · 1D" if is_top else "▼ BOTTOM MOVERS · 1D"
    accent = "#10b981" if is_top else "#ef4444"
    rows_html = ""
    for _, row in df.iterrows():
        cfg = baskets.get(row["basket"], {})
        color = cfg.get("color", "#64748b")
        rgb = _rgb(color)
        rows_html += f"""
        <div style="display:flex;align-items:center;gap:10px;padding:6px 0;border-bottom:1px solid #0f172a">
            <span style="width:50px;font-size:13px;font-weight:700;color:#e2e8f0;font-family:'IBM Plex Mono',monospace">{row['ticker']}</span>
            <span style="flex:1;font-size:9px;color:{color};background:rgba({rgb},0.13);border:1px solid rgba({rgb},0.27);border-radius:3px;padding:1px 6px;font-weight:700;width:fit-content;flex:0 0 auto">{row['basket'][:10]}</span>
            <span style="margin-left:auto">{pct_html(row['ret1d'], 14)}</span>
        </div>"""
    st.html(f"""
    <div style="background:#080f1a;border:1px solid #1e293b;border-radius:8px;padding:14px 16px">
        <div style="font-size:12px;font-weight:700;color:{accent};letter-spacing:0.1em;margin-bottom:8px">{label}</div>
        {rows_html if rows_html else '<div style="color:#475569;font-size:13px">No data</div>'}
    </div>
    """)


def _crossings_card(crossings: list, baskets: dict, max_show: int = 8):
    rows_html = ""
    for r in crossings[:max_show]:
        color = baskets.get(r["basket"], {}).get("color", "#64748b")
        rgb = _rgb(color)
        arrow = "↑" if r["direction"] == "up" else "↓"
        arrow_color = "#10b981" if r["direction"] == "up" else "#ef4444"
        rows_html += f"""
        <div style="display:flex;align-items:center;gap:10px;padding:6px 0;border-bottom:1px solid #0f172a">
            <span style="color:{arrow_color};font-size:17px;font-weight:900;width:14px">{arrow}</span>
            <span style="width:50px;font-size:13px;font-weight:700;color:#e2e8f0;font-family:'IBM Plex Mono',monospace">{r['ticker']}</span>
            <span style="font-size:9px;color:{color};background:rgba({rgb},0.13);border:1px solid rgba({rgb},0.27);border-radius:3px;padding:1px 6px;font-weight:700">{r['basket'][:10]}</span>
            <span style="margin-left:auto;font-size:12px;color:#64748b;font-family:'IBM Plex Mono',monospace">{r['prev_z']:+.2f}σ → <span style="color:{arrow_color};font-weight:700">{r['cur_z']:+.2f}σ</span></span>
        </div>"""
    body = rows_html if rows_html else '<div style="color:#475569;font-size:13px">No z-score crossings today.</div>'
    st.html(f"""
    <div style="background:#080f1a;border:1px solid #1e293b;border-radius:8px;padding:14px 16px">
        <div style="font-size:12px;font-weight:700;color:#f59e0b;letter-spacing:0.1em;margin-bottom:8px">⤢ 20D Z-SCORE CROSSINGS</div>
        <div style="font-size:9px;color:#475569;margin-bottom:8px">Tickers that flipped above/below zero since yesterday</div>
        {body}
    </div>
    """)


def _flips_card(flips: list, baskets: dict):
    rows_html = ""
    for f in flips:
        color = baskets.get(f["basket"], {}).get("color", "#64748b")
        rgb = _rgb(color)
        delta = f["delta"]
        arrow = "↑" if delta > 0 else "↓"
        arrow_color = "#10b981" if delta > 0 else "#ef4444"
        rows_html += f"""
        <div style="display:flex;align-items:center;gap:10px;padding:6px 0;border-bottom:1px solid #0f172a">
            <span style="width:4px;height:22px;background:{color};border-radius:2px"></span>
            <span style="flex:1;font-size:13px;font-weight:700;color:#e2e8f0">{f['basket']}</span>
            <span style="font-size:12px;color:#64748b;font-family:'IBM Plex Mono',monospace">#{f['prev_rank']} → #{f['cur_rank']}</span>
            <span style="color:{arrow_color};font-size:14px;font-weight:900;font-family:'IBM Plex Mono',monospace">{arrow} {abs(delta)}</span>
        </div>"""
    body = rows_html if rows_html else '<div style="color:#475569;font-size:13px">No significant leadership flips in the last 5 days.</div>'
    st.html(f"""
    <div style="background:#080f1a;border:1px solid #1e293b;border-radius:8px;padding:14px 16px">
        <div style="font-size:12px;font-weight:700;color:#8b5cf6;letter-spacing:0.1em;margin-bottom:8px">↻ LEADERSHIP FLIPS · 5D</div>
        <div style="font-size:9px;color:#475569;margin-bottom:8px">Baskets whose 20d-z rank shifted by ≥3 positions</div>
        {body}
    </div>
    """)


def _sparkline_row(basket: str, color: str, series: pd.Series, latest: float):
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=series.index, y=series.values, mode="lines",
        line=dict(color=color, width=1.5),
        hovertemplate="%{x|%b %d}: %{y:+.2f}σ<extra></extra>",
    ))
    fig.add_hline(y=0, line=dict(color="#334155", dash="dot", width=1))
    fig.update_layout(
        **{**PLOTLY_LAYOUT,
           "height": 60,
           "margin": dict(l=0, r=0, t=0, b=0),
           "showlegend": False,
           "xaxis": dict(visible=False),
           "yaxis": dict(visible=False, zeroline=False)},
    )
    col_name, col_val, col_spark = st.columns([2, 1, 5])
    with col_name:
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:8px;padding-top:18px">'
            f'<div style="width:3px;height:18px;background:{color};border-radius:2px"></div>'
            f'<span style="font-size:14px;font-weight:700;color:#e2e8f0">{basket}</span></div>',
            unsafe_allow_html=True,
        )
    with col_val:
        st.markdown(
            f'<div style="padding-top:18px;text-align:right">{z_html(latest, 16)}</div>',
            unsafe_allow_html=True,
        )
    with col_spark:
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False},
                        key=f"spark_{basket}")


def _render_compare(prices_df: pd.DataFrame, baskets: dict):
    options = list(baskets.keys())
    if len(options) < 2:
        st.info("Need at least two baskets to compare.")
        return

    default = st.session_state.get("compare_baskets") or options[:2]
    default = [b for b in default if b in options][:2] or options[:2]

    selected = st.multiselect(
        "Pick two baskets",
        options=options,
        default=default,
        max_selections=2,
        key="compare_baskets",
        label_visibility="collapsed",
    )
    if len(selected) != 2:
        st.info("Pick exactly two baskets.")
        return

    a_name, b_name = selected
    a_cfg = baskets[a_name]
    b_cfg = baskets[b_name]
    a_cum = _basket_cumret(prices_df, a_cfg["tickers"], window=126)
    b_cum = _basket_cumret(prices_df, b_cfg["tickers"], window=126)
    if a_cum.empty or b_cum.empty:
        st.warning("Not enough data for one of the selected baskets.")
        return

    idx = a_cum.index.intersection(b_cum.index)
    a_cum = a_cum.loc[idx]
    b_cum = b_cum.loc[idx]
    ratio = (a_cum / b_cum) * 100 / (a_cum.iloc[0] / b_cum.iloc[0])  # rebased to 100

    col_chart, col_rs = st.columns([2, 1])
    with col_chart:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=a_cum.index, y=a_cum.values, mode="lines",
                                 name=a_name,
                                 line=dict(color=a_cfg["color"], width=1.6),
                                 hovertemplate=f"{a_name}: %{{y:.1f}}<extra></extra>"))
        fig.add_trace(go.Scatter(x=b_cum.index, y=b_cum.values, mode="lines",
                                 name=b_name,
                                 line=dict(color=b_cfg["color"], width=1.6),
                                 hovertemplate=f"{b_name}: %{{y:.1f}}<extra></extra>"))
        fig.update_layout(
            **{**PLOTLY_LAYOUT,
               "height": 260,
               "margin": dict(l=40, r=20, t=10, b=30),
               "yaxis": {**PLOTLY_LAYOUT["yaxis"],
                         "title": dict(text="Normalized (start=100)",
                                       font=dict(color="#475569", size=9))}},
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    with col_rs:
        rs_fig = go.Figure()
        rs_fig.add_trace(go.Scatter(
            x=ratio.index, y=ratio.values, mode="lines",
            line=dict(color="#06b6d4", width=1.4),
            hovertemplate=f"{a_name}/{b_name}: %{{y:.2f}}<extra></extra>",
        ))
        rs_fig.add_hline(y=100, line=dict(color="#334155", dash="dot", width=1))
        rs_fig.update_layout(
            **{**PLOTLY_LAYOUT,
               "height": 260,
               "margin": dict(l=40, r=20, t=10, b=30),
               "showlegend": False,
               "yaxis": {**PLOTLY_LAYOUT["yaxis"],
                         "title": dict(text=f"{a_name} ÷ {b_name} (rebased)",
                                       font=dict(color="#475569", size=9))}},
        )
        st.plotly_chart(rs_fig, use_container_width=True, config={"displayModeBar": False})

    latest_rs = ratio.iloc[-1]
    rs_color = "#10b981" if latest_rs >= 100 else "#ef4444"
    rs_arrow = "▲" if latest_rs >= 100 else "▼"
    rs_pct = latest_rs - 100
    st.markdown(
        f'<div style="font-size:13px;color:#94a3b8;margin-top:6px">'
        f'Over last ~6 months, <b style="color:{a_cfg["color"]}">{a_name}</b> is '
        f'<span style="color:{rs_color};font-weight:700;font-family:\'IBM Plex Mono\',monospace">'
        f'{rs_arrow} {abs(rs_pct):.1f}%</span> vs <b style="color:{b_cfg["color"]}">{b_name}</b>.'
        f'</div>',
        unsafe_allow_html=True,
    )


def render_today(stock_df: pd.DataFrame, prices_df: pd.DataFrame,
                 baskets: dict, z_window: int, regime: dict):
    st.markdown(f"""
    <div style="display:flex;align-items:center;gap:14px;margin-bottom:8px">
        <div style="font-size:17px;font-weight:700;color:#e2e8f0">What changed</div>
        <span style="font-size:12px;color:#64748b;font-family:'IBM Plex Mono',monospace">
            Regime: <span style="color:{regime['color']};font-weight:700">{regime['label']}</span>
            &nbsp;·&nbsp; {regime['detail']}
        </span>
    </div>
    """, unsafe_allow_html=True)

    if stock_df.empty or prices_df.empty:
        st.info("No data yet.")
        return

    hist = momentum_history(prices_df, baskets, z_window, lookback=20)
    ticker_z = hist["ticker_z"]
    basket_z = hist["basket_z"]

    # ── Movers + crossings row ──
    col_top, col_bot, col_cross = st.columns([1, 1, 1.2])
    valid = stock_df.dropna(subset=["ret1d"]).sort_values("ret1d", ascending=False)
    with col_top:
        _movers_card(valid.head(5), is_top=True, baskets=baskets)
    with col_bot:
        _movers_card(valid.tail(5).iloc[::-1], is_top=False, baskets=baskets)
    with col_cross:
        _crossings_card(zscore_crossings(ticker_z, baskets), baskets)

    # ── Leadership flips ──
    _section_header("Basket leadership", accent="#8b5cf6")
    _flips_card(leadership_flips(basket_z, lookback_days=5, min_change=3), baskets)

    # ── Compare two baskets ──
    _section_header("Compare", accent="#06b6d4")
    _render_compare(prices_df, baskets)

    # ── Sparklines ──
    _section_header("20d momentum · last 60 days", accent="#f59e0b")
    if basket_z.empty:
        st.info("Not enough history to draw sparklines.")
        return
    spark_window = basket_z.dropna(how="all").tail(60)
    latest = spark_window.iloc[-1]
    # Sort by today's z, descending.
    ordered = latest.sort_values(ascending=False).index.tolist()
    for name in ordered:
        color = baskets.get(name, {}).get("color", "#64748b")
        s = spark_window[name].dropna()
        if s.empty:
            continue
        _sparkline_row(name, color, s, latest[name])
