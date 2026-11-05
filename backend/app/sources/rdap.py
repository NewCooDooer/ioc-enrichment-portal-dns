"""RDAP via rdap.org (keyless). Registration data for a registered domain. Never raises.

rdap.org answers with a 302 redirect to the registry's own RDAP server, so the client must follow redirects.
The name is looked up exactly as typed: a subdomain such as login.example.com is normally "not_found".
rdap.org also answers 404 for top-level domains it has no RDAP server for (seen for .de and .io), so
"not_found" means: no such domain, not a registered domain, OR a TLD that rdap.org does not cover.
"""

import httpx

from backend.app import config
from backend.app.sources.common import (error_block, not_found_block, ok_block,
                                         status_error, transport_error)

SERVICE = "RDAP"


def _registrar(body: dict) -> str | None:
    for entity in body.get("entities", []):
        if "registrar" in entity.get("roles", []):
            for item in entity.get("vcardArray", [None, []])[1]:
                if item[0] == "fn":
                    return item[3]
    return None


def parse(body: dict, final_url: str) -> dict:
    events = {e["eventAction"]: e["eventDate"] for e in body.get("events", [])}
    self_links = [l["href"] for l in body.get("links", []) if l.get("rel") == "self"]
    return {
        "registrar": _registrar(body),
        "registered": events.get("registration"),
        "expires": events.get("expiration"),
        "last_changed": events.get("last changed"),
        "statuses": list(body.get("status", [])),
        "nameservers": sorted(ns["ldhName"].lower() for ns in body.get("nameservers", [])),
        "registry_url": self_links[0] if self_links else final_url,
    }


async def lookup(name: str, client: httpx.AsyncClient) -> dict:
    url = f"{config.RDAP_URL}/domain/{name}"
    try:
        response = await client.get(
            url, timeout=config.SOURCE_TIMEOUT_SECONDS, headers={"Accept": "application/rdap+json"}
        )
    except httpx.HTTPError as exc:
        return transport_error(exc, SERVICE, config.SOURCE_TIMEOUT_SECONDS)

    if response.status_code == 404:
        return not_found_block()
    failure = status_error(response, SERVICE)
    if failure:
        return failure
    try:
        return ok_block(parse(response.json(), str(response.url)))
    except (ValueError, KeyError, TypeError, IndexError, AttributeError):
        return error_block("invalid_response", "RDAP returned a response we could not parse")
