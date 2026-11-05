"""Helpers shared by every source so failures look identical in the response."""

import httpx


def error_block(code: str, message: str) -> dict:
    return {"status": "error", "data": None, "error": {"code": code, "message": message}}


def not_found_block() -> dict:
    return {"status": "not_found", "data": None}


def ok_block(data: dict) -> dict:
    return {"status": "ok", "data": data}


def transport_error(exc: httpx.HTTPError, service: str, timeout_seconds: float) -> dict:
    """Timeouts, refused connections, TLS problems, ... (no HTTP response at all)."""
    if isinstance(exc, httpx.TimeoutException):
        return error_block("timeout", f"{service} did not answer within {timeout_seconds:g} s")
    return error_block("upstream_error", f"could not reach {service}: {type(exc).__name__}")


def status_error(response: httpx.Response, service: str) -> dict | None:
    """An error block for HTTP 4xx/5xx (404 is handled by each source), else None."""
    if response.status_code == 429:
        retry = response.headers.get("Retry-After")
        hint = f" (Retry-After: {retry})" if retry else ""
        return error_block("rate_limited", f"{service} returned HTTP 429" + hint)
    if response.status_code >= 400:
        return error_block("upstream_error", f"{service} returned HTTP {response.status_code}")
    return None
