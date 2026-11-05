"""The frontend's only data access: calls the backend API. It never calls a source."""

import os
from dataclasses import dataclass
from urllib.parse import quote

import httpx
from dotenv import load_dotenv

load_dotenv()

DEFAULT_BACKEND_URL = "http://127.0.0.1:8010"


@dataclass
class Result:
    status_code: int | None  # None when the backend could not be reached
    body: dict | None
    message: str | None = None  # human-readable problem, when there is one

    @property
    def ok(self) -> bool:
        return self.status_code == 200


# The backend waits up to 60 s for crt.sh (backend/app/config.py); this must be longer.
DEFAULT_TIMEOUT_SECONDS = 75.0


def fetch_domain(name: str, base_url: str | None = None, timeout: float = DEFAULT_TIMEOUT_SECONDS) -> Result:
    base_url = (base_url or os.getenv("BACKEND_URL", DEFAULT_BACKEND_URL)).rstrip("/")
    url = f"{base_url}/api/v1/domain/{quote(name.strip(), safe='')}"
    try:
        response = httpx.get(url, timeout=timeout)
    except httpx.HTTPError as exc:
        return Result(None, None, f"Could not reach the backend at {base_url} ({type(exc).__name__}). Is it running?")
    try:
        body = response.json()
    except ValueError:
        return Result(response.status_code, None, f"The backend returned an unreadable response (HTTP {response.status_code}).")
    message = None if response.status_code == 200 else body.get("error", f"HTTP {response.status_code}")
    return Result(response.status_code, body, message)
