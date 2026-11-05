"""Streamlit frontend. Run: streamlit run frontend/app.py --server.port ${FRONTEND_PORT:-8510}"""

import streamlit as st
from client import fetch_domain

SOURCE_TITLES = {
    "dns": "DNS (Google Public DNS over HTTPS)",
    "rdap": "Registration (RDAP)",
    "crtsh": "Certificates (crt.sh)",
}

st.set_page_config(page_title="IOC Enrichment Portal: DNS names", page_icon="🔎")
st.title("IOC Enrichment Portal: DNS names")
st.caption(
    "Enter a domain name to see context from public sources. These sources report facts; "
    "none of them gives a verdict. **Do not enter internal or private names**: lookups go to outside services."
)

with st.form("lookup"):
    name = st.text_input("DNS name", placeholder="example.com")
    submitted = st.form_submit_button("Look up")


def render_dns(data: dict) -> None:
    for rtype in ("A", "AAAA", "NS", "MX", "TXT"):
        records = data.get(rtype, [])
        if records:
            st.markdown(f"**{rtype}**")
            st.table([{"value": r["value"], "ttl (s)": r["ttl"]} for r in records])
        else:
            st.markdown(f"**{rtype}**: no records")


def render_generic(data: dict) -> None:
    st.json(data)


def render_source(key: str, block: dict) -> None:
    title = SOURCE_TITLES.get(key, key)
    with st.container(border=True):
        st.subheader(title)
        status = block["status"]
        if status == "ok":
            st.success("OK: the source answered with data.")
            (render_dns if key == "dns" else render_generic)(block["data"])
        elif status == "not_found":
            st.info("Not found: the source answered that it knows nothing about this name.")
        else:
            err = block.get("error", {})
            st.error(f"Error ({err.get('code', 'unknown')}): {err.get('message', '')} "
                     "This does NOT mean there is no data; the check could not be completed.")


if submitted:
    if not name.strip():
        st.warning("Please type a DNS name.")
    else:
        with st.spinner("Asking the backend..."):
            result = fetch_domain(name)
        if result.status_code is None:
            st.error(result.message)
        elif result.status_code == 400:
            st.warning(f"Invalid input: {result.message}")
        elif result.status_code == 502:
            st.error(f"{result.message}: every source failed, so there is nothing to show.")
            for key, block in (result.body or {}).get("sources", {}).items():
                render_source(key, block)
        elif not result.ok:
            st.error(f"Unexpected backend response: {result.message}")
        else:
            ioc = result.body["ioc"]
            st.markdown(f"### Results for `{ioc['value']}`")
            if ioc["input"].strip().lower() != ioc["value"]:
                st.caption(f"You entered `{ioc['input']}`; normalized to `{ioc['value']}`.")
            for key, block in result.body["sources"].items():
                render_source(key, block)
            with st.expander("Raw JSON from the backend"):
                st.json(result.body)
