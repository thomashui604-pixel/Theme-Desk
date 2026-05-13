"""Shared constants for Theme Desk."""

DEFAULT_BASKETS = {
    "Hyperscalers":      {"color": "#3b82f6", "tickers": ["MSFT", "AMZN", "GOOGL", "META", "ORCL"]},
    "Semis":             {"color": "#f59e0b", "tickers": ["NVDA", "AMD", "AVGO", "QCOM", "AMAT", "LRCX", "ASML"]},
    "SaaS":              {"color": "#8b5cf6", "tickers": ["CRM", "NOW", "SNOW", "DDOG", "MDB", "ZS", "HUBS"]},
    "AI Infrastructure": {"color": "#10b981", "tickers": ["ARM", "SMCI", "DELL", "NET", "CDNS"]},
    "Cybersecurity":     {"color": "#ef4444", "tickers": ["CRWD", "PANW", "FTNT", "ZS", "S", "OKTA"]},
}

PALETTE = [
    "#3b82f6", "#f59e0b", "#8b5cf6", "#10b981", "#ef4444",
    "#ec4899", "#06b6d4", "#84cc16", "#f97316", "#6366f1",
    "#14b8a6", "#a855f7", "#eab308", "#22c55e", "#0ea5e9",
]

Z_WINDOWS = {
    "63d  (Quarter)":     63,
    "126d (Semi-annual)": 126,
    "252d (Annual)":      252,
    "504d (Biennial)":    504,
}

FETCH_PERIOD = "5y"

INTERVALS = [
    ("1-Day",    1),
    ("5-Day",    5),
    ("20-Day",   20),
    ("3-Month",  63),
    ("6-Month",  126),
    ("12-Month", 252),
]
