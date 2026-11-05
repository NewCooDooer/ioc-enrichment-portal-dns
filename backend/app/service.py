"""Combines the sources into one response. Every source runs concurrently and can never crash the request."""

import asyncio
import logging

import httpx

from backend.app.models import DomainResponse, Ioc, SourceBlock
from backend.app.sources import crtsh, doh, rdap
from backend.app.sources.common import error_block

log = logging.getLogger("ioc-portal")

SOURCES = {"dns": doh.lookup, "rdap": rdap.lookup, "crtsh": crtsh.lookup}


async def _safe(key: str, lookup, name: str, client: httpx.AsyncClient) -> dict:
    """Last line of defence: an unexpected bug inside one source becomes that source's error block."""
    try:
        return await lookup(name, client)
    except Exception:  # noqa: BLE001 - deliberately broad, see docstring
        log.exception("unexpected error in source %s", key)
        return error_block("upstream_error", f"unexpected error while querying {key}")


async def enrich(raw_input: str, value: str, client: httpx.AsyncClient) -> DomainResponse:
    """Query every source for an already-validated name and merge the blocks."""
    keys = list(SOURCES)
    blocks = await asyncio.gather(*(_safe(k, SOURCES[k], value, client) for k in keys))
    return DomainResponse(
        ioc=Ioc(type="domain", input=raw_input, value=value),
        sources={k: SourceBlock(**b) for k, b in zip(keys, blocks)},
    )


def all_failed(response: DomainResponse) -> bool:
    return all(block.status == "error" for block in response.sources.values())
