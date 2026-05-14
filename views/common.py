"""Shared UI helpers: formatters, colors, plotly theme, CSS."""

import streamlit as st

CSS = """
<style>
[data-testid="stAppViewContainer"] { background: #030712; }
[data-testid="stSidebar"] { display: none !important; }
[data-testid="collapsedControl"] { display: none !important; }
.stTabs [data-baseweb="tab-list"] { background: transparent; border-bottom: 1px solid #1e293b; gap: 0; }
.stTabs [data-baseweb="tab"] {
    background: transparent !important; color: #475569 !important;
    padding: 12px 20px; border: none !important;
    font-size:14px; font-weight: 600; letter-spacing: 0.04em;
}
.stTabs [aria-selected="true"] { color: #f59e0b !important; border-bottom: 2px solid #f59e0b !important; }
.stTabs [data-baseweb="tab-panel"] { background: transparent; padding-top: 24px; }

div[data-testid="metric-container"] {
    background: #080f1a !important;
    border: 1px solid #1e293b !important;
    border-radius: 8px;
    padding: 14px 18px !important;
}
div[data-testid="metric-container"] label { color: #475569 !important; font-size:12px !important; letter-spacing: 0.06em; text-transform: uppercase; }
div[data-testid="metric-container"] [data-testid="stMetricValue"] { font-family: 'IBM Plex Mono', monospace; font-size:22px !important; }

h1, h2, h3, p, div { color: #e2e8f0; }
.stMarkdown p { color: #94a3b8; }

.stButton > button {
    background: #080f1a !important;
    border: 1px solid #1e293b !important;
    color: #94a3b8 !important;
    border-radius: 6px;
    font-size:13px;
    transition: all 0.15s;
}
.stButton > button:hover { border-color: #334155 !important; color: #e2e8f0 !important; }

[data-testid="stSelectbox"] > div > div { background: #080f1a !important; border: 1px solid #1e293b !important; }
.stTextInput > div > div > input { background: #080f1a !important; border: 1px solid #1e293b !important; color: #e2e8f0 !important; }
.stTextArea > div > div > textarea { background: #080f1a !important; border: 1px solid #1e293b !important; color: #e2e8f0 !important; }

[data-testid="stDataFrame"] { border: 1px solid #1e293b; border-radius: 8px; }
hr { border-color: #1e293b !important; }
.block-container { padding-top: 4rem; padding-bottom: 2rem; }
[data-testid="stHeader"] { background: transparent; }

.info-box {
    background: #080f1a;
    border: 1px solid #1e293b;
    border-radius: 6px;
    padding: 10px 16px;
    font-size:13px;
    color: #475569;
    margin-bottom: 14px;
}
.live-badge {
    display: inline-flex; align-items: center; gap: 6px;
    background: #052010; border: 1px solid rgba(16,185,129,0.2);
    border-radius: 5px; padding: 4px 12px;
    font-size:13px; color: #10b981; font-weight: 700;
}

/* Responsive: gracefully reflow multi-column layouts as viewport shrinks.
   Below 1200px, columns wrap with a 240px minimum per child — so 5-wide
   becomes 3-up, then 2-up, before collapsing to a single column on phone. */
@media (max-width: 1200px) {
    [data-testid="stHorizontalBlock"] {
        flex-wrap: wrap !important;
        row-gap: 8px;
    }
    [data-testid="stHorizontalBlock"] > [data-testid="column"] {
        flex: 1 1 240px !important;
        min-width: 240px !important;
    }
}
@media (max-width: 600px) {
    [data-testid="stHorizontalBlock"] > [data-testid="column"] {
        flex: 1 1 100% !important;
        min-width: 100% !important;
        margin-bottom: 8px;
    }
    .block-container { padding: 0.75rem !important; }
    .stTabs [data-baseweb="tab"] { padding: 10px 12px; font-size: 13px; }
}
</style>
"""


def inject_css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def _sign(v):
    return "▲" if v >= 0 else "▼"


def _color(v):
    return "#10b981" if v >= 0 else "#ef4444"


def pct_html(v, size=16):
    c = _color(v)
    return f'<span style="color:{c};font-family:\'IBM Plex Mono\',monospace;font-weight:700;font-size:{size}px">{_sign(v)} {abs(v):.2f}%</span>'


def z_html(v, size=16):
    if v is None:
        return '<span style="color:#334155">—</span>'
    c = _color(v)
    return f'<span style="color:{c};font-family:\'IBM Plex Mono\',monospace;font-weight:700;font-size:{size}px">{_sign(v)} {abs(v):.2f}σ</span>'


def _rgb(hex_color):
    h = hex_color.lstrip("#")
    return f"{int(h[0:2], 16)},{int(h[2:4], 16)},{int(h[4:6], 16)}"


PLOTLY_LAYOUT = dict(
    paper_bgcolor="#080f1a",
    plot_bgcolor="#080f1a",
    font=dict(color="#94a3b8", family="IBM Plex Mono, monospace", size=10),
    margin=dict(l=50, r=30, t=30, b=50),
    showlegend=True,
    legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor="#1e293b", borderwidth=1),
    xaxis=dict(gridcolor="#1e293b", zerolinecolor="#334155", linecolor="#1e293b"),
    yaxis=dict(gridcolor="#1e293b", zerolinecolor="#334155", linecolor="#1e293b"),
)
