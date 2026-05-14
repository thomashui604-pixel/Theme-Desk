"""Market data fetching."""

import time

import pandas as pd
import streamlit as st
import yfinance as yf

from config import FETCH_PERIOD


@st.cache_data(ttl=300, show_spinner=False)
def fetch_prices(tickers: tuple, period: str = FETCH_PERIOD,
                 max_retries: int = 2) -> pd.DataFrame:
    if not tickers:
        return pd.DataFrame()

    last_err = None
    for attempt in range(max_retries + 1):
        try:
            raw = yf.download(
                list(tickers), period=period, interval="1d",
                auto_adjust=True, progress=False, threads=True,
                timeout=20,
            )
            break
        except Exception as e:
            last_err = e
            if attempt < max_retries:
                time.sleep(1.5 * (attempt + 1))
            else:
                raw = pd.DataFrame()
    if last_err and (raw is None or raw.empty):
        return pd.DataFrame()

    if raw.empty:
        return pd.DataFrame()
    close = raw["Close"] if "Close" in raw.columns else raw
    if isinstance(close, pd.Series):
        close = close.to_frame(name=tickers[0])
    close = close.dropna(how="all").ffill()
    return close


@st.cache_data(ttl=300, show_spinner=False)
def fetch_ohlc(ticker: str, period: str = "1y") -> pd.DataFrame:
    """OHLC for a single ticker — used by the drill-down modal for candles."""
    if not ticker:
        return pd.DataFrame()
    try:
        df = yf.download(
            ticker, period=period, interval="1d",
            auto_adjust=True, progress=False,
            timeout=15,
        )
    except Exception:
        return pd.DataFrame()
    if df.empty:
        return pd.DataFrame()
    # yfinance may return columns as a MultiIndex when threads=True; flatten.
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    keep = [c for c in ("Open", "High", "Low", "Close") if c in df.columns]
    return df[keep].dropna(how="all")


def missing_tickers(requested: tuple, prices_df: pd.DataFrame) -> list:
    """Tickers that were requested but absent or all-NaN in the returned panel."""
    if prices_df.empty:
        return list(requested)
    missing = []
    for t in requested:
        if t not in prices_df.columns or prices_df[t].dropna().empty:
            missing.append(t)
    return missing
