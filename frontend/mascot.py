"""Trojan Tim, the chipper pixel bug: his picture, his speech bubble and what he says.

Content rules (design.md): sources report facts, never verdicts. Tim must never call a name
clean, safe, malicious, benign or trusted, and a source that could not be checked must never sound like
"nothing there". `narrate()` is a pure function so these rules can be tested.
"""

import base64
import html

# A 16x15 pixel bug. k=outline, g=green, G=dark green, w=white of the eyes, '.'=transparent.
_PIXELS = [
    "....k......k....",
    ".....k....k.....",
    "......kkkk......",
    "....kkggggkk....",
    "...kggggggggk...",
    "..kggwwggwwggk..",
    "..kggwkggwkggk..",
    "..kggggggggggk..",
    "..kgggkkkkgggk..",
    "..kggggkkggggk..",
    "...kggggggggk...",
    "..kkGGGGGGGGkk..",
    ".k.kGGGGGGGGk.k.",
    "k...kkkkkkkk...k",
    "...k..k..k..k...",
]
_COLORS = {"k": "#101010", "g": "#3ddc3d", "G": "#1f9a1f", "w": "#ffffff"}


def _svg() -> str:
    # One tiny square per coloured pixel. Walk every row (y) and every character in the row (x).
    rects = ""
    for y, row in enumerate(_PIXELS):
        for x, colour_code in enumerate(row):
            if colour_code != ".":  # "." means transparent: draw nothing
                rects += f'<rect x="{x}" y="{y}" width="1" height="1" fill="{_COLORS[colour_code]}"/>'
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 {len(_PIXELS)}" '
        f'shape-rendering="crispEdges">{rects}</svg>'
    )


def tim_data_uri() -> str:
    """The picture as a data: URI, so the page loads nothing from outside and no markup is injected."""
    return "data:image/svg+xml;base64," + base64.b64encode(_svg().encode()).decode()


def tim_img(css_class: str = "w95-tim") -> str:
    return f'<img class="{css_class}" src="{tim_data_uri()}" alt="Trojan Tim, a smiling green pixel bug">'


def bubble(lines: list[str]) -> str:
    """Speech bubble HTML. Every line is escaped: it may contain text that came from a source."""
    paragraphs = "".join(f"<p>{html.escape(line)}</p>" for line in lines)
    return f'<div class="w95-bubble" role="status">{paragraphs}</div>'


def popup(lines: list[str]) -> str:
    """Tim plus his bubble, as one Clippy-style popup (the window chrome is added by theme.window)."""
    return f'<div class="w95-tim-row">{tim_img()}{bubble(lines)}</div>'


# ---------------------------------------------------------------------------------------------------------------
# What Tim says
# ---------------------------------------------------------------------------------------------------------------

SIGN_OFF = "I only report facts. You decide what they mean."


def narrate_idle() -> list[str]:
    return [
        "Hi! I'm Trojan Tim, your friendly neighborhood bug.",
        "Type a domain name below and click Look up. I'll ask three public sources what they know: "
        "DNS, RDAP and crt.sh.",
        "Heads up: please don't type internal or private names. These lookups go to outside services.",
    ]


def narrate_working() -> list[str]:
    return [
        "On it! Sniffing around...",
        "crt.sh is slow and can take up to a minute, so hang tight.",
    ]


def _count(n: int, singular: str, plural: str | None = None) -> str:
    plural = plural or singular + "s"
    return f"{n} {singular if n == 1 else plural}"


def _dns_line(block: dict) -> str:
    if block["status"] == "ok":
        d = block["data"]
        return (
            f"DNS: it points to {_count(len(d['A']), 'IPv4 address', 'IPv4 addresses')} and "
            f"{_count(len(d['AAAA']), 'IPv6 address', 'IPv6 addresses')}, with {_count(len(d['NS']), 'name server')}."
        )
    if block["status"] == "not_found":
        return "DNS: Google says that name does not exist (NXDOMAIN)."
    return _error_line("DNS", block)


def _rdap_line(block: dict) -> str:
    if block["status"] == "ok":
        d = block["data"]
        registered = (d.get("registered") or "an unstated date")[:10]
        registrar = d.get("registrar") or "an unstated registrar"
        expires = (d.get("expires") or "")[:10]
        tail = f"; it expires {expires}" if expires else ""
        return f"RDAP: registered {registered} through {registrar}{tail}."
    if block["status"] == "not_found":
        return (
            "RDAP: no registration record. That can mean no such domain, a subdomain, "
            "or a top-level domain rdap.org does not cover."
        )
    return _error_line("RDAP", block)


def _crtsh_line(block: dict) -> str:
    if block["status"] == "ok":
        d = block["data"]
        return (
            f"crt.sh: {_count(d['certificate_count'], 'certificate')} on record, "
            f"first seen {d['first_seen'][:10]}, most recent {d['last_seen'][:10]}."
        )
    if block["status"] == "not_found":
        return "crt.sh: no certificates on record for that exact name."
    return _error_line("crt.sh", block)


def _error_line(label: str, block: dict) -> str:
    err = block.get("error") or {}
    return (
        f"{label}: I couldn't check this one ({err.get('code', 'error')}). "
        "That is not the same as finding nothing."
    )


_LINES = {"dns": _dns_line, "rdap": _rdap_line, "crtsh": _crtsh_line}


def narrate(result) -> list[str]:
    """Tim's lines for a finished lookup. `result` is frontend.client.Result."""
    if result.status_code is None:
        return [
            "Uh oh, I can't reach my brain (the backend).",
            "Is it running? Start it with: python -m backend",
        ]
    if result.status_code == 400:
        return [
            "Hmm, that doesn't look like a domain name I can use.",
            f"The backend says: {result.message}",
            "Try something like example.com: no spaces, no http://, and no IP addresses.",
        ]
    if result.status_code == 502:
        return [
            "Yikes, every source failed, so I have nothing to report.",
            "That tells us nothing about the domain. It only means none of the checks could be completed.",
        ]
    if result.status_code != 200 or not result.body:
        return ["Something unexpected happened.", f"The backend says: {result.message}"]

    value = result.body["ioc"]["value"]
    lines = [f"Here's what I found for {value}:"]
    for key, block in result.body["sources"].items():
        lines.append(_LINES[key](block))
    lines.append(SIGN_OFF)
    return lines
