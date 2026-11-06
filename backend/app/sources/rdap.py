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
    """Find the registrar's name. It is buried inside the "entities" list, in a contact-card ("vcard") format."""
    for entity in body.get("entities", []):
        if "registrar" in entity.get("roles", []):
            for item in entity.get("vcardArray", [None, []])[1]:
                if item[0] == "fn":
                    return item[3]
    return None


def parse(body: dict, final_url: str) -> dict:
    """Pick the facts we want out of RDAP's long reply."""
    # The reply lists dated events like {"eventAction": "registration", "eventDate": "1995-08-14T04:00:00Z"}.
    # Turn that list into a lookup table: {"registration": "1995-08-14...", "expiration": "...", ...}
    events = {}
    for event in body.get("events", []):
        events[event["eventAction"]] = event["eventDate"]

    # The registry's own page for this domain is the link marked "self" (if there is one).
    self_links = []
    for link in body.get("links", []):
        if link.get("rel") == "self":
            self_links.append(link["href"])
    if self_links:
        registry_url = self_links[0]
    else:
        registry_url = final_url

    # Name servers, lowercased and in alphabetical order.
    nameservers = []
    for server in body.get("nameservers", []):
        nameservers.append(server["ldhName"].lower())
    nameservers.sort()

    return {
        "registrar": _registrar(body),
        "registered": events.get("registration"),
        "expires": events.get("expiration"),
        "last_changed": events.get("last changed"),
        "statuses": list(body.get("status", [])),
        "nameservers": nameservers,
        "registry_url": registry_url,
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
