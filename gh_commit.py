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


def _fetch_sha(url: str, headers: dict, ref: str) -> "str | None":
    try:
        r = requests.get(url, headers=headers, params={"ref": ref}, timeout=10)
    except requests.RequestException:
        return None
    if not r.ok:
        return None
    try:
        return r.json().get("sha")
    except ValueError:  # JSONDecodeError subclass — non-JSON body
        return None


def commit_baskets(baskets: dict, message: str | None = None) -> tuple[bool, str]:
    """Returns (ok, detail). detail is 'not_configured', 'ok', or an error string.

    Retries once on 409 (stale sha) — happens when two commits race, e.g. quick-add
    and a Settings save firing nearly simultaneously.
    """
    cfg = _config()
    if not cfg:
        return False, "not_configured"

    headers = {
        "Authorization": f"Bearer {cfg['token']}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    url = f"{API}/repos/{cfg['repo']}/contents/{cfg['path']}"
    payload = json.dumps(baskets, indent=2) + "\n"
    content_b64 = base64.b64encode(payload.encode("utf-8")).decode("ascii")

    for attempt in range(2):  # initial + one retry on stale-sha
        sha = _fetch_sha(url, headers, cfg["branch"])
        body = {
            "message": message or "Update baskets.json from app",
            "content": content_b64,
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
        if r.status_code == 409 and attempt == 0:
            continue  # sha went stale — fetch fresh and retry once
        return False, f"http {r.status_code}: {r.text[:200]}"
    return False, "exhausted retries"
