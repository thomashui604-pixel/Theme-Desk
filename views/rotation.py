"""Rotation Map tab — RRG-style basket trails on a 5d / 20d z-score plane."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from analytics import rotation_trails
from views.common import PLOTLY_LAYOUT, _rgb, z_html


def render_rotation(b_stats: pd.DataFrame, prices_df: pd.DataFrame,
                    baskets: dict, z_window: int, z_label: str):
    st.markdown("""
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:4px">
        <div style="width:3px;height:20px;background:#f59e0b;border-radius:2px"></div>
        <span style="font-size:16px;font-weight:700;color:#e2e8f0">Thematic Rotation Map</span>
    </div>
    <div style="font-size:13px;color:#475569;margin-left:13px">RRG-style trails — each basket's path through (5d z, 20d z) over the last N days</div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="info-box">
        <strong style="color:#f59e0b">σ</strong>&nbsp;
        Axes show <strong style="color:#94a3b8">z-scores</strong> — each basket's return divided by its own {z_label.split("(")[0].strip()} rolling std dev.
        Each basket shows where it stood <strong style="color:#94a3b8">20 trading days ago</strong> (faint dot) connected to <strong style="color:#94a3b8">today</strong> (bright dot).
        Direction matters more than location.
    </div>
    """, unsafe_allow_html=True)

    q1, q2, q3, q4 = st.columns(4)
    quadrants = [
        ("LAGGING · DECEL", "5d z < 0, 20d z < 0", "#ef4444"),
        ("LAGGING · ACCEL", "5d z > 0, 20d z < 0", "#f59e0b"),
        ("LEADING · DECEL", "5d z < 0, 20d z > 0", "#8b5cf6"),
        ("LEADING · ACCEL", "5d z > 0, 20d z > 0", "#10b981"),
    ]
    for col, (q, desc, color) in zip([q1, q2, q3, q4], quadrants):
        col.markdown(f"""
        <div style="background:#080f1a;border:1px solid #1e293b;border-radius:6px;padding:6px 8px;font-size:9px">
            <span style="color:{color};font-weight:700">{q}</span><br>
            <span style="color:#475569">{desc}</span>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height:16px'/>", unsafe_allow_html=True)

    if b_stats.empty or prices_df.empty:
        st.info("No basket data available.")
        return

    TRAIL_DAYS = 20
    trails = rotation_trails(prices_df, baskets, z_window, trail_len=TRAIL_DAYS + 1)

    fig = go.Figure()
    for x0, x1, y0, y1, col in [
        (-5, 0, -5, 0, "rgba(239,68,68,0.04)"),
        ( 0, 5, -5, 0, "rgba(245,158,11,0.04)"),
        (-5, 0,  0, 5, "rgba(139,92,246,0.04)"),
        ( 0, 5,  0, 5, "rgba(16,185,129,0.04)"),
    ]:
        fig.add_shape(type="rect", x0=x0, x1=x1, y0=y0, y1=y1,
                      fillcolor=col, line_width=0, layer="below")

    # Compute axis range from data so trails always fit.
    all_x, all_y = [], []
    for df in trails.values():
        all_x.extend(df["z_short"].dropna().tolist())
        all_y.extend(df["z_long"].dropna().tolist())
    if all_x:
        pad = 0.6
        x_range = [min(min(all_x) - pad, -2.5), max(max(all_x) + pad, 2.5)]
        y_range = [min(min(all_y) - pad, -2.5), max(max(all_y) + pad, 2.5)]
    else:
        x_range = [-3, 3]
        y_range = [-3, 3]

    for _, row in b_stats.iterrows():
        name = row["basket"]
        color = row["color"]
        rgb = _rgb(color)
        if name not in trails or trails[name].empty:
            continue
        path = trails[name].dropna(subset=["z_short", "z_long"])
        if len(path) < 2:
            continue

        # Keep only the endpoints: 20 days ago and today.
        endpoints = path.iloc[[0, -1]]
        xs = endpoints["z_short"].tolist()
        ys = endpoints["z_long"].tolist()

        # Connecting line — past → present
        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode="lines",
            line=dict(color=f"rgba({rgb},0.5)", width=1.5),
            hoverinfo="skip",
            showlegend=False,
        ))

        # Past marker (faint, small)
        past_date = endpoints["date"].iloc[0].strftime("%b %d")
        fig.add_trace(go.Scatter(
            x=[xs[0]], y=[ys[0]], mode="markers",
            marker=dict(size=7, color=f"rgba({rgb},0.35)",
                        line=dict(color=color, width=1)),
            hovertemplate=(
                f"<b style='color:{color}'>{name}</b><br>"
                f"{past_date}<br>"
                "5d z: %{x:.2f}σ<br>"
                "20d z: %{y:.2f}σ<extra></extra>"
            ),
            showlegend=False,
        ))

        # Current marker (bright, larger) + label
        label = name[:7] + "…" if len(name) > 7 else name
        fig.add_trace(go.Scatter(
            x=[xs[-1]], y=[ys[-1]], mode="markers+text",
            text=[label], textposition="top center",
            textfont=dict(color=color, size=12, family="IBM Plex Mono"),
            marker=dict(size=14, color=color,
                        line=dict(color="#080f1a", width=2)),
            hovertemplate=(
                f"<b style='color:{color}'>{name}</b><br>"
                "today<br>"
                "5d z: %{x:.2f}σ<br>"
                "20d z: %{y:.2f}σ<extra></extra>"
            ),
            showlegend=False,
        ))

    fig.add_hline(y=0,  line=dict(color="#334155", dash="dash", width=1))
    fig.add_vline(x=0,  line=dict(color="#334155", dash="dash", width=1))
    fig.add_hline(y=1,  line=dict(color="#1e293b", dash="dot",  width=1))
    fig.add_hline(y=-1, line=dict(color="#1e293b", dash="dot",  width=1))
    fig.add_vline(x=1,  line=dict(color="#1e293b", dash="dot",  width=1))
    fig.add_vline(x=-1, line=dict(color="#1e293b", dash="dot",  width=1))

    layout = dict(**PLOTLY_LAYOUT)
    layout.update(
        height=480, showlegend=False,
        xaxis=dict(**PLOTLY_LAYOUT["xaxis"], title=dict(text="5d z-score (σ)", font=dict(color="#475569", size=10)), range=x_range),
        yaxis=dict(**PLOTLY_LAYOUT["yaxis"], title=dict(text="20d z-score (σ)", font=dict(color="#475569", size=10)), range=y_range),
    )
    fig.update_layout(**layout)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    # Rotation summary table (unchanged — uses today's snapshot only)
    st.markdown("""
    <div style="font-size:9px;font-weight:700;color:#94a3b8;letter-spacing:0.12em;text-transform:uppercase;margin-bottom:4px">Rotation Summary</div>
    """, unsafe_allow_html=True)

    def sort_key(row):
        return row["avgZ20d"] + (row["avgZ5d"] - row["avgZ20d"])
    sorted_rows = b_stats.iloc[b_stats.apply(sort_key, axis=1).argsort()[::-1]]

    rows_html = ""
    for _, row in sorted_rows.iterrows():
        color = row["color"]
        tickers_str = ", ".join(row["tickers"][:8]) + (f" +{len(row['tickers']) - 8}" if len(row["tickers"]) > 8 else "")
        rows_html += f"""
        <tr style="border-bottom:1px solid #0f172a">
            <td style="padding:10px 14px">
                <div style="display:flex;align-items:center;gap:10px">
                    <div style="width:4px;height:32px;background:{color};border-radius:2px;flex-shrink:0"></div>
                    <div>
                        <div style="font-weight:700;font-size:16px;color:#e2e8f0">{row["basket"]}</div>
                        <div style="font-size:12px;color:#475569;margin-top:2px">{tickers_str}</div>
                    </div>
                </div>
            </td>
            <td style="padding:10px 14px;text-align:right"><div style="font-size:9px;color:#475569">5d σ</div>{z_html(row["avgZ5d"])}</td>
            <td style="padding:10px 14px;text-align:right"><div style="font-size:9px;color:#475569">20d σ</div>{z_html(row["avgZ20d"])}</td>
        </tr>"""

    st.html(f"""
    <div style="background:#080f1a;border:1px solid #1e293b;border-radius:8px;overflow:hidden">
        <table style="width:100%;border-collapse:collapse;font-size:14px">
            <tbody>{rows_html}</tbody>
        </table>
    </div>
    """)
