"""Combines the sources into one response. Every source runs concurrently and can never crash the request."""

import asyncio
import logging

import httpx

from backend.app.models import DomainResponse, Ioc, SourceBlock
from backend.app.sources import crtsh, doh, rdap
from backend.app.sources.common import error_block

# A logger writes notes to the server's log (the terminal where you ran "python -m backend").
log = logging.getLogger("ioc-portal")

# The menu of sources: a name, and the function that asks that source.
# There are no parentheses after "doh.lookup": that means "the function itself", not "run it now".
SOURCES = {"dns": doh.lookup, "rdap": rdap.lookup, "crtsh": crtsh.lookup}


async def _safe(key: str, lookup, name: str, client: httpx.AsyncClient) -> dict:
    """Last line of defence: an unexpected bug inside one source becomes that source's error block."""
    try:
        # "await" means: pause here until the source has answered.
        return await lookup(name, client)
    except Exception:  # noqa: BLE001 - deliberately broad: ANY crash in one source must not break the others
        log.exception("unexpected error in source %s", key)
        return error_block("upstream_error", f"unexpected error while querying {key}")


async def enrich(raw_input: str, value: str, client: httpx.AsyncClient) -> DomainResponse:
    """Query every source for an already-validated name and merge the results."""
    keys = list(SOURCES)  # ["dns", "rdap", "crtsh"]

    # Step 1: prepare one "to-do item" per source. Calling _safe(...) does NOT run the lookup yet;
    # it only creates a job that is ready to start.
    todo_items = []
    for key in keys:
        lookup_function = SOURCES[key]
        todo_items.append(_safe(key, lookup_function, value, client))

    # Step 2: run all the to-do items AT THE SAME TIME and wait until every one has finished.
    # The results come back in the same order as the to-do items.
    results = await asyncio.gather(*todo_items)  # the * spreads the list into separate arguments

    # Step 3: pair each source name with its result, and wrap each result in the shape defined in models.py.
    sources = {}
    for key, result in zip(keys, results):  # zip pairs them up: ("dns", dns_result), ("rdap", rdap_result), ...
        # ** spreads the dictionary into named arguments: SourceBlock(status="ok", data={...})
        sources[key] = SourceBlock(**result)

    return DomainResponse(
        ioc=Ioc(type="domain", input=raw_input, value=value),
        sources=sources,
    )


def all_failed(response: DomainResponse) -> bool:
    """True only if EVERY source ended in an error. A 'not_found' answer counts as an answer, not a failure."""
    for block in response.sources.values():
        if block.status != "error":
            return False  # at least one source gave an answer
    return True
