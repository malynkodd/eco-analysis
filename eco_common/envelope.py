"""Standard response envelope and pagination primitives.

Every JSON response that crosses the API gateway has the shape

    {
      "data":  <payload | null>,
      "error": {"code": str, "message": str, "details": ...} | null,
      "meta":  {"request_id": str, "timestamp": str, "pagination": {...} | null}
    }

It is implemented as a custom ``JSONResponse`` so endpoints can keep
returning their domain models without a per-route adapter. Binary
responses (``Response(media_type="application/pdf")`` etc.) bypass the
envelope because they are not ``JSONResponse`` instances.
"""
from __future__ import annotations

import json
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any, Generic, List, Optional, TypeVar

from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

T = TypeVar("T")

request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")


class ErrorPayload(BaseModel):
    code: str
    message: str
    details: Optional[Any] = None


class PaginationMeta(BaseModel):
    page: int = Field(ge=1)
    limit: int = Field(ge=1, le=200)
    total: int = Field(ge=0)
    pages: int = Field(ge=0)


class EnvelopeMeta(BaseModel):
    request_id: str
    timestamp: str
    pagination: Optional[PaginationMeta] = None


class Envelope(BaseModel, Generic[T]):
    data: Optional[T] = None
    error: Optional[ErrorPayload] = None
    meta: EnvelopeMeta


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def _envelope_dict(
    *,
    data: Any,
    error: Optional[ErrorPayload],
    pagination: Optional[PaginationMeta],
) -> dict:
    return {
        "data": jsonable_encoder(data) if data is not None else None,
        "error": error.model_dump() if error is not None else None,
        "meta": {
            "request_id": request_id_ctx.get() or "",
            "timestamp": _utc_now(),
            "pagination": pagination.model_dump() if pagination else None,
        },
    }


class EnvelopeJSONResponse(JSONResponse):
    """Wraps the rendered payload unless it is already an envelope."""

    def render(self, content: Any) -> bytes:
        if not _looks_like_envelope(content):
            content = _envelope_dict(data=content, error=None, pagination=None)
        return json.dumps(content, separators=(",", ":"), default=str).encode("utf-8")


def _looks_like_envelope(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and "data" in value
        and "error" in value
        and "meta" in value
    )


def paginate(items: List[Any], *, page: int, limit: int, total: int) -> JSONResponse:
    pages = (total + limit - 1) // limit if limit else 0
    payload = _envelope_dict(
        data=items,
        error=None,
        pagination=PaginationMeta(page=page, limit=limit, total=total, pages=pages),
    )
    return JSONResponse(content=payload)


def error_response(
    *, status_code: int, code: str, message: str, details: Any = None
) -> JSONResponse:
    payload = _envelope_dict(
        data=None,
        error=ErrorPayload(code=code, message=message, details=details),
        pagination=None,
    )
    return JSONResponse(content=payload, status_code=status_code)
