# Deferred Ideas

Items considered but not built during the phase 1–6 redesign. Notes are for
the future me / future Claude — feel free to scratch out, reorder, or add.

## Analytics

- **Sharpe as alternative momentum metric**
  Add a Settings toggle "Momentum metric: z-score / Sharpe". Sharpe over a 63d
  window per ticker, then mean across basket. Threads through every view that
  reads `z*` columns, so it's a non-trivial swap. Skipped in phase 5 to keep
  scope tight.

- **Z-score acceleration (2nd derivative)**
  Slope of the 20d z-score over the last 5 days. Highlights baskets that are
  not just leading but accelerating their lead.

- **Mean-reversion signals**
  Tickers whose z-score is extreme (|z| > 2) AND whose ranking has held for
  N days. Pair with breadth: extreme + low breadth = exhaustion candidate.

- **Volatility regime per basket**
  Realized 20d vol; compare to 252d baseline. Show "vol regime" tag alongside
  the existing momentum read.

## Data / persistence

- **External DB for true daily history**
  Postgres (Supabase / Neon) or Turso/libsql. Would unlock real time-series
  features that survive Streamlit Cloud restarts:
  - Alert journal (basket / ticker thresholds with notes)
  - Annotations on the rotation trail ("I bought NVDA here")
  - Long-horizon backtest of basket signals
  Replace the on-the-fly history reconstruction with stored snapshots only
  when there's actually a feature that needs > 5y or needs user-event data.

- **Alerts**
  "Flag when basket 20d z > 1.5" or "ticker breadth drops below 30%". Needs
  persistence to dedupe fires across reloads. Could be email or just a feed
  on the Today tab.

- **Notes / journal**
  Per-basket and per-ticker free-text notes shown on drill-down. Stored
  alongside alerts.

- **Snapshot-to-git** (no DB)
  At end of each session, append today's basket snapshot to a CSV in the
  repo and `git commit && git push` via deploy key. Free, ugly, works.
  Useful only if external DB is rejected.

## UI

- **Backtest / lookback mode**
  Slider that rewinds the "as of" date — recompute every view as it would
  have looked N days ago. Sanity-check the signal against history.

- **Drag-and-drop basket editor**
  Reorder baskets, drag tickers between baskets. Streamlit doesn't support
  this natively — would need a custom component or move off Streamlit.

- **Per-basket sparkline of breadth + dispersion over time**
  Already have the math in `basket_quality`; just need to compute it
  historically and plot.

- **Keyboard shortcuts**
  Arrow keys between periods, `b` to toggle benchmark, etc. Requires a
  small JS injection.

- **Polish for the ticker drill-down modal**
  Show basket-relative performance line (ticker ÷ basket mean) — exists
  in spec but skipped.

## Robustness

- **Auth + multi-user**
  Streamlit Cloud has SSO but the app doesn't use it. Per-user baskets
  would need either DB-backed config keyed on user ID, or per-deploy
  app instance.

- **Better empty-data handling**
  Currently shows a top-of-page warning. Could mute empty tickers in
  basket cards or strike them through in the constituent table.
