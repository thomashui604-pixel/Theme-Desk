"""Settings tab — basket CRUD, import/export, diagnostics."""

import json
from pathlib import Path

import streamlit as st

from config import DEFAULT_BASKETS, PALETTE
from gh_commit import commit_baskets, is_configured
from views.common import _rgb

BASKETS_PATH = Path(__file__).resolve().parent.parent / "baskets.json"


def load_default_baskets() -> dict:
    if BASKETS_PATH.exists():
        try:
            with open(BASKETS_PATH) as f:
                return json.load(f)
        except Exception:
            pass
    return {k: dict(v) for k, v in DEFAULT_BASKETS.items()}


def save_baskets() -> None:
    try:
        with open(BASKETS_PATH, "w") as f:
            json.dump(st.session_state.baskets, f, indent=2)
    except Exception:
        pass


def persist(commit_message: str, success_label: str = "Saved") -> None:
    """Write locally, then commit to GitHub if configured. Uses st.toast so
    the notification survives the st.rerun() (and any auto-redeploy) that
    each settings handler triggers.
    """
    save_baskets()
    if is_configured():
        ok, detail = commit_baskets(st.session_state.baskets, message=commit_message)
        if ok:
            st.toast(f"{success_label} · committed to repo (redeploy ~30s)", icon="✅")
        else:
            st.toast(f"{success_label} locally · commit failed: {detail}", icon="⚠️")
    else:
        st.toast(f"{success_label} (session only — add [github] secret)", icon="ℹ️")


def render_settings():
    col_left, col_right = st.columns([1, 1], gap="large")

    with col_left:
        st.markdown('<div style="font-size:13px;font-weight:700;color:#64748b;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:10px">Theme Baskets</div>', unsafe_allow_html=True)

        for name, cfg in st.session_state.baskets.items():
            col_sel, col_edit = st.columns([5, 1])
            with col_sel:
                is_sel = st.session_state.selected_basket == name
                if st.button(f"{'◆ ' if is_sel else '◇ '}{name}", key=f"sel_{name}", use_container_width=True):
                    st.session_state.selected_basket = name
                    st.session_state.editing_basket = None
            with col_edit:
                if st.button("✎", key=f"edit_{name}", help=f"Edit {name}"):
                    st.session_state.editing_basket = name

        st.markdown("<div style='height:8px'/>", unsafe_allow_html=True)

        if st.button("＋ New Basket", use_container_width=True, key="new_basket_btn"):
            st.session_state.editing_basket = "__new__"

        editing = st.session_state.editing_basket
        if editing:
            st.divider()
            is_new = editing == "__new__"
            existing = {} if is_new else st.session_state.baskets.get(editing, {})

            st.markdown(
                f'<div style="font-size:13px;font-weight:700;color:#e2e8f0;margin-bottom:12px">{"New Basket" if is_new else f"Edit · {editing}"}</div>',
                unsafe_allow_html=True,
            )

            with st.form(key="basket_form", clear_on_submit=True):
                new_name = st.text_input("Name", value="" if is_new else editing, placeholder="e.g. Fintech, EV…")
                color_idx = PALETTE.index(existing.get("color", PALETTE[0])) if existing.get("color") in PALETTE else 0
                new_color = st.selectbox("Color", PALETTE, index=color_idx, format_func=lambda c: c)
                tickers_default = ", ".join(existing.get("tickers", []))
                tickers_raw = st.text_area("Tickers (comma-separated)", value=tickers_default, height=80, placeholder="MSFT, AAPL, NVDA…")

                col_save, col_cancel = st.columns(2)
                with col_save:
                    submitted = st.form_submit_button("Save", use_container_width=True, type="primary")
                with col_cancel:
                    cancelled = st.form_submit_button("Cancel", use_container_width=True)

                if submitted:
                    name_clean = new_name.strip()
                    ticker_list = [t.strip().upper() for t in tickers_raw.replace("\n", ",").split(",") if t.strip()]
                    ticker_unique = list(dict.fromkeys(ticker_list))
                    dupes_removed = len(ticker_list) - len(ticker_unique)

                    if not name_clean:
                        st.error("Name is required")
                    elif not ticker_unique:
                        st.error("Add at least one ticker")
                    elif is_new and name_clean in st.session_state.baskets:
                        st.error("Name already exists")
                    else:
                        if dupes_removed:
                            st.warning(f"Removed {dupes_removed} duplicate ticker{'s' if dupes_removed > 1 else ''}")
                        if not is_new and editing != name_clean:
                            st.session_state.baskets.pop(editing)
                            if st.session_state.selected_basket == editing:
                                st.session_state.selected_basket = name_clean
                        st.session_state.baskets[name_clean] = {"color": new_color, "tickers": ticker_unique}
                        if is_new:
                            st.session_state.selected_basket = name_clean
                        st.session_state.editing_basket = None
                        verb = "Created" if is_new else "Updated"
                        persist(f"{verb} basket {name_clean}", f"{verb} {name_clean}")
                        st.rerun()

                if cancelled:
                    st.session_state.editing_basket = None
                    st.rerun()

            if not is_new:
                if st.button(f"🗑 Delete '{editing}'", key="delete_basket", use_container_width=True):
                    deleted = editing
                    del st.session_state.baskets[editing]
                    remaining = list(st.session_state.baskets.keys())
                    st.session_state.selected_basket = remaining[0] if remaining else None
                    st.session_state.editing_basket = None
                    persist(f"Delete basket {deleted}", f"Deleted {deleted}")
                    st.rerun()

    with col_right:
        st.markdown('<div style="font-size:13px;font-weight:700;color:#64748b;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:8px">Config</div>', unsafe_allow_html=True)

        basket_json = json.dumps(st.session_state.baskets, indent=2)
        st.download_button("⬇ Export baskets.json", data=basket_json, file_name="baskets.json", mime="application/json", use_container_width=True)

        uploaded = st.file_uploader("⬆ Import baskets.json", type="json", label_visibility="collapsed")
        if uploaded:
            try:
                imported = json.load(uploaded)
                st.session_state.baskets = imported
                st.session_state.selected_basket = list(imported.keys())[0]
                persist("Import baskets.json from upload", "Imported")
                st.rerun()
            except Exception as e:
                st.error(f"Invalid file: {e}")

        st.markdown("<div style='height:24px'/>", unsafe_allow_html=True)
        st.markdown('<div style="font-size:13px;font-weight:700;color:#64748b;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:10px">Ticker Diagnostics</div>', unsafe_allow_html=True)

        baskets = st.session_state.baskets
        has_issues = False
        diag_html = ""

        for name, cfg in baskets.items():
            seen = {}
            for t in cfg["tickers"]:
                seen[t] = seen.get(t, 0) + 1
            dupes = {t: c for t, c in seen.items() if c > 1}
            if dupes:
                has_issues = True
                color = cfg.get("color", "#64748b")
                for t, c in dupes.items():
                    diag_html += f"""
                    <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px">
                        <span style="color:#ef4444;font-size:14px;font-weight:900">✕</span>
                        <span style="font-size:13px;color:#e2e8f0;font-family:'IBM Plex Mono',monospace;font-weight:700">{t}</span>
                        <span style="font-size:12px;color:#94a3b8">repeated {c}× in</span>
                        <span style="background:rgba({_rgb(color)},0.13);color:{color};border:1px solid rgba({_rgb(color)},0.27);border-radius:3px;padding:1px 6px;font-size:9px;font-weight:700">{name}</span>
                    </div>"""

        ticker_to_baskets = {}
        for name, cfg in baskets.items():
            for t in set(cfg["tickers"]):
                ticker_to_baskets.setdefault(t, []).append(name)
        cross_dupes = {t: bs for t, bs in ticker_to_baskets.items() if len(bs) > 1}

        if cross_dupes:
            for t, bs in sorted(cross_dupes.items()):
                tags = ""
                for b in bs:
                    color = baskets[b].get("color", "#64748b")
                    tags += f'<span style="background:rgba({_rgb(color)},0.13);color:{color};border:1px solid rgba({_rgb(color)},0.27);border-radius:3px;padding:1px 6px;font-size:9px;font-weight:700">{b}</span> '
                diag_html += f"""
                <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;flex-wrap:wrap">
                    <span style="color:#64748b;font-size:13px">·</span>
                    <span style="font-size:13px;color:#e2e8f0;font-family:'IBM Plex Mono',monospace;font-weight:700">{t}</span>
                    <span style="font-size:12px;color:#64748b">in {len(bs)} baskets:</span>
                    {tags}
                </div>"""

        if has_issues:
            st.html(f'<div style="background:#080f1a;border:1px solid #1e293b;border-radius:8px;padding:16px">{diag_html}</div>')
        else:
            st.html('<div style="background:#080f1a;border:1px solid #1e293b;border-radius:8px;padding:16px;display:flex;align-items:center;gap:8px"><span style="color:#10b981;font-size:14px;font-weight:900">✓</span><span style="font-size:13px;color:#10b981;font-weight:600">All clean — no duplicate tickers found</span></div>')
