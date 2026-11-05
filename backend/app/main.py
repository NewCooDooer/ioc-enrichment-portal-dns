"""FastAPI backend: GET /api/v1/domain/{name} and GET /api/v1/health."""

import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.app import config, service
from backend.app.models import DomainResponse, ErrorResponse
from backend.app.validation import InvalidDomain, normalize_domain

log = logging.getLogger("ioc-portal")


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with httpx.AsyncClient(
        follow_redirects=True, headers={"User-Agent": config.USER_AGENT}
    ) as client:
        app.state.client = client
        yield


app = FastAPI(title="IOC Enrichment Portal (DNS names)", version="1", lifespan=lifespan)


def _error(status: int, message: str, input_value: str | None = None, **extra) -> JSONResponse:
    body = {"error": message}
    if input_value is not None:
        body["input"] = input_value
    body.update(extra)
    return JSONResponse(status_code=status, content=body)


@app.get("/api/v1/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get(
    "/api/v1/domain/{name:path}",
    response_model=DomainResponse,
    response_model_exclude_unset=True,
    responses={400: {"model": ErrorResponse}, 502: {"model": ErrorResponse}},
)
async def get_domain(name: str, request: Request):
    try:
        value = normalize_domain(name)
    except InvalidDomain as exc:
        return _error(400, f"not a valid DNS name: {name} ({exc})", name)

    result = await service.enrich(name, value, request.app.state.client)
    if service.all_failed(result):
        sources = result.model_dump(exclude_unset=True)["sources"]
        return _error(502, "all sources failed", name, sources=sources)
    return result


@app.exception_handler(StarletteHTTPException)
async def http_error(request: Request, exc: StarletteHTTPException):
    message = "not found" if exc.status_code == 404 else str(exc.detail)
    return _error(exc.status_code, message)


@app.exception_handler(Exception)
async def unexpected_error(request: Request, exc: Exception):
    log.exception("unexpected error on %s", request.url.path)
    return _error(500, "internal error")
