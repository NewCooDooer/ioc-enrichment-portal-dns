"""Google Public DNS over HTTPS (JSON API). Keyless. Never raises: returns a source block."""

import asyncio

import httpx

from backend.app import config
from backend.app.sources.common import error_block as _error

RECORD_TYPES = {"A": 1, "NS": 2, "MX": 15, "TXT": 16, "AAAA": 28}
RCODE_NAMES = {0: "NOERROR", 2: "SERVFAIL", 3: "NXDOMAIN", 5: "REFUSED"}


async def _query(client: httpx.AsyncClient, name: str, rtype: str) -> dict:
    """One DoH query. Returns {'rcode': int, 'records': [...]} or raises an httpx/ValueError."""
    response = await client.get(
        config.DOH_URL,
        params={"name": name, "type": RECORD_TYPES[rtype]},
        timeout=config.SOURCE_TIMEOUT_SECONDS,
    )
    if response.status_code == 429:
        raise _RateLimited(response.headers.get("Retry-After"))
    if response.status_code >= 400:
        raise _HttpFailure(response.status_code)
    body = response.json()
    rcode = body["Status"]
    wanted = RECORD_TYPES[rtype]
    records = [
        {"value": rr["data"], "ttl": rr["TTL"]}
        for rr in body.get("Answer", [])
        if rr.get("type") == wanted
    ]
    return {"rcode": rcode, "records": records}


class _RateLimited(Exception):
    def __init__(self, retry_after: str | None):
        self.retry_after = retry_after


class _HttpFailure(Exception):
    def __init__(self, status: int):
        self.status = status


async def lookup(name: str, client: httpx.AsyncClient) -> dict:
    """Resolve A, AAAA, NS, MX and TXT concurrently and return one source block."""
    types = list(RECORD_TYPES)
    try:
        results = await asyncio.gather(*(_query(client, name, t) for t in types))
    except httpx.TimeoutException:
        return _error("timeout", f"Google DNS did not answer within {config.SOURCE_TIMEOUT_SECONDS:g} s")
    except _RateLimited as exc:
        hint = f" (Retry-After: {exc.retry_after})" if exc.retry_after else ""
        return _error("rate_limited", "Google DNS returned HTTP 429" + hint)
    except _HttpFailure as exc:
        return _error("upstream_error", f"Google DNS returned HTTP {exc.status}")
    except httpx.HTTPError as exc:
        return _error("upstream_error", f"could not reach Google DNS: {type(exc).__name__}")
    except (ValueError, KeyError, TypeError):
        return _error("invalid_response", "Google DNS returned a response we could not parse")

    by_type = dict(zip(types, results))
    rcode = by_type["A"]["rcode"]
    if rcode == 3:
        return {"status": "not_found", "data": None}
    if rcode != 0:
        return _error("upstream_error", f"Google DNS returned {RCODE_NAMES.get(rcode, f'rcode {rcode}')}")

    data = {"resolver": "dns.google", "rcode": "NOERROR"}
    for rtype in ("A", "AAAA", "NS", "MX", "TXT"):
        data[rtype] = by_type[rtype]["records"]
    return {"status": "ok", "data": data}
