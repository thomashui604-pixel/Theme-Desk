"""Commit baskets.json back to GitHub via the contents API.

Configuration lives in Streamlit secrets:

    [github]
    token  = "ghp_..."                                  # fine-grained PAT, contents: write
    repo   = "owner/repository-name"
    branch = "main"                                     # optional, defaults to main
    path   = "baskets.json"                             # optional, defaults to baskets.json
"""

import base64
import json

import requests
import streamlit as st

API = "https://api.github.com"


def _config() -> dict | None:
    try:
        gh = st.secrets.get("github")
    except (AttributeError, FileNotFoundError):
        return None
    if not gh:
        return None
    token = gh.get("token")
    repo = gh.get("repo")
    if not token or not repo:
        return None
    return {
        "token":  token,
        "repo":   repo,
        "branch": gh.get("branch", "main"),
        "path":   gh.get("path", "baskets.json"),
    }


def is_configured() -> bool:
    return _config() is not None


def commit_baskets(baskets: dict, message: str | None = None) -> tuple[bool, str]:
    """Returns (ok, detail). detail is 'not_configured', 'ok', or an error string."""
    cfg = _config()
    if not cfg:
        return False, "not_configured"

    headers = {
        "Authorization": f"Bearer {cfg['token']}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    url = f"{API}/repos/{cfg['repo']}/contents/{cfg['path']}"

    # Look up current file sha (required for updates; absent for new files).
    try:
        r = requests.get(url, headers=headers,
                         params={"ref": cfg["branch"]}, timeout=10)
    except requests.RequestException as e:
        return False, f"network: {e}"
    sha = r.json().get("sha") if r.ok else None

    payload = json.dumps(baskets, indent=2) + "\n"
    body = {
        "message": message or "Update baskets.json from app",
        "content": base64.b64encode(payload.encode("utf-8")).decode("ascii"),
        "branch": cfg["branch"],
    }
    if sha:
        body["sha"] = sha

    try:
        r = requests.put(url, headers=headers, json=body, timeout=15)
    except requests.RequestException as e:
        return False, f"network: {e}"
    if r.ok:
        return True, "ok"
    return False, f"http {r.status_code}: {r.text[:200]}"
