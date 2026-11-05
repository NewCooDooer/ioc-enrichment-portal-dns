"""Response models: the API contract of design.md section 4, in code."""

from typing import Any, Literal

from pydantic import BaseModel


class SourceError(BaseModel):
    code: Literal["timeout", "rate_limited", "upstream_error", "invalid_response", "missing_key"]
    message: str


class SourceBlock(BaseModel):
    status: Literal["ok", "not_found", "error"]
    data: dict[str, Any] | None = None
    error: SourceError | None = None


class Ioc(BaseModel):
    type: Literal["domain"] = "domain"
    input: str
    value: str


class DomainResponse(BaseModel):
    ioc: Ioc
    sources: dict[str, SourceBlock]


class ErrorResponse(BaseModel):
    error: str
    input: str | None = None
