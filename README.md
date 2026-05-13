# Theme Desk — Tech Basket Monitor

Live thematic momentum tracker for tech stocks. Deployed via Streamlit Community Cloud — no local installs required.

---

## Deploy in 5 minutes

### 1. Create a GitHub repo

Create a **new public (or private) repo** and add these two files:
```
your-repo/
├── app.py
└── requirements.txt
```

### 2. Deploy to Streamlit Community Cloud

1. Go to **[share.streamlit.io](https://share.streamlit.io)** and sign in with GitHub
2. Click **"New app"**
3. Select your repo, branch (`main`), and set the **Main file path** to `app.py`
4. Click **"Deploy"**

Streamlit will install dependencies and launch the app. You'll get a permanent URL like:
```
https://your-app-name.streamlit.app
```

That's it. Accessible from any browser, no Python or Node required.

---

## Saving your basket config

Streamlit Cloud's filesystem is ephemeral, so edits made in the app are lost on every redeploy or restart. To make ticker edits persist, configure the app to commit `baskets.json` back to this repo automatically.

### One-time setup

1. **Create a fine-grained Personal Access Token** at
   [github.com/settings/tokens?type=beta](https://github.com/settings/tokens?type=beta):
   - **Resource owner**: your account
   - **Repository access**: only this repo
   - **Permissions** → Repository → **Contents: Read and write**
   - Copy the token (`github_pat_…`)

2. **Add it to Streamlit Cloud secrets**:
   Streamlit app → Settings → Secrets → paste:
   ```toml
   [github]
   token  = "github_pat_..."
   repo   = "your-username/Tech-Thematic-Rotation-Dashboard-Test"
   branch = "main"              # optional, defaults to main
   path   = "baskets.json"      # optional
   ```

### How it works

Once configured, the **Quick-Add row at the top of every page** lets you paste tickers + pick a basket + hit `＋ Add`. The app:

1. Updates the basket in-session immediately
2. Commits the updated `baskets.json` to your repo via the GitHub API
3. Streamlit Cloud detects the commit and redeploys (~30s)

Without the token, quick-add still works but only for the current session.

---

## Features

| Feature | Details |
|---|---|
| **Live data** | yfinance pulls 2 years of adjusted daily closes, cached 5 min |
| **Basket cards** | Raw % returns (5d / 20d) per basket |
| **Overview tab** | Per-stock table with raw % + z-scores + signal (ACCEL / FADE / NEUTRAL) |
| **Rotation Map** | Z-scored scatter plot — 5d z (Y) vs 20d z (X), quadrant analysis |
| **Momentum Ranks** | Top/bottom 5 stocks by z-score across all baskets |
| **Z-score windows** | 63d / 126d / 252d / 504d (quarter / semi / annual / biennial) |
| **Basket management** | Create, rename, recolor, edit tickers, delete — all in sidebar |
| **Config export/import** | Download/upload `baskets.json` to persist across sessions |

---

## Local development (optional)

If you want to run it locally:

```bash
pip install streamlit yfinance pandas numpy plotly
streamlit run app.py
```
