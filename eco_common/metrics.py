"""Prometheus instrumentation: a /metrics endpoint + per-request timing.

``mount_metrics(app)`` is invoked from ``create_app()`` so every service
exposes the standard four golden signals out of the box:

  http_requests_total{method, path, status}     counter
  http_request_duration_seconds{method, path}   histogram
  http_requests_in_flight{method}               gauge

The collectors are module-globals so multiple ``create_app()`` calls
inside the same process (tests) reuse the same registry and don't crash
on duplicate metric registration.
"""
from __future__ import annotations

import time

from fastapi import FastAPI, Request, Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    REGISTRY,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

_REQ_TOTAL: Counter | None = None
_REQ_DURATION: Histogram | None = None
_IN_FLIGHT: Gauge | None = None


def _get_or_create() -> tuple[Counter, Histogram, Gauge]:
    global _REQ_TOTAL, _REQ_DURATION, _IN_FLIGHT
    if _REQ_TOTAL is not None and _REQ_DURATION is not None and _IN_FLIGHT is not None:
        return _REQ_TOTAL, _REQ_DURATION, _IN_FLIGHT

    registry: CollectorRegistry = REGISTRY
    _REQ_TOTAL = Counter(
        "http_requests_total",
        "Total HTTP requests served, labelled by method/path/status.",
        ["method", "path", "status"],
        registry=registry,
    )
    _REQ_DURATION = Histogram(
        "http_request_duration_seconds",
        "End-to-end HTTP request duration in seconds.",
        ["method", "path"],
        buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10),
        registry=registry,
    )
    _IN_FLIGHT = Gauge(
        "http_requests_in_flight",
        "Number of HTTP requests currently being processed.",
        ["method"],
        registry=registry,
    )
    return _REQ_TOTAL, _REQ_DURATION, _IN_FLIGHT


def mount_metrics(app: FastAPI) -> None:
    req_total, req_duration, in_flight = _get_or_create()

    @app.middleware("http")
    async def _prometheus_mw(request: Request, call_next):
        method = request.method
        path = _route_template(request) or request.url.path
        in_flight.labels(method=method).inc()
        start = time.perf_counter()
        try:
            response = await call_next(request)
            status = str(response.status_code)
            return response
        except Exception:
            status = "500"
            raise
        finally:
            elapsed = time.perf_counter() - start
            req_duration.labels(method=method, path=path).observe(elapsed)
            req_total.labels(method=method, path=path, status=status).inc()
            in_flight.labels(method=method).dec()

    @app.get("/metrics", include_in_schema=False)
    def metrics():
        return Response(
            content=generate_latest(REGISTRY),
            media_type=CONTENT_TYPE_LATEST,
        )


def _route_template(request: Request) -> str | None:
    """Use the matched route template (``/projects/{project_id}``) so that
    label cardinality stays bounded — without it, every distinct id would
    spawn a new time series."""
    route = request.scope.get("route")
    if route is not None and getattr(route, "path", None):
        return route.path
    return None
