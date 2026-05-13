"""Return and momentum computations."""

import numpy as np
import pandas as pd

from config import INTERVALS


def ret_pct(prices: pd.Series, lookback: int) -> float:
    n = len(prices)
    if n < lookback + 1:
        return 0.0
    cur = prices.iloc[-1]
    prev = prices.iloc[-(lookback + 1)]
    return ((cur - prev) / prev) * 100 if prev != 0 else 0.0


def rolling_return_series(prices: pd.Series, lookback: int) -> pd.Series:
    return prices.pct_change(lookback).dropna() * 100


def rolling_zscore(prices: pd.Series, lookback: int, z_window: int):
    daily_rets = prices.pct_change().dropna()
    if len(daily_rets) < z_window + lookback:
        return None
    # Strict out-of-sample baseline — exclude the days that make up the current return.
    historical = daily_rets.iloc[-(z_window + lookback): -lookback]
    daily_sigma = historical.std(ddof=1)
    if daily_sigma < 1e-8:
        return 0.0
    period_sigma = daily_sigma * np.sqrt(lookback) * 100
    period_ret = ret_pct(prices, lookback)
    return float(period_ret / period_sigma)


def ytd_return(prices: pd.Series) -> float:
    if prices.empty:
        return 0.0
    current_year = prices.index[-1].year
    prior_year = prices[prices.index.year < current_year]
    if prior_year.empty:
        return 0.0
    prev = prior_year.iloc[-1]
    cur = prices.iloc[-1]
    return ((cur - prev) / prev) * 100 if prev != 0 else 0.0


def ytd_trading_days(prices: pd.Series) -> int:
    if prices.empty:
        return 0
    current_year = prices.index[-1].year
    return int((prices.index.year == current_year).sum())


def build_stock_stats(prices_df: pd.DataFrame, baskets: dict, z_window: int) -> pd.DataFrame:
    primary = {}
    for name, cfg in baskets.items():
        for t in cfg["tickers"]:
            if t not in primary:
                primary[t] = name

    rows = []
    for ticker in prices_df.columns:
        s = prices_df[ticker].dropna()
        if len(s) < 25:
            continue
        ytd_days = ytd_trading_days(s)
        row = {
            "ticker":  ticker,
            "basket":  primary.get(ticker, "Other"),
            "price":   round(float(s.iloc[-1]), 2),
            "ret1d":   round(ret_pct(s, 1),  2),
            "ret5d":   round(ret_pct(s, 5),  2),
            "ret20d":  round(ret_pct(s, 20), 2),
            "z1d":     rolling_zscore(s, 1,  z_window),
            "z5d":     rolling_zscore(s, 5,  z_window),
            "z20d":    rolling_zscore(s, 20, z_window),
            "ret_ytd": round(ytd_return(s), 2),
            "z_ytd":   rolling_zscore(s, ytd_days, z_window) if ytd_days >= 2 else None,
        }
        for _, lb in INTERVALS:
            row[f"ret_{lb}"] = round(ret_pct(s, lb), 2)
            row[f"z_{lb}"]   = rolling_zscore(s, lb, z_window)
        rows.append(row)

    if not rows:
        cols = ["ticker", "basket", "price", "ret1d", "ret5d", "ret20d",
                "z1d", "z5d", "z20d", "ret_ytd", "z_ytd"]
        for _, lb in INTERVALS:
            cols += [f"ret_{lb}", f"z_{lb}"]
        return pd.DataFrame(columns=cols)
    return pd.DataFrame(rows)


def basket_stats(baskets: dict, stock_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for name, cfg in baskets.items():
        members = stock_df[stock_df["ticker"].isin(cfg["tickers"])]
        if members.empty:
            row = {"basket": name, "color": cfg["color"], "tickers": cfg["tickers"], "n": 0,
                   "avg1d": 0, "avg5d": 0, "avg20d": 0,
                   "avgZ1d": 0, "avgZ5d": 0, "avgZ20d": 0,
                   "avg_ret_ytd": 0, "avgZ_ytd": 0}
            for _, lb in INTERVALS:
                row[f"avg_ret_{lb}"] = 0
                row[f"avgZ_{lb}"] = 0
            rows.append(row)
            continue
        z_rows = members.dropna(subset=["z1d", "z5d", "z20d"])
        row = {
            "basket":  name,
            "color":   cfg["color"],
            "tickers": cfg["tickers"],
            "n":       len(members),
            "avg1d":   round(members["ret1d"].mean(),  2),
            "avg5d":   round(members["ret5d"].mean(),  2),
            "avg20d":  round(members["ret20d"].mean(), 2),
            "avgZ1d":  round(z_rows["z1d"].mean(),  3) if not z_rows.empty else 0,
            "avgZ5d":  round(z_rows["z5d"].mean(),  3) if not z_rows.empty else 0,
            "avgZ20d": round(z_rows["z20d"].mean(), 3) if not z_rows.empty else 0,
            "avg_ret_ytd": round(members["ret_ytd"].mean(), 2),
            "avgZ_ytd":    round(members["z_ytd"].dropna().mean(), 3) if not members["z_ytd"].dropna().empty else 0,
        }
        for _, lb in INTERVALS:
            ret_col = f"ret_{lb}"
            z_col = f"z_{lb}"
            row[f"avg_ret_{lb}"] = round(members[ret_col].mean(), 2)
            z_valid = members[z_col].dropna()
            row[f"avgZ_{lb}"] = round(z_valid.mean(), 3) if not z_valid.empty else 0
        rows.append(row)
    return pd.DataFrame(rows)
