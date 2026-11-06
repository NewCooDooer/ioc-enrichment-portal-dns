"""Input rules for DNS names (design.md section 4). Pure functions, no network."""

import ipaddress
import re

# What ONE piece of a domain name (the part between dots) may look like:
# starts and ends with a letter, number or underscore; hyphens are allowed in the middle; at most 63 characters.
LABEL = re.compile(r"^[a-z0-9_]([a-z0-9_-]{0,61}[a-z0-9_])?$")

# Characters that must never appear in a name. If one is there, someone probably pasted a URL or an e-mail address.
FORBIDDEN_CHARS = set("/:@?# \t\r\n")


class InvalidDomain(ValueError):
    """Raised with a short reason when the input is not an acceptable DNS name."""


def _looks_like_an_ip_address(text: str) -> bool:
    """True for things like 10.0.0.1 or 2001:db8::1."""
    try:
        ipaddress.ip_address(text)  # raises ValueError if the text is NOT an IP address
    except ValueError:
        return False
    return True


def normalize_domain(raw: str) -> str:
    """Return the normalized (lowercase, punycode, no trailing dot) name or raise InvalidDomain."""
    # Step 1: tidy up. Remove spaces at the ends, drop one trailing dot, make it lowercase.
    name = raw.strip()
    if name.endswith("."):
        name = name[:-1]  # [:-1] means "everything except the last character"
    name = name.lower()
    if not name:
        raise InvalidDomain("empty input")

    # Step 2: reject things that are not domain names.
    if _looks_like_an_ip_address(name):
        raise InvalidDomain("IP addresses are not accepted")

    for character in name:
        if character in FORBIDDEN_CHARS:
            raise InvalidDomain("URLs, ports, e-mail addresses and spaces are not accepted")

    # Step 3: convert non-English letters to the plain-letters form called punycode (bücher.de -> xn--bcher-kva.de).
    try:
        name = name.encode("idna").decode("ascii")
    except UnicodeError:
        raise InvalidDomain("invalid international (non-ASCII) name") from None

    # Step 4: check the size and shape of the name.
    if len(name) > 253:
        raise InvalidDomain("longer than 253 characters")

    labels = name.split(".")  # "login.example.com" -> ["login", "example", "com"]
    if len(labels) < 2:
        raise InvalidDomain("a single label is not a DNS name to look up")
    for label in labels:
        if not LABEL.match(label):
            raise InvalidDomain(f"invalid label: {label!r}")
    if labels[-1].isdigit():  # labels[-1] is the last piece, like "com"
        raise InvalidDomain("top-level label cannot be all digits")

    return name
