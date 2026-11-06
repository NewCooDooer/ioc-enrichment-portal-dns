"""crt.sh Certificate Transparency search (keyless). Summarizes issued certificates. Never raises.

crt.sh is slow and often answers HTTP 502 (seen on 2026-11-05), which becomes an `error` block, not a crash.
"""

import httpx

from backend.app import config
from backend.app.sources.common import (error_block, not_found_block, ok_block,
                                         status_error, transport_error)

SERVICE = "crt.sh"
MAX_NAMES = 50
MAX_ISSUERS = 10


def summarize(rows: list) -> dict:
    """Condense raw certificate rows. Precertificates and final certificates share a serial: count each once."""
    # A "set" keeps each value only once, which is exactly what we want for counting and for lists of unique names.
    serials = set()
    issuers = set()
    names = set()
    starts = []
    for row in rows:
        serials.add(row["serial_number"])
        issuers.add(row["issuer_name"])
        starts.append(row["not_before"])
        # One certificate can list several names, one per line. Add each non-empty line.
        for line in row["name_value"].split("\n"):
            cleaned = line.strip()
            if cleaned:
                names.add(cleaned)
    sorted_names = sorted(names)
    return {
        "certificate_count": len(serials),
        "first_seen": min(starts),
        "last_seen": max(starts),
        "issuers": sorted(issuers)[:MAX_ISSUERS],
        "names": sorted_names[:MAX_NAMES],
        "names_truncated": len(sorted_names) > MAX_NAMES,
    }


async def lookup(name: str, client: httpx.AsyncClient) -> dict:
    try:
        response = await client.get(
            f"{config.CRTSH_URL}/",
            params={"q": name, "output": "json"},
            timeout=config.CRTSH_TIMEOUT_SECONDS,
        )
    except httpx.HTTPError as exc:
        return transport_error(exc, SERVICE, config.CRTSH_TIMEOUT_SECONDS)

    failure = status_error(response, SERVICE)
    if failure:
        return failure
    try:
        rows = response.json()
        if not isinstance(rows, list):
            raise ValueError("expected a list")
        if not rows:
            return not_found_block()
        return ok_block(summarize(rows))
    except (ValueError, KeyError, TypeError, AttributeError):
        return error_block("invalid_response", "crt.sh returned a response we could not parse")
