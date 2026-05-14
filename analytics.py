"""Return and momentum computations."""

import numpy as np
import pandas as pd

from config import INTERVALS


def relative_panel(prices_df: pd.DataFrame, bench: pd.Series) -> pd.DataFrame:
    """Return a price-ratio panel: each ticker's price divided by the benchmark's.

    Returns and z-scores derived from this series are excess-of-benchmark.
    Normalized to start at 100 so the series looks like a regular price line.
    """
    if bench is None or bench.empty:
        return prices_df
    bench = bench.reindex(prices_df.index).ffill()
    ratio = prices_df.div(bench, axis=0)
    first_valid = ratio.apply(lambda s: s.first_valid_index())
    scale = pd.Series(
        {c: 100.0 / ratio[c].loc[first_valid[c]] if first_valid[c] is not None else 1.0
         for c in ratio.columns}
    )
    return ratio.mul(scale, axis=1)


def market_regime(spy: pd.Series) -> dict:
    """Classify market regime from SPY price series.

    Returns dict with label, color, and component metrics.
    """
    if spy is None or len(spy) < 200:
        return {"label": "—", "color": "#64748b", "detail": "insufficient data"}
    ma50 = spy.rolling(50).mean()
    ma200 = spy.rolling(200).mean()
    last = spy.iloc[-1]
    above_50 = last > ma50.iloc[-1]
    above_200 = last > ma200.iloc[-1]
    golden = ma50.iloc[-1] > ma200.iloc[-1]
    slope_20 = (ma50.iloc[-1] / ma50.iloc[-21] - 1) * 100 if len(ma50.dropna()) > 21 else 0.0

    score = int(above_50) + int(above_200) + int(golden) + int(slope_20 > 0)
    if score >= 3:
        label, color = "RISK-ON", "#10b981"
    elif score <= 1:
        label, color = "RISK-OFF", "#ef4444"
    else:
        label, color = "MIXED", "#f59e0b"

    detail = (
        f"SPY {'>' if above_50 else '<'} 50d, "
        f"{'>' if above_200 else '<'} 200d · "
        f"50d {'rising' if slope_20 > 0 else 'falling'} ({slope_20:+.1f}% / 20d)"
    )
    return {"label": label, "color": color, "detail": detail,
            "score": score, "slope_20": slope_20}


def ret_pct(prices: pd.Series, lookback: int) -> float:
    n = len(prices)
    if n < lookback + 1:
        return 0.0
    cur = prices.iloc[-1]
    prev = prices.iloc[-(lookback + 1)]
    return ((cur - prev) / prev) * 100 if prev != 0 else 0.0


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


def zscore_series(prices: pd.Series, lookback: int, z_window: int) -> pd.Series:
    """Vectorized rolling z-score time series.

    Mirrors rolling_zscore but returns a value at every timestamp. Baseline
    volatility at time t is computed over daily returns in
    [t - z_window - lookback, t - lookback), strictly out of sample.
    """
    daily_rets = prices.pct_change()
    daily_sigma = daily_rets.shift(lookback).rolling(z_window).std(ddof=1)
    period_sigma = daily_sigma * np.sqrt(lookback) * 100
    period_ret = prices.pct_change(lookback) * 100
    z = period_ret / period_sigma.where(period_sigma > 1e-8)
    return z


def rotation_trails(prices_df: pd.DataFrame, baskets: dict,
                    z_window: int, trail_len: int = 10,
                    lookbacks: tuple = (5, 20)) -> dict:
    """Per-basket trail of (z_short, z_long) over the last `trail_len` days."""
    short_lb, long_lb = lookbacks
    z_short = pd.DataFrame({
        t: zscore_series(prices_df[t].dropna(), short_lb, z_window)
        for t in prices_df.columns
    })
    z_long = pd.DataFrame({
        t: zscore_series(prices_df[t].dropna(), long_lb, z_window)
        for t in prices_df.columns
    })
    trails = {}
    for name, cfg in baskets.items():
        members = [t for t in cfg["tickers"] if t in z_short.columns]
        if not members:
            continue
        bs = z_short[members].mean(axis=1).dropna().tail(trail_len)
        bl = z_long[members].mean(axis=1).dropna().tail(trail_len)
        idx = bs.index.intersection(bl.index)
        if len(idx) == 0:
            continue
        trails[name] = pd.DataFrame({
            "date": idx,
            "z_short": bs.loc[idx].values,
            "z_long": bl.loc[idx].values,
        })
    return trails


def momentum_history(prices_df: pd.DataFrame, baskets: dict,
                     z_window: int, lookback: int = 20) -> dict:
    """Per-ticker and per-basket z-score time series for the given lookback.

    Returns:
      {
        "ticker_z": DataFrame (date × ticker) of z-score over `lookback`,
        "basket_z": DataFrame (date × basket) of mean z across constituents.
      }
    """
    ticker_z = pd.DataFrame({
        t: zscore_series(prices_df[t].dropna(), lookback, z_window)
        for t in prices_df.columns
    })
    basket_z = pd.DataFrame()
    for name, cfg in baskets.items():
        members = [t for t in cfg["tickers"] if t in ticker_z.columns]
        if not members:
            continue
        basket_z[name] = ticker_z[members].mean(axis=1)
    return {"ticker_z": ticker_z, "basket_z": basket_z}


def zscore_crossings(ticker_z: pd.DataFrame, baskets: dict) -> list:
    """Tickers whose z-score crossed zero between the last two trading days."""
    if ticker_z.empty or len(ticker_z) < 2:
        return []
    prev = ticker_z.iloc[-2]
    cur = ticker_z.iloc[-1]

    primary = {}
    for name, cfg in baskets.items():
        for t in cfg["tickers"]:
            primary.setdefault(t, name)

    crossings = []
    for ticker in ticker_z.columns:
        p, c = prev.get(ticker), cur.get(ticker)
        if pd.isna(p) or pd.isna(c):
            continue
        if p == 0 or c == 0:
            continue
        if (p < 0) != (c < 0):
            crossings.append({
                "ticker": ticker,
                "basket": primary.get(ticker, "Other"),
                "prev_z": float(p),
                "cur_z": float(c),
                "direction": "up" if c > 0 else "down",
            })
    # Strongest moves first.
    crossings.sort(key=lambda r: abs(r["cur_z"] - r["prev_z"]), reverse=True)
    return crossings


def leadership_flips(basket_z: pd.DataFrame, lookback_days: int = 5,
                     min_change: int = 3) -> list:
    """Baskets whose mean-z rank moved by at least `min_change` vs N days ago."""
    if basket_z.empty or len(basket_z) <= lookback_days:
        return []
    cur = basket_z.iloc[-1].dropna()
    prev = basket_z.iloc[-1 - lookback_days].dropna()
    common = cur.index.intersection(prev.index)
    if len(common) < 2:
        return []
    # Rank 1 = highest z.
    cur_rank = cur[common].rank(ascending=False, method="min").astype(int)
    prev_rank = prev[common].rank(ascending=False, method="min").astype(int)
    flips = []
    for name in common:
        delta = int(prev_rank[name]) - int(cur_rank[name])  # positive = moved up
        if abs(delta) >= min_change:
            flips.append({
                "basket": name,
                "prev_rank": int(prev_rank[name]),
                "cur_rank": int(cur_rank[name]),
                "delta": delta,
            })
    flips.sort(key=lambda r: abs(r["delta"]), reverse=True)
    return flips


def basket_quality(prices_df: pd.DataFrame, baskets: dict,
                   ma_window: int = 50, corr_window: int = 60,
                   disp_lookback: int = 20) -> dict:
    """Breadth, dispersion, and mean intra-basket correlation per basket."""
    result = {}
    for name, cfg in baskets.items():
        members = [t for t in cfg["tickers"] if t in prices_df.columns]
        breadth = None
        dispersion = None
        mean_corr = None

        if members:
            above = total = 0
            for t in members:
                s = prices_df[t].dropna()
                if len(s) < ma_window + 1:
                    continue
                ma = s.rolling(ma_window).mean().iloc[-1]
                if pd.isna(ma):
                    continue
                above += int(s.iloc[-1] > ma)
                total += 1
            if total:
                breadth = above / total * 100

        if len(members) >= 2:
            returns = []
            for t in members:
                s = prices_df[t].dropna()
                if len(s) >= disp_lookback + 1:
                    returns.append(ret_pct(s, disp_lookback))
            if len(returns) >= 2:
                dispersion = float(np.std(returns, ddof=1))

            rets = prices_df[members].pct_change().dropna().tail(corr_window)
            if not rets.empty and len(rets.columns) >= 2:
                corr = rets.corr()
                mask = np.triu(np.ones_like(corr, dtype=bool), k=1)
                vals = corr.values[mask]
                vals = vals[~np.isnan(vals)]
                if len(vals):
                    mean_corr = float(vals.mean())

        result[name] = {
            "breadth_pct": breadth,
            "dispersion": dispersion,
            "mean_corr": mean_corr,
        }
    return result


def basket_correlation_matrix(prices_df: pd.DataFrame, tickers: list,
                              window: int = 60) -> pd.DataFrame:
    members = [t for t in tickers if t in prices_df.columns]
    if len(members) < 2:
        return pd.DataFrame()
    rets = prices_df[members].pct_change().dropna().tail(window)
    if rets.empty:
        return pd.DataFrame()
    return rets.corr()


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
