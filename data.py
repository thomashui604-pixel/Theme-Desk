"""Market data fetching."""

import pandas as pd
import streamlit as st
import yfinance as yf

from config import FETCH_PERIOD


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
