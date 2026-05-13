"""Market data fetching and SQLite history."""

import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st
import yfinance as yf

from config import FETCH_PERIOD

DB_PATH = Path(__file__).parent / "history.db"


@st.cache_data(ttl=300, show_spinner=False)
def fetch_prices(tickers: tuple, period: str = FETCH_PERIOD) -> pd.DataFrame:
    if not tickers:
        return pd.DataFrame()
    raw = yf.download(
        list(tickers), period=period, interval="1d",
        auto_adjust=True, progress=False, threads=True,
    )
    if raw.empty:
        return pd.DataFrame()
    close = raw["Close"] if "Close" in raw.columns else raw
    if isinstance(close, pd.Series):
        close = close.to_frame(name=tickers[0])
    close = close.dropna(how="all").ffill()
    return close


# ── SQLite history ─────────────────────────────────────────────────────────────
_SCHEMA = """
CREATE TABLE IF NOT EXISTS ticker_daily (
    date TEXT NOT NULL,
    ticker TEXT NOT NULL,
    close REAL,
    ret_1d REAL,
    ret_5d REAL,
    ret_20d REAL,
    z_5d REAL,
    z_20d REAL,
    PRIMARY KEY (date, ticker)
);
CREATE TABLE IF NOT EXISTS basket_daily (
    date TEXT NOT NULL,
    basket TEXT NOT NULL,
    mean_ret_20d REAL,
    mean_z_20d REAL,
    breadth_above_50dma REAL,
    dispersion REAL,
    PRIMARY KEY (date, basket)
);
"""


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(_SCHEMA)
    return conn


def snapshot_today(stock_df: pd.DataFrame, basket_df: pd.DataFrame,
                   prices_df: pd.DataFrame) -> None:
    """Idempotent upsert of today's per-ticker and per-basket stats."""
    if stock_df.empty or prices_df.empty:
        return
    snapshot_date = prices_df.index[-1].strftime("%Y-%m-%d")
    try:
        with _connect() as conn:
            ticker_rows = [
                (snapshot_date, r["ticker"], r["price"],
                 r["ret1d"], r["ret5d"], r["ret20d"],
                 r["z5d"], r["z20d"])
                for _, r in stock_df.iterrows()
            ]
            conn.executemany(
                "INSERT OR REPLACE INTO ticker_daily "
                "(date, ticker, close, ret_1d, ret_5d, ret_20d, z_5d, z_20d) "
                "VALUES (?,?,?,?,?,?,?,?)",
                ticker_rows,
            )
            basket_rows = [
                (snapshot_date, r["basket"], r["avg20d"], r["avgZ20d"], None, None)
                for _, r in basket_df.iterrows()
            ]
            conn.executemany(
                "INSERT OR REPLACE INTO basket_daily "
                "(date, basket, mean_ret_20d, mean_z_20d, breadth_above_50dma, dispersion) "
                "VALUES (?,?,?,?,?,?)",
                basket_rows,
            )
    except Exception:
        # Snapshotting is best-effort; never break the UI on a write failure.
        pass


def load_history(days: int = 90) -> dict:
    """Return {'ticker': df, 'basket': df} of recent history. Empty frames if no DB."""
    if not DB_PATH.exists():
        return {"ticker": pd.DataFrame(), "basket": pd.DataFrame()}
    try:
        with _connect() as conn:
            cutoff = (pd.Timestamp.today().normalize() - pd.Timedelta(days=days)).strftime("%Y-%m-%d")
            t = pd.read_sql_query(
                "SELECT * FROM ticker_daily WHERE date >= ? ORDER BY date",
                conn, params=(cutoff,), parse_dates=["date"],
            )
            b = pd.read_sql_query(
                "SELECT * FROM basket_daily WHERE date >= ? ORDER BY date",
                conn, params=(cutoff,), parse_dates=["date"],
            )
        return {"ticker": t, "basket": b}
    except Exception:
        return {"ticker": pd.DataFrame(), "basket": pd.DataFrame()}
