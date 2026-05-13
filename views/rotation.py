"""Rotation Map tab."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from views.common import PLOTLY_LAYOUT, _rgb, z_html


def render_rotation(b_stats: pd.DataFrame, z_label: str):
    st.markdown("""
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:4px">
        <div style="width:3px;height:20px;background:#f59e0b;border-radius:2px"></div>
        <span style="font-size:13px;font-weight:700;color:#e2e8f0">Thematic Rotation Map</span>
    </div>
    <div style="font-size:11px;color:#475569;margin-left:13px">Z-scored returns — each basket normalized by its own rolling vol</div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="info-box">
        <strong style="color:#f59e0b">σ</strong>&nbsp;
        Axes show <strong style="color:#94a3b8">z-scores</strong> — each basket's return divided by its own {z_label.split("(")[0].strip()} rolling std dev.
        Equal distances from origin are genuinely comparable across baskets regardless of vol regime.
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
        <div style="background:#080f1a;border:1px solid #1e293b;border-radius:6px;padding:8px 12px;font-size:10px">
            <span style="color:{color};font-weight:700">{q}</span><br>
            <span style="color:#475569">{desc}</span>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height:16px'/>", unsafe_allow_html=True)

    if b_stats.empty:
        st.info("No basket data available.")
        return

    fig = go.Figure()
    for x0, x1, y0, y1, col in [
        (-5, 0, -5,  0, "rgba(239,68,68,0.04)"),
        ( 0, 5, -5,  0, "rgba(245,158,11,0.04)"),
        (-5, 0,  0,  5, "rgba(139,92,246,0.04)"),
        ( 0, 5,  0,  5, "rgba(16,185,129,0.04)"),
    ]:
        fig.add_shape(type="rect", x0=x0, x1=x1, y0=y0, y1=y1,
                      fillcolor=col, line_width=0, layer="below")

    for _, row in b_stats.iterrows():
        x, y = row["avgZ5d"], row["avgZ20d"]
        color = row["color"]
        label = row["basket"][:7] + "…" if len(row["basket"]) > 7 else row["basket"]
        fig.add_trace(go.Scatter(
            x=[x], y=[y], mode="markers+text", text=[label],
            textposition="middle center",
            textfont=dict(color=color, size=9, family="IBM Plex Mono"),
            marker=dict(
                size=48,
                color=f"rgba({_rgb(color)},0.13)",
                line=dict(color=color, width=1.5),
            ),
            hovertemplate=(
                f"<b style='color:{color}'>{row['basket']}</b><br>"
                f"5d z: {'+' if x >= 0 else ''}{x:.2f}σ<br>"
                f"20d z: {'+' if y >= 0 else ''}{y:.2f}σ<extra></extra>"
            ),
            name=row["basket"],
        ))

    fig.add_hline(y=0,  line=dict(color="#334155", dash="dash", width=1))
    fig.add_vline(x=0,  line=dict(color="#334155", dash="dash", width=1))
    fig.add_hline(y=1,  line=dict(color="#1e293b", dash="dot",  width=1))
    fig.add_hline(y=-1, line=dict(color="#1e293b", dash="dot",  width=1))
    fig.add_vline(x=1,  line=dict(color="#1e293b", dash="dot",  width=1))
    fig.add_vline(x=-1, line=dict(color="#1e293b", dash="dot",  width=1))

    layout = dict(**PLOTLY_LAYOUT)
    layout.update(
        height=420, showlegend=False,
        xaxis=dict(**PLOTLY_LAYOUT["xaxis"], title=dict(text="5d z-score (σ)", font=dict(color="#475569", size=10))),
        yaxis=dict(**PLOTLY_LAYOUT["yaxis"], title=dict(text="20d z-score (σ)", font=dict(color="#475569", size=10))),
    )
    fig.update_layout(**layout)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

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
                        <div style="font-weight:700;font-size:13px;color:#e2e8f0">{row["basket"]}</div>
                        <div style="font-size:10px;color:#475569;margin-top:2px">{tickers_str}</div>
                    </div>
                </div>
            </td>
            <td style="padding:10px 14px;text-align:right"><div style="font-size:9px;color:#475569">5d σ</div>{z_html(row["avgZ5d"])}</td>
            <td style="padding:10px 14px;text-align:right"><div style="font-size:9px;color:#475569">20d σ</div>{z_html(row["avgZ20d"])}</td>
        </tr>"""

    st.html(f"""
    <div style="background:#080f1a;border:1px solid #1e293b;border-radius:8px;overflow:hidden">
        <table style="width:100%;border-collapse:collapse;font-size:12px">
            <tbody>{rows_html}</tbody>
        </table>
    </div>
    """)
