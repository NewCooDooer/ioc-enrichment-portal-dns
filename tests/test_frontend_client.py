"""The frontend's only data access (frontend/client.py), tested against a mocked backend."""

import httpx
import respx

from client import fetch_domain

BASE = "http://backend.test"


def test_success_returns_the_body():
    with respx.mock() as mock:
        mock.get(f"{BASE}/api/v1/domain/example.com").mock(
            return_value=httpx.Response(200, json={"ioc": {"value": "example.com"}, "sources": {}})
        )
        result = fetch_domain("example.com", base_url=BASE)
    assert result.ok and result.status_code == 200 and result.message is None
    assert result.body["ioc"]["value"] == "example.com"


def test_name_is_url_encoded_and_400_message_is_surfaced():
    with respx.mock() as mock:
        route = mock.get(f"{BASE}/api/v1/domain/not%20a%20name").mock(
            return_value=httpx.Response(400, json={"error": "not a valid DNS name: not a name (...)", "input": "not a name"})
        )
        result = fetch_domain("  not a name ", base_url=BASE)
    assert route.called
    assert result.status_code == 400 and not result.ok
    assert result.message.startswith("not a valid DNS name")


def test_502_message_is_surfaced():
    with respx.mock() as mock:
        mock.get(f"{BASE}/api/v1/domain/example.com").mock(
            return_value=httpx.Response(502, json={"error": "all sources failed", "input": "example.com", "sources": {}})
        )
        result = fetch_domain("example.com", base_url=BASE)
    assert result.status_code == 502 and result.message == "all sources failed"


def test_backend_down_is_a_clear_message_not_a_crash():
    with respx.mock() as mock:
        mock.get(f"{BASE}/api/v1/domain/example.com").mock(side_effect=httpx.ConnectError("refused"))
        result = fetch_domain("example.com", base_url=BASE)
    assert result.status_code is None and result.body is None
    assert "Could not reach the backend" in result.message


def test_unreadable_backend_response():
    with respx.mock() as mock:
        mock.get(f"{BASE}/api/v1/domain/example.com").mock(return_value=httpx.Response(500, text="oops"))
        result = fetch_domain("example.com", base_url=BASE)
    assert result.status_code == 500 and "unreadable" in result.message
