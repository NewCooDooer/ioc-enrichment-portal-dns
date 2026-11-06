"""Turns the backend's JSON into Windows-95 HTML. Every value that came from a source is escaped here."""

import html
import json

import theme

TITLES = {
    "dns": "DNS - Google Public DNS.exe",
    "rdap": "RDAP - Registration.exe",
    "crtsh": "crt.sh - Certificates.exe",
}


def esc(value) -> str:
    return html.escape("" if value is None else str(value))


def table(headers: list[str], rows: list[list], key_value: bool = False) -> str:
    """An escaped table. key_value=True keeps the first column on one line (labels such as "Last changed")."""
    # Build the header cells, then each row of cells. esc() cleans every value so it can never run as code.
    head = ""
    for header in headers:
        head += f"<th>{esc(header)}</th>"
    body = ""
    for row in rows:
        cells = ""
        for cell in row:
            cells += f"<td>{esc(cell)}</td>"
        body += "<tr>" + cells + "</tr>"
    css = "w95-table w95-kv" if key_value else "w95-table"
    return f'<div class="w95-scroll"><table class="{css}"><tr>{head}</tr>{body}</table></div>'


def _ok_banner() -> str:
    return '<p class="w95-status">OK: the source answered with data.</p>'


def dns_body(data: dict) -> str:
    parts = [_ok_banner()]
    for rtype in ("A", "AAAA", "NS", "MX", "TXT"):
        records = data.get(rtype, [])
        parts.append(f"<h4>{rtype}</h4>")
        if records:
            rows = []
            for record in records:
                rows.append([record["value"], record["ttl"]])
            parts.append(table(["value", "ttl (s)"], rows))
        else:
            parts.append("<p>no records</p>")
    return "".join(parts)


def rdap_body(data: dict) -> str:
    rows = [
        ["Registrar", data.get("registrar") or "not stated"],
        ["Registered", data.get("registered") or "not stated"],
        ["Expires", data.get("expires") or "not stated"],
        ["Last changed", data.get("last_changed") or "not stated"],
        ["Status flags", ", ".join(data.get("statuses", [])) or "none"],
        ["Name servers", ", ".join(data.get("nameservers", [])) or "none"],
    ]
    return _ok_banner() + table(["field", "value"], rows, key_value=True) + f"<p>Registry record: {esc(data.get('registry_url'))}</p>"


def crtsh_body(data: dict) -> str:
    summary = (
        f"<p><b>{esc(data['certificate_count'])}</b> certificates, first seen <b>{esc(data['first_seen'])}</b>, "
        f"most recent <b>{esc(data['last_seen'])}</b></p>"
    )
    issuer_rows = []
    for issuer in data["issuers"]:
        issuer_rows.append([issuer])
    name_rows = []
    for name in data["names"]:
        name_rows.append([name])
    issuers = table(["issuer"], issuer_rows)
    names = table(["names on the certificates"], name_rows)
    note = "<p>List truncated; more names exist.</p>" if data.get("names_truncated") else ""
    return _ok_banner() + summary + "<h4>Issuers</h4>" + issuers + f"<h4>Names ({esc(len(data['names']))} shown)</h4>" + names + note


_BODIES = {"dns": dns_body, "rdap": rdap_body, "crtsh": crtsh_body}

NOT_FOUND_TEXT = "Not found: the source answered that it knows nothing about this name."
RDAP_EXTRA = (
    " For RDAP this also happens for subdomains (RDAP only covers registered domains) and for "
    "top-level domains rdap.org does not cover, such as .de or .io."
)


def source_window(key: str, block: dict) -> str:
    """One window per source. ok = data table; not_found = info box; error = error box."""
    title = TITLES.get(key, key)
    if block["status"] == "ok":
        return theme.window(title, _BODIES[key](block["data"]))
    if block["status"] == "not_found":
        return theme.dialog("info", title, NOT_FOUND_TEXT + (RDAP_EXTRA if key == "rdap" else ""))
    err = block.get("error") or {}
    return theme.dialog(
        "error",
        title,
        f"Error ({err.get('code', 'unknown')}): {err.get('message', '')}. "
        "This does NOT mean there is no data; the check could not be completed.",
    )


def _pretty_json_html(body: dict) -> str:
    """Indented JSON as HTML. Streamlit's markdown pass collapses newlines and spaces even inside <pre>,
    so line breaks are explicit <br> and the indentation is explicit &nbsp;. Every value is escaped."""
    lines = []
    for line in json.dumps(body, indent=2).split("\n"):
        text = line.lstrip(" ")
        lines.append("&nbsp;" * (len(line) - len(text)) + esc(text))
    return "<br>".join(lines)


def raw_json_window(body: dict) -> str:
    return theme.window(
        "Raw JSON from the backend",
        f'<details><summary>Show</summary><div class="w95-pre">{_pretty_json_html(body)}</div></details>',
    )


def intro_window() -> str:
    return theme.window(
        "IOC Enrichment Portal: DNS names",
        "<p>Enter a domain name to see context from public sources. These sources report facts; none of them gives a verdict.</p>"
        "<p><b>Do not enter internal or private names:</b> lookups go to outside services.</p>",
    )
