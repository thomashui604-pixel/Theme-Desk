"""Baskets tab — landing grid with expandable cards."""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from analytics import basket_correlation_matrix
from config import INTERVALS, Z_WINDOWS
from views.common import PLOTLY_LAYOUT, _color, _rgb, _sign, pct_html, z_html


def _mini_row_html(ticker, val, show_z=False):
    if show_z:
        display = f"{abs(val):.1f}σ" if val is not None else "—"
        c = _color(val) if val is not None else "#334155"
    else:
        display = f"{abs(val):.1f}%"
        c = _color(val)
    sign = _sign(val) if val is not None else ""
    return f'<div style="display:flex;justify-content:space-between;padding:2px 0;font-size:12px"><span style="color:#94a3b8;font-family:\'IBM Plex Mono\',monospace">{ticker}</span><span style="color:{c};font-family:\'IBM Plex Mono\',monospace;font-weight:600">{sign}{display}</span></div>'


def _breadth_bar(pct: float) -> str:
    if pct is None:
        return '<div style="font-size:9px;color:#475569">breadth —</div>'
    color = "#10b981" if pct >= 60 else ("#f59e0b" if pct >= 40 else "#ef4444")
    return f"""
    <div style="margin-top:4px">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:2px">
            <span style="font-size:8px;color:#475569;font-weight:600;letter-spacing:0.06em">BREADTH ▸ 50D MA</span>
            <span style="font-size:9px;color:{color};font-family:'IBM Plex Mono',monospace;font-weight:700">{pct:.0f}%</span>
        </div>
        <div style="background:#0f172a;height:4px;border-radius:2px;overflow:hidden">
            <div style="background:{color};height:100%;width:{pct:.0f}%;border-radius:2px"></div>
        </div>
    </div>"""


def render_landing_page(b_stats: pd.DataFrame, stock_df: pd.DataFrame, z_label: str,
                        quality: dict | None = None, prices_df: pd.DataFrame | None = None):
    quality = quality or {}
    _PREVIEW_PERIODS = {
        "1d":  ("ret1d",  "z1d",  "1D"),
        "5d":  ("ret5d",  "z5d",  "5D"),
        "20d": ("ret20d", "z20d", "20D"),
        "3m":  ("ret_63", "z_63", "3M"),
        "6m":  ("ret_126","z_126","6M"),
        "12m": ("ret_252","z_252","12M"),
        "ytd": ("ret_ytd","z_ytd","YTD"),
    }

    ctrl1, ctrl2, ctrl3 = st.columns([2, 2, 2])

    with ctrl1:
        period_keys = list(_PREVIEW_PERIODS.keys())
        period_labels = [_PREVIEW_PERIODS[k][2] for k in period_keys]
        cur_period = st.session_state.preview_period
        cur_idx = period_keys.index(cur_period) if cur_period in period_keys else 1
        new_idx = st.selectbox(
            "Period", range(len(period_keys)), index=cur_idx,
            format_func=lambda i: f"Period: {period_labels[i]}",
            key="preview_period_select", label_visibility="collapsed",
        )
        if period_keys[new_idx] != st.session_state.preview_period:
            st.session_state.preview_period = period_keys[new_idx]
            st.rerun()

    with ctrl2:
        z_options = list(Z_WINDOWS.keys())
        z_idx = z_options.index(z_label) if z_label in z_options else 2
        new_z_label = st.selectbox(
            "Z-Score Period", z_options, index=z_idx,
            key="landing_z_window", label_visibility="collapsed",
        )
        new_z_val = Z_WINDOWS[new_z_label]
        if new_z_val != st.session_state.z_window:
            st.session_state.z_window = new_z_val
            st.rerun()

    with ctrl3:
        mode_labels = {"returns": "Raw Returns %", "zscore": "Z-Score Momentum σ"}
        current_mode = st.session_state.display_mode
        toggled = st.button(
            f"Showing: {mode_labels[current_mode]}  ⇄",
            key="toggle_display_mode", use_container_width=True,
        )
        if toggled:
            st.session_state.display_mode = "zscore" if current_mode == "returns" else "returns"
            st.rerun()

    pp = st.session_state.preview_period
    pp_ret_col, pp_z_col, pp_label = _PREVIEW_PERIODS[pp]

    mode_display = "RAW RETURNS %" if st.session_state.display_mode == "returns" else "Z-SCORE MOMENTUM σ"
    st.markdown(f"""
    <div style="display:flex;align-items:center;gap:16px;margin-bottom:14px">
        <div style="font-size:12px;font-weight:700;color:#94a3b8;letter-spacing:0.14em;text-transform:uppercase">
            ▌ Theme Baskets
        </div>
        <span style="font-size:9px;color:#475569;font-family:'IBM Plex Mono',monospace">
            z-window: {z_label} &nbsp;·&nbsp; {mode_display} &nbsp;·&nbsp; Period: {pp_label}
        </span>
    </div>
    """, unsafe_allow_html=True)

    baskets = st.session_state.baskets
    expanded = st.session_state.expanded_basket
    show_z = st.session_state.display_mode == "zscore"

    card_data = []
    for basket_name, cfg in baskets.items():
        b_row = b_stats[b_stats["basket"] == basket_name]
        if b_row.empty:
            continue
        b_row = b_row.iloc[0]
        members = stock_df[stock_df["ticker"].isin(cfg["tickers"])]
        if members.empty:
            continue
        card_data.append((basket_name, cfg, b_row, members))

    if not card_data:
        st.info("No baskets with data. Add tickers in Settings.")
        return

    n_cards = len(card_data)
    cols_per_row = min(n_cards, 5)

    def _render_card(basket_name, cfg, b_row, members, slot):
        color = cfg["color"]
        rgb = _rgb(color)
        is_exp = expanded == basket_name

        sort_col = pp_z_col if show_z else pp_ret_col
        sorted_m = members.dropna(subset=[sort_col]).sort_values(sort_col, ascending=False) if show_z else members.sort_values(sort_col, ascending=False)
        top3 = sorted_m.head(3)
        bot3 = sorted_m.tail(3).iloc[::-1]

        if show_z:
            _bz_map = {"1d": "avgZ1d", "5d": "avgZ5d", "20d": "avgZ20d",
                       "3m": "avgZ_63", "6m": "avgZ_126", "12m": "avgZ_252", "ytd": "avgZ_ytd"}
            basket_perf = b_row.get(_bz_map.get(pp, "avgZ5d"), 0)
        else:
            _br_map = {"1d": "avg1d", "5d": "avg5d", "20d": "avg20d",
                       "3m": "avg_ret_63", "6m": "avg_ret_126", "12m": "avg_ret_252", "ytd": "avg_ret_ytd"}
            basket_perf = b_row.get(_br_map.get(pp, "avg5d"), 0)
        try:
            basket_perf = float(basket_perf)
            if np.isnan(basket_perf):
                basket_perf = 0.0
        except (TypeError, ValueError):
            basket_perf = 0.0
        is_up = basket_perf >= 0

        top_html = "".join(_mini_row_html(r["ticker"], r[sort_col], show_z) for _, r in top3.iterrows())
        bot_html = "".join(_mini_row_html(r["ticker"], r[sort_col], show_z) for _, r in bot3.iterrows())

        if show_z:
            m1_l, m1_v = "1D σ", z_html(b_row["avgZ1d"], 13)
            m2_l, m2_v = "5D σ", z_html(b_row["avgZ5d"], 13)
            m3_l, m3_v = "20D σ", z_html(b_row["avgZ20d"], 13)
        else:
            m1_l, m1_v = "1D", pct_html(b_row["avg1d"], 13)
            m2_l, m2_v = "5D", pct_html(b_row["avg5d"], 13)
            m3_l, m3_v = "20D", pct_html(b_row["avg20d"], 13)

        perf_color = "#10b981" if is_up else "#ef4444"
        perf_rgb = _rgb(perf_color)
        if is_exp:
            border = f"2px solid rgba({rgb},0.6)"
            bg = "#0a1120"
        else:
            border = f"1px solid rgba({perf_rgb},0.3)"
            bg = "#080f1a"
        indicator = f'<div style="width:6px;height:6px;border-radius:50%;background:{color};box-shadow:0 0 6px {color}"></div>' if is_exp else ""

        perf_sign = "▲" if is_up else "▼"
        perf_display = f"{abs(basket_perf):.2f}σ" if show_z else f"{abs(basket_perf):.2f}%"
        perf_badge = f'<span style="color:{perf_color};font-family:\'IBM Plex Mono\',monospace;font-weight:700;font-size:14px">{perf_sign} {perf_display}</span>'

        glow_style = f"box-shadow:inset 3px 0 8px -4px {'rgba(16,185,129,0.3)' if is_up else 'rgba(239,68,68,0.3)'};"

        breadth_pct = (quality.get(basket_name) or {}).get("breadth_pct")
        breadth_html = _breadth_bar(breadth_pct)

        with slot:
            st.html(f"""
            <div style="background:{bg};border:{border};border-radius:10px;padding:14px 16px;min-height:300px;display:flex;flex-direction:column;{glow_style}">
                <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px">
                    <div style="width:3px;height:22px;background:{color};border-radius:2px;flex-shrink:0"></div>
                    <div style="flex:1;min-width:0">
                        <div style="font-size:16px;font-weight:700;color:#e2e8f0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{basket_name}</div>
                    </div>
                    {indicator}
                </div>
                <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:10px">
                    <span style="background:rgba({rgb},0.12);color:{color};border:1px solid rgba({rgb},0.25);border-radius:3px;padding:1px 6px;font-size:8px;font-weight:700">{b_row["n"]} STOCKS</span>
                    {perf_badge}
                </div>
                <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:6px;margin-bottom:6px">
                    <div style="background:#0b1322;border-radius:5px;padding:6px 8px;text-align:center">
                        <div style="font-size:7px;color:#475569;font-weight:600;letter-spacing:0.06em;margin-bottom:2px">{m1_l}</div>
                        <div>{m1_v}</div>
                    </div>
                    <div style="background:#0b1322;border-radius:5px;padding:6px 8px;text-align:center">
                        <div style="font-size:7px;color:#475569;font-weight:600;letter-spacing:0.06em;margin-bottom:2px">{m2_l}</div>
                        <div>{m2_v}</div>
                    </div>
                    <div style="background:#0b1322;border-radius:5px;padding:6px 8px;text-align:center">
                        <div style="font-size:7px;color:#475569;font-weight:600;letter-spacing:0.06em;margin-bottom:2px">{m3_l}</div>
                        <div>{m3_v}</div>
                    </div>
                </div>
                <div style="margin-bottom:10px;padding-bottom:10px;border-bottom:1px solid #1e293b">
                    {breadth_html}
                </div>
                <div style="margin-bottom:6px">
                    <div style="font-size:8px;font-weight:700;color:#10b981;letter-spacing:0.08em;margin-bottom:3px">▲ TOP 3 ({pp_label})</div>
                    {top_html}
                </div>
                <div style="flex:1">
                    <div style="font-size:8px;font-weight:700;color:#ef4444;letter-spacing:0.08em;margin-bottom:3px">▼ BOTTOM 3 ({pp_label})</div>
                    {bot_html}
                </div>
            </div>
            """)

            btn_label = f"▾ {basket_name}" if is_exp else f"▸ {basket_name}"
            if st.button(btn_label, key=f"expand_{basket_name}", use_container_width=True):
                if is_exp:
                    st.session_state.expanded_basket = None
                else:
                    st.session_state.expanded_basket = basket_name
                    st.session_state.selected_basket = basket_name
                st.rerun()

    # Render in row chunks so the expanded detail drops in directly under
    # the row containing the pressed button, not at the bottom of the page.
    for row_start in range(0, n_cards, cols_per_row):
        row = card_data[row_start:row_start + cols_per_row]
        row_cols = st.columns(cols_per_row)
        for slot, (basket_name, cfg, b_row, members) in zip(row_cols, row):
            _render_card(basket_name, cfg, b_row, members, slot)

        if expanded:
            in_row = next(((bn, c, br, m) for bn, c, br, m in row if bn == expanded), None)
            if in_row:
                basket_name, cfg, b_row, members = in_row
                st.markdown("<div style='height:12px'/>", unsafe_allow_html=True)
                render_expanded_detail(
                    basket_name, cfg, b_row, members,
                    quality.get(basket_name) or {},
                    prices_df,
                )


def render_expanded_detail(basket_name, cfg, b_row, members_df,
                           q: dict | None = None,
                           prices_df: pd.DataFrame | None = None):
    q = q or {}
    color = cfg["color"]
    rgb = _rgb(color)
    show_z = st.session_state.display_mode == "zscore"

    if show_z:
        st.markdown('<div style="font-size:12px;font-weight:700;color:#64748b;text-transform:uppercase;letter-spacing:0.05em;border-bottom:1px solid #1e293b;padding-bottom:4px;margin-bottom:8px">Momentum Regime (Avg Z-Score)</div>', unsafe_allow_html=True)
        metric_cols = st.columns(len(INTERVALS) + 1)
        for i, (label, lb) in enumerate(INTERVALS):
            val = b_row[f"avgZ_{lb}"]
            metric_cols[i].metric(f"{label} σ", f"{'+' if val >= 0 else ''}{val:.2f}σ")
        zytd_val = b_row["avgZ_ytd"]
        metric_cols[-1].metric("YTD σ", f"{'+' if zytd_val >= 0 else ''}{zytd_val:.2f}σ")
    else:
        st.markdown('<div style="font-size:12px;font-weight:700;color:#64748b;text-transform:uppercase;letter-spacing:0.05em;border-bottom:1px solid #1e293b;padding-bottom:4px;margin-bottom:8px">Basket Performance (Avg Raw %)</div>', unsafe_allow_html=True)
        metric_cols = st.columns(len(INTERVALS) + 1)
        for i, (label, lb) in enumerate(INTERVALS):
            val = b_row[f"avg_ret_{lb}"]
            metric_cols[i].metric(label, f"{'+' if val >= 0 else ''}{val:.2f}%")
        ytd_val = b_row["avg_ret_ytd"]
        metric_cols[-1].metric("YTD", f"{'+' if ytd_val >= 0 else ''}{ytd_val:.2f}%")

    st.markdown("<div style='height:12px'/>", unsafe_allow_html=True)

    col_headers = ""
    for label, lb in INTERVALS:
        short = label.replace("-", "")
        col_headers += f'<th style="text-align:right;padding:8px 10px;font-size:9px;font-weight:700;color:#475569;white-space:nowrap">{short}</th>'
    col_headers += '<th style="text-align:right;padding:8px 10px;font-size:9px;font-weight:700;color:#475569;white-space:nowrap">YTD</th>'

    n_data_cols = len(INTERVALS) + 1
    group_label = "Z-SCORE MOMENTUM (σ)" if show_z else "RAW RETURN %"

    rows_html = ""
    default_sort = "z_20" if show_z else "ret_20"
    for _, row in members_df.sort_values(default_sort, ascending=False, na_position="last").iterrows():
        data_cells = ""
        if show_z:
            for _, lb in INTERVALS:
                data_cells += f'<td style="padding:6px 10px;text-align:right">{z_html(row[f"z_{lb}"], 13)}</td>'
            data_cells += f'<td style="padding:6px 10px;text-align:right">{z_html(row["z_ytd"], 13)}</td>'
        else:
            for _, lb in INTERVALS:
                data_cells += f'<td style="padding:6px 10px;text-align:right">{pct_html(row[f"ret_{lb}"], 13)}</td>'
            data_cells += f'<td style="padding:6px 10px;text-align:right">{pct_html(row["ret_ytd"], 13)}</td>'

        rows_html += f"""
        <tr style="border-bottom:1px solid #0f172a">
            <td style="padding:6px 10px;font-weight:700;color:#e2e8f0;font-family:'IBM Plex Mono',monospace;font-size:13px;white-space:nowrap">{row["ticker"]}</td>
            <td style="padding:6px 10px;text-align:right;color:#94a3b8;font-family:'IBM Plex Mono',monospace;font-size:13px">${row["price"]:.2f}</td>
            {data_cells}
        </tr>"""

    st.html(f"""
    <div style="background:#080f1a;border:1px solid rgba({rgb},0.25);border-radius:8px;overflow-x:auto">
        <table style="width:100%;border-collapse:collapse;font-size:13px">
            <thead>
                <tr style="border-bottom:1px solid #1e293b;background:#0f172a">
                    <th></th><th></th>
                    <th colspan="{n_data_cols}" style="text-align:center;padding:6px;font-size:9px;font-weight:700;color:#64748b;letter-spacing:0.05em;border-left:1px solid #1e293b;border-right:1px solid #1e293b">{group_label}</th>
                </tr>
                <tr style="border-bottom:1px solid #1e293b">
                    <th style="text-align:left;padding:8px 10px;font-size:9px;font-weight:700;color:#475569;letter-spacing:0.08em">TICKER</th>
                    <th style="text-align:right;padding:8px 10px;font-size:9px;font-weight:700;color:#475569;letter-spacing:0.08em">PRICE</th>
                    {col_headers}
                </tr>
            </thead>
            <tbody>{rows_html}</tbody>
        </table>
    </div>
    """)

    st.markdown("<div style='height:16px'/>", unsafe_allow_html=True)

    _render_ticker_drilldown(basket_name, cfg, members_df, prices_df, rgb)
    _render_quality_section(cfg, q, prices_df, rgb)


@st.dialog("Ticker detail", width="large")
def _ticker_dialog(ticker: str, basket_name: str, prices_df: pd.DataFrame):
    from analytics import zscore_series  # local to avoid circular

    if ticker not in prices_df.columns:
        st.warning(f"No price data for {ticker}.")
        return
    series = prices_df[ticker].dropna().tail(252)
    if series.empty:
        st.warning(f"No price data for {ticker}.")
        return

    st.markdown(
        f'<div style="font-size:13px;color:#475569;letter-spacing:0.08em;text-transform:uppercase;margin-bottom:4px">'
        f'<span style="color:#e2e8f0;font-weight:700;font-size:17px;font-family:\'IBM Plex Mono\',monospace">{ticker}</span>'
        f' &nbsp;·&nbsp; in {basket_name} &nbsp;·&nbsp; last 12 months</div>',
        unsafe_allow_html=True,
    )

    # Price (rebased to 100)
    rebased = series / series.iloc[0] * 100
    price_fig = go.Figure()
    price_fig.add_trace(go.Scatter(
        x=rebased.index, y=rebased.values, mode="lines",
        line=dict(color="#f59e0b", width=1.6),
        hovertemplate="%{x|%b %d, %Y}<br>%{y:.1f} (rebased)<extra></extra>",
    ))
    price_fig.update_layout(
        **{**PLOTLY_LAYOUT,
           "height": 220,
           "margin": dict(l=40, r=20, t=10, b=30),
           "showlegend": False,
           "yaxis": {**PLOTLY_LAYOUT["yaxis"],
                     "title": dict(text="Price (rebased=100)", font=dict(color="#475569", size=9))}},
    )
    st.plotly_chart(price_fig, use_container_width=True, config={"displayModeBar": False})

    # Z-scores over time (5d + 20d) using the active z-window from session.
    full = prices_df[ticker].dropna()
    z_window = st.session_state.get("z_window", 252)
    z5 = zscore_series(full, 5, z_window).dropna().tail(252)
    z20 = zscore_series(full, 20, z_window).dropna().tail(252)
    z_fig = go.Figure()
    z_fig.add_trace(go.Scatter(x=z5.index, y=z5.values, mode="lines",
                                name="5d z", line=dict(color="#06b6d4", width=1.2)))
    z_fig.add_trace(go.Scatter(x=z20.index, y=z20.values, mode="lines",
                                name="20d z", line=dict(color="#a855f7", width=1.2)))
    z_fig.add_hline(y=0, line=dict(color="#334155", dash="dot", width=1))
    z_fig.update_layout(
        **{**PLOTLY_LAYOUT,
           "height": 200,
           "margin": dict(l=40, r=20, t=10, b=30),
           "yaxis": {**PLOTLY_LAYOUT["yaxis"],
                     "title": dict(text="Z-score (σ)", font=dict(color="#475569", size=9))}},
    )
    st.plotly_chart(z_fig, use_container_width=True, config={"displayModeBar": False})


def _render_ticker_drilldown(basket_name, cfg, members_df, prices_df, rgb):
    if prices_df is None or members_df.empty:
        return
    members = members_df["ticker"].tolist()
    sel_key = f"drilldown_{basket_name}"
    col_sel, col_btn = st.columns([3, 1])
    with col_sel:
        choice = st.selectbox(
            "Inspect ticker", ["— select —"] + members,
            key=sel_key, label_visibility="collapsed",
        )
    with col_btn:
        clicked = st.button("Open detail", key=f"drilldown_btn_{basket_name}",
                            use_container_width=True,
                            disabled=(choice == "— select —"))
    if clicked and choice != "— select —":
        _ticker_dialog(choice, basket_name, prices_df)


def _render_quality_section(cfg, q, prices_df, rgb):
    breadth = q.get("breadth_pct")
    dispersion = q.get("dispersion")
    mean_corr = q.get("mean_corr")

    if prices_df is None or not cfg.get("tickers"):
        return

    st.markdown('<div style="font-size:12px;font-weight:700;color:#64748b;text-transform:uppercase;letter-spacing:0.05em;border-bottom:1px solid #1e293b;padding-bottom:4px;margin-bottom:8px">Basket quality</div>', unsafe_allow_html=True)

    m_col, h_col = st.columns([1, 2])
    with m_col:
        b_txt = f"{breadth:.0f}%" if breadth is not None else "—"
        d_txt = f"{dispersion:.2f}%" if dispersion is not None else "—"
        c_txt = f"{mean_corr:.2f}" if mean_corr is not None else "—"
        st.html(f"""
        <div style="background:#080f1a;border:1px solid rgba({rgb},0.25);border-radius:8px;padding:14px 16px">
            <div style="display:flex;flex-direction:column;gap:14px">
                <div>
                    <div style="font-size:9px;color:#475569;font-weight:700;letter-spacing:0.08em;margin-bottom:4px">BREADTH · % &gt; 50D MA</div>
                    <div style="font-size:22px;font-weight:700;color:#e2e8f0;font-family:'IBM Plex Mono',monospace">{b_txt}</div>
                </div>
                <div>
                    <div style="font-size:9px;color:#475569;font-weight:700;letter-spacing:0.08em;margin-bottom:4px">DISPERSION · σ OF 20D RETURNS</div>
                    <div style="font-size:22px;font-weight:700;color:#e2e8f0;font-family:'IBM Plex Mono',monospace">{d_txt}</div>
                </div>
                <div>
                    <div style="font-size:9px;color:#475569;font-weight:700;letter-spacing:0.08em;margin-bottom:4px">MEAN PAIRWISE CORR · 60D</div>
                    <div style="font-size:22px;font-weight:700;color:#e2e8f0;font-family:'IBM Plex Mono',monospace">{c_txt}</div>
                </div>
            </div>
        </div>
        """)

    with h_col:
        corr = basket_correlation_matrix(prices_df, cfg["tickers"], window=60)
        if corr.empty:
            st.html(f'<div style="background:#080f1a;border:1px solid rgba({rgb},0.25);border-radius:8px;padding:14px 16px;color:#475569;font-size:13px">Not enough constituents for a correlation matrix.</div>')
            return
        fig = go.Figure(data=go.Heatmap(
            z=corr.values,
            x=corr.columns, y=corr.index,
            zmin=-1, zmax=1,
            colorscale=[
                [0.0, "#ef4444"],
                [0.5, "#0b1322"],
                [1.0, "#10b981"],
            ],
            colorbar=dict(thickness=8, len=0.7, tickfont=dict(size=9, color="#94a3b8")),
            hovertemplate="%{y} ↔ %{x}: %{z:.2f}<extra></extra>",
        ))
        height = max(220, 22 * len(corr) + 60)
        fig.update_layout(
            **{**PLOTLY_LAYOUT,
               "height": height,
               "margin": dict(l=40, r=20, t=20, b=40),
               "showlegend": False,
               "xaxis": dict(tickfont=dict(size=9, color="#94a3b8"),
                             showgrid=False, zeroline=False),
               "yaxis": dict(tickfont=dict(size=9, color="#94a3b8"),
                             showgrid=False, zeroline=False, autorange="reversed")},
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    st.markdown("<div style='height:16px'/>", unsafe_allow_html=True)
