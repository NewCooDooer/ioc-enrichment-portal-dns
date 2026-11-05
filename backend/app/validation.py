"""Input rules for DNS names (design.md section 4). Pure functions, no network."""

import ipaddress
import re

LABEL = re.compile(r"^[a-z0-9_]([a-z0-9_-]{0,61}[a-z0-9_])?$")
FORBIDDEN_CHARS = set("/:@?# \t\r\n")


class InvalidDomain(ValueError):
    """Raised with a short reason when the input is not an acceptable DNS name."""


def normalize_domain(raw: str) -> str:
    """Return the normalized (lowercase, punycode, no trailing dot) name or raise InvalidDomain."""
    name = raw.strip()
    if name.endswith("."):
        name = name[:-1]
    name = name.lower()
    if not name:
        raise InvalidDomain("empty input")

    try:
        ipaddress.ip_address(name)
    except ValueError:
        pass
    else:
        raise InvalidDomain("IP addresses are not accepted")

    if any(ch in FORBIDDEN_CHARS for ch in name):
        raise InvalidDomain("URLs, ports, e-mail addresses and spaces are not accepted")

    try:
        name = name.encode("idna").decode("ascii")
    except UnicodeError:
        raise InvalidDomain("invalid international (non-ASCII) name") from None

    if len(name) > 253:
        raise InvalidDomain("longer than 253 characters")

    labels = name.split(".")
    if len(labels) < 2:
        raise InvalidDomain("a single label is not a DNS name to look up")
    for label in labels:
        if not LABEL.match(label):
            raise InvalidDomain(f"invalid label: {label!r}")
    if labels[-1].isdigit():
        raise InvalidDomain("top-level label cannot be all digits")
    return name
