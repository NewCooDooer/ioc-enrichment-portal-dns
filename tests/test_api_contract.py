"""End-to-end API tests (backend + all three sources) replaying recorded real responses."""

import httpx

from backend.app import service
from conftest import load_exchanges, mount, mount_world

HIT = "/api/v1/domain/example.com"
UNKNOWN = "/api/v1/domain/this-does-not-exist-zzqq1234.com"


def statuses(body: dict) -> dict:
    return {key: block["status"] for key, block in body["sources"].items()}


# ---- an IOC with results -------------------------------------------------------------------------------------

def test_hit_returns_all_three_sources(client, mock):
    mount_world(mock, "hit")
    response = client.get(HIT)
    assert response.status_code == 200
    body = response.json()
    assert body["ioc"] == {"type": "domain", "input": "example.com", "value": "example.com"}
    assert statuses(body) == {"dns": "ok", "rdap": "ok", "crtsh": "ok"}


def test_hit_dns_data_matches_recording(client, mock):
    mount_world(mock, "hit")
    dns = client.get(HIT).json()["sources"]["dns"]["data"]
    recorded_a = [
        rr["data"]
        for ex in load_exchanges("doh", "hit")
        if "name=example.com&type=1" in ex["url"].replace("%3D", "=")
        for rr in ex["body_json"].get("Answer", [])
        if rr["type"] == 1
    ]
    assert dns["resolver"] == "dns.google" and dns["rcode"] == "NOERROR"
    assert [r["value"] for r in dns["A"]] == recorded_a and recorded_a
    assert set(dns) >= {"A", "AAAA", "NS", "MX", "TXT"}


def test_hit_rdap_follows_the_recorded_redirect(client, mock):
    mount_world(mock, "hit")
    rdap = client.get(HIT).json()["sources"]["rdap"]["data"]
    assert rdap["registrar"] == "RESERVED-Internet Assigned Numbers Authority"
    assert rdap["registered"] == "1995-08-14T04:00:00Z"
    assert rdap["registry_url"].startswith("https://rdap.verisign.com/com/v1/domain/example.com")
    assert all(ns == ns.lower() for ns in rdap["nameservers"]) and rdap["nameservers"]


def test_hit_crtsh_summary(client, mock):
    mount_world(mock, "hit")
    crt = client.get(HIT).json()["sources"]["crtsh"]["data"]
    assert crt["certificate_count"] > 0
    assert crt["first_seen"] <= crt["last_seen"]
    assert "example.com" in crt["names"]
    assert len(crt["names"]) <= 50 and len(crt["issuers"]) <= 10


# ---- an IOC that no source knows -----------------------------------------------------------------------------

def test_unknown_ioc_is_not_found_everywhere_but_still_200(client, mock):
    mount_world(mock, "unknown")
    response = client.get(UNKNOWN)
    assert response.status_code == 200
    body = response.json()
    assert statuses(body) == {"dns": "not_found", "rdap": "not_found", "crtsh": "not_found"}
    assert all(block["data"] is None and "error" not in block for block in body["sources"].values())


# ---- a source error: the others still return ------------------------------------------------------------------

def test_recorded_crtsh_502_shows_an_error_and_keeps_the_other_sources(client, mock):
    mount(mock, "doh", "hit")
    mount(mock, "rdap", "hit")
    mount(mock, "crtsh", "error_502")  # a real crt.sh 502 recorded on 2026-11-05
    response = client.get(HIT)
    assert response.status_code == 200
    body = response.json()
    assert statuses(body) == {"dns": "ok", "rdap": "ok", "crtsh": "error"}
    crt = body["sources"]["crtsh"]
    assert crt["data"] is None
    assert crt["error"] == {"code": "upstream_error", "message": "crt.sh returned HTTP 502"}
    assert body["sources"]["dns"]["data"]["A"] and body["sources"]["rdap"]["data"]["registrar"]


# ---- simulated failures (not recorded: built with respx and labelled as simulated) --------------------------------

def test_simulated_timeout_is_reported_as_timeout(client, mock):
    mount(mock, "doh", "hit")
    mount(mock, "crtsh", "hit")
    mock.get(url__startswith="https://rdap.org/").mock(side_effect=httpx.ReadTimeout("simulated"))
    body = client.get(HIT).json()
    assert body["sources"]["rdap"]["status"] == "error"
    assert body["sources"]["rdap"]["error"]["code"] == "timeout"
    assert body["sources"]["dns"]["status"] == "ok" and body["sources"]["crtsh"]["status"] == "ok"


def test_simulated_429_is_reported_as_rate_limited(client, mock):
    mount(mock, "doh", "hit")
    mount(mock, "crtsh", "hit")
    mock.get(url__startswith="https://rdap.org/").mock(
        return_value=httpx.Response(429, headers={"Retry-After": "10"})
    )
    rdap = client.get(HIT).json()["sources"]["rdap"]
    assert rdap["status"] == "error"
    assert rdap["error"]["code"] == "rate_limited" and "Retry-After: 10" in rdap["error"]["message"]


def test_simulated_unparseable_body_is_invalid_response(client, mock):
    mount(mock, "doh", "hit")
    mount(mock, "rdap", "hit")
    mock.get(url__startswith="https://crt.sh/").mock(return_value=httpx.Response(200, text="<html>not json</html>"))
    crt = client.get(HIT).json()["sources"]["crtsh"]
    assert crt["status"] == "error" and crt["error"]["code"] == "invalid_response"


def test_unexpected_bug_inside_one_source_becomes_that_sources_error(client, mock, monkeypatch):
    mount_world(mock, "hit")

    async def broken(name, http_client):
        raise RuntimeError("boom")

    monkeypatch.setitem(service.SOURCES, "rdap", broken)
    response = client.get(HIT)
    assert response.status_code == 200
    body = response.json()
    assert statuses(body) == {"dns": "ok", "rdap": "error", "crtsh": "ok"}


# ---- everything fails -> 502 --------------------------------------------------------------------------------------

def test_all_sources_failing_returns_502_with_each_error(client, mock):
    # Simulated: every source answers like the recorded crt.sh 502.
    for pattern in ("https://dns.google/", "https://rdap.org/", "https://crt.sh/"):
        mock.get(url__startswith=pattern).mock(return_value=httpx.Response(502, text="Bad Gateway"))
    response = client.get(HIT)
    assert response.status_code == 502
    body = response.json()
    assert body["error"] == "all sources failed" and body["input"] == "example.com"
    assert statuses(body) == {"dns": "error", "rdap": "error", "crtsh": "error"}


# ---- input handling stays offline and never reaches a source -----------------------------------------------------

def test_invalid_input_is_400_and_calls_no_source(client, mock):
    response = client.get("/api/v1/domain/10.0.0.1")
    assert response.status_code == 400
    assert response.json() == {
        "error": "not a valid DNS name: 10.0.0.1 (IP addresses are not accepted)",
        "input": "10.0.0.1",
    }
    assert mock.calls.call_count == 0


def test_health_and_unknown_route(client):
    assert client.get("/api/v1/health").json() == {"status": "ok"}
    missing = client.get("/nope")
    assert missing.status_code == 404 and missing.json() == {"error": "not found"}
