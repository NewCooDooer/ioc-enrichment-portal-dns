"""Combines the sources into one response. Milestone 1: Google DoH only."""

import httpx

from backend.app.models import DomainResponse, Ioc, SourceBlock
from backend.app.sources import doh


async def enrich(raw_input: str, value: str, client: httpx.AsyncClient) -> DomainResponse:
    """Query every source for an already-validated name and merge the blocks."""
    dns_block = await doh.lookup(value, client)
    return DomainResponse(
        ioc=Ioc(type="domain", input=raw_input, value=value),
        sources={"dns": SourceBlock(**dns_block)},
    )


def all_failed(response: DomainResponse) -> bool:
    return all(block.status == "error" for block in response.sources.values())
