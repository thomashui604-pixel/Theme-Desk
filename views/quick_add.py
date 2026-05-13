"""Always-visible quick-add row: ticker(s) → basket → save."""

import streamlit as st

from gh_commit import commit_baskets, is_configured
from views.settings import save_baskets


def render_quick_add():
    baskets = st.session_state.baskets
    if not baskets:
        return

    with st.form("quick_add_form", clear_on_submit=True):
        c_in, c_b, c_btn = st.columns([4, 2, 1])
        with c_in:
            raw = st.text_input(
                "Add tickers",
                placeholder="＋ Add ticker(s) — paste one or many: NVDA, AMD, AVGO",
                label_visibility="collapsed",
            )
        with c_b:
            target = st.selectbox(
                "Basket",
                list(baskets.keys()),
                index=list(baskets.keys()).index(st.session_state.get("selected_basket"))
                if st.session_state.get("selected_basket") in baskets else 0,
                label_visibility="collapsed",
            )
        with c_btn:
            submitted = st.form_submit_button("＋ Add", use_container_width=True,
                                              type="primary")

    if not submitted:
        return

    new_raw = [t.strip().upper() for t in raw.replace("\n", ",").split(",") if t.strip()]
    if not new_raw:
        st.warning("Nothing to add.")
        return

    existing = set(baskets[target]["tickers"])
    new = [t for t in dict.fromkeys(new_raw) if t not in existing]
    dupes = [t for t in new_raw if t in existing]

    if not new:
        st.info(f"All {len(dupes)} ticker(s) already in **{target}**.")
        return

    baskets[target]["tickers"].extend(new)
    st.session_state.selected_basket = target
    save_baskets()  # local write (immediate for this session)

    msg_parts = [f"Added **{', '.join(new)}** to **{target}**"]
    if dupes:
        msg_parts.append(f"(skipped duplicates: {', '.join(dupes)})")

    if is_configured():
        with st.spinner("Committing to GitHub…"):
            ok, detail = commit_baskets(
                baskets,
                message=f"Add {', '.join(new)} to {target}",
            )
        if ok:
            st.success(" ".join(msg_parts) +
                       " · committed to repo (Streamlit Cloud will redeploy in ~30s)")
        else:
            st.warning(" ".join(msg_parts) +
                       f" · LOCAL ONLY — GitHub commit failed: `{detail}`")
    else:
        st.info(" ".join(msg_parts) +
                " · session only. Add `[github]` token to Streamlit secrets to persist.")
