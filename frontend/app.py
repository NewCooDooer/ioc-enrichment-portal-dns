"""Streamlit frontend, Windows 95 style, with Trojan Tim.
Run: streamlit run frontend/app.py --server.port "${FRONTEND_PORT:-8510}"

All data comes from the backend (client.py). This file only decides what to show and how.
"""

import streamlit as st
from client import fetch_domain

import mascot
import render
import theme

st.set_page_config(page_title="Trojan Tim's IOC Enrichment Portal", page_icon="🐛", layout="centered")
st.markdown(theme.css_block(), unsafe_allow_html=True)

st.markdown(render.intro_window(), unsafe_allow_html=True)
tim_slot = st.empty()
tim_slot.markdown(theme.window("Trojan Tim says", mascot.popup(mascot.narrate_idle())), unsafe_allow_html=True)

with st.form("lookup"):
    name = st.text_input("Open:", placeholder="example.com")
    submitted = st.form_submit_button("Look up")

results = st.container()

if submitted:
    if not name.strip():
        tim_slot.markdown(
            theme.window("Trojan Tim says", mascot.popup(["You didn't type anything! Try a domain name like example.com."])),
            unsafe_allow_html=True,
        )
    else:
        tim_slot.markdown(theme.window("Trojan Tim says", mascot.popup(mascot.narrate_working())), unsafe_allow_html=True)
        result = fetch_domain(name)
        tim_slot.markdown(theme.window("Trojan Tim says", mascot.popup(mascot.narrate(result))), unsafe_allow_html=True)

        with results:
            if result.status_code is None:
                st.markdown(theme.dialog("error", "Backend unreachable", result.message), unsafe_allow_html=True)
            elif result.status_code == 400:
                st.markdown(theme.dialog("warn", "Invalid input", result.message), unsafe_allow_html=True)
            elif result.status_code == 502:
                st.markdown(
                    theme.dialog("error", "All sources failed", f"{result.message}: every source failed, so there is nothing to show."),
                    unsafe_allow_html=True,
                )
                for key, block in (result.body or {}).get("sources", {}).items():
                    st.markdown(render.source_window(key, block), unsafe_allow_html=True)
            elif not result.ok:
                st.markdown(theme.dialog("error", "Unexpected response", result.message or "unknown"), unsafe_allow_html=True)
            else:
                for key, block in result.body["sources"].items():
                    st.markdown(render.source_window(key, block), unsafe_allow_html=True)
                st.markdown(render.raw_json_window(result.body), unsafe_allow_html=True)

st.markdown(theme.taskbar(mascot.tim_img("w95-mini")), unsafe_allow_html=True)
