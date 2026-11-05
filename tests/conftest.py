"""Shared test helpers: replay recorded real responses (tests/fixtures) through respx. No network calls."""

import json
from pathlib import Path

import httpx
import pytest
import respx
from fastapi.testclient import TestClient

from backend.app.main import app

FIXTURES = Path(__file__).parent / "fixtures"


def load_exchanges(source: str, case: str) -> list[dict]:
    return json.loads((FIXTURES / source / f"{case}.json").read_text())["exchanges"]


def mount(mock: respx.MockRouter, source: str, case: str) -> None:
    """Serve every recorded request/response pair of a fixture (including redirect hops)."""
    for ex in load_exchanges(source, case):
        headers = {"location": ex["location"]} if "location" in ex else {}
        if "body_json" in ex:
            content = json.dumps(ex["body_json"]).encode()
        else:
            content = ex.get("body_text", "").encode()
        mock.get(ex["url"]).mock(return_value=httpx.Response(ex["status"], headers=headers, content=content))


def mount_world(mock: respx.MockRouter, case: str, crtsh_case: str | None = None) -> None:
    mount(mock, "doh", case)
    mount(mock, "rdap", case)
    mount(mock, "crtsh", crtsh_case or case)


@pytest.fixture
def mock() -> respx.MockRouter:
    with respx.mock(assert_all_called=False) as router:
        yield router


@pytest.fixture
def client(mock):
    """A TestClient for the real backend app; its outgoing HTTP is intercepted by respx."""
    with TestClient(app) as test_client:
        yield test_client
