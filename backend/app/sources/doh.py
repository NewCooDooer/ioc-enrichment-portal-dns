"""Google Public DNS over HTTPS (JSON API). Keyless. Never raises: returns a source block."""

import asyncio

import httpx

from backend.app import config
from backend.app.sources.common import error_block as _error

# The five kinds of DNS record we ask for, with the number DNS uses for each kind.
RECORD_TYPES = {"A": 1, "NS": 2, "MX": 15, "TXT": 16, "AAAA": 28}
# DNS answers with a status number; these are the ones we give names to.
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

    # Keep only the answers of the kind we asked for (an A question can also bring back other kinds).
    records = []
    for answer in body.get("Answer", []):
        if answer.get("type") == wanted:
            records.append({"value": answer["data"], "ttl": answer["TTL"]})
    return {"rcode": rcode, "records": records}


# Two small custom errors. _query raises one of them to jump straight out when the reply is bad,
# and lookup() (below) catches them and turns each into a proper error block.
class _RateLimited(Exception):
    def __init__(self, retry_after: str | None):
        self.retry_after = retry_after


class _HttpFailure(Exception):
    def __init__(self, status: int):
        self.status = status


async def lookup(name: str, client: httpx.AsyncClient) -> dict:
    """Resolve A, AAAA, NS, MX and TXT concurrently and return one source block."""
    types = list(RECORD_TYPES)  # ["A", "NS", "MX", "TXT", "AAAA"]

    # Prepare one to-do item per record type, then run all five at the same time (see service.py for how gather works).
    todo_items = []
    for rtype in types:
        todo_items.append(_query(client, name, rtype))
    try:
        results = await asyncio.gather(*todo_items)
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

    # Pair each record type with its result: {"A": {...}, "NS": {...}, ...}
    by_type = {}
    for rtype, result in zip(types, results):
        by_type[rtype] = result

    rcode = by_type["A"]["rcode"]  # 0 = fine, 3 = this name does not exist
    if rcode == 3:
        return {"status": "not_found", "data": None}
    if rcode != 0:
        rcode_name = RCODE_NAMES.get(rcode, f"rcode {rcode}")
        return _error("upstream_error", f"Google DNS returned {rcode_name}")

    data = {"resolver": "dns.google", "rcode": "NOERROR"}
    for rtype in ("A", "AAAA", "NS", "MX", "TXT"):
        data[rtype] = by_type[rtype]["records"]
    return {"status": "ok", "data": data}
