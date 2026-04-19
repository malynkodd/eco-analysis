"""Factory that builds a uniformly-configured FastAPI app.

Every service should call ``create_app(...)`` instead of constructing
``FastAPI()`` directly so that the response envelope, CORS, exception
handlers and request-id middleware are wired identically across the
entire microservice fleet.
"""
from __future__ import annotations

import os
import uuid
from typing import List, Optional

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from .envelope import (
    EnvelopeJSONResponse,
    error_response,
    request_id_ctx,
)


def _is_production() -> bool:
    return os.getenv("ENVIRONMENT", "development").lower() == "production"


def _cors_origins() -> List[str]:
    raw = os.getenv("CORS_ALLOWED_ORIGINS", "")
    return [o.strip() for o in raw.split(",") if o.strip()]


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Ensures every request has a stable X-Request-ID header.

    Reads the inbound header if the gateway/client supplied one, otherwise
    mints a UUID4. Echoes it back on the response and stashes it in the
    ``request_id_ctx`` context-var so logging and the envelope can pick
    it up without explicit plumbing.
    """

    HEADER = "X-Request-ID"

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get(self.HEADER) or uuid.uuid4().hex
        token = request_id_ctx.set(request_id)
        try:
            response = await call_next(request)
        finally:
            request_id_ctx.reset(token)
        response.headers[self.HEADER] = request_id
        return response


def create_app(
    *,
    title: str,
    root_path: str,
    openapi_tags: Optional[list] = None,
    description: Optional[str] = None,
    version: str = "1.0.0",
) -> FastAPI:
    app = FastAPI(
        title=title,
        version=version,
        description=description or title,
        root_path=root_path,
        openapi_tags=openapi_tags,
        docs_url=None if _is_production() else "/docs",
        redoc_url=None if _is_production() else "/redoc",
        openapi_url=None if _is_production() else "/openapi.json",
        default_response_class=EnvelopeJSONResponse,
    )

    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins(),
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
    )

    @app.exception_handler(StarletteHTTPException)
    async def _http_exc_handler(_: Request, exc: StarletteHTTPException):
        return error_response(
            status_code=exc.status_code,
            code=_status_code_to_code(exc.status_code),
            message=str(exc.detail) if exc.detail else "Request failed",
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_handler(_: Request, exc: RequestValidationError):
        return error_response(
            status_code=422,
            code="validation_error",
            message="Request body did not validate",
            details=exc.errors(),
        )

    @app.exception_handler(Exception)
    async def _unhandled_handler(_: Request, exc: Exception):
        return error_response(
            status_code=500,
            code="internal_error",
            message="Internal server error",
            details=str(exc) if not _is_production() else None,
        )

    return app


def _status_code_to_code(status_code: int) -> str:
    return {
        400: "bad_request",
        401: "unauthorized",
        403: "forbidden",
        404: "not_found",
        409: "conflict",
        422: "unprocessable_entity",
        429: "too_many_requests",
        502: "bad_gateway",
        503: "service_unavailable",
    }.get(status_code, "error")
