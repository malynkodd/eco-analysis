"""Resilient httpx-based async client used for service-to-service calls.

Features:
  * configurable timeout
  * exponential-backoff retry on connect / read / 5xx errors
  * per-target circuit breaker that opens after consecutive failures
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Mapping, Optional

import httpx

from eco_common.envelope import request_id_ctx
from eco_common.exceptions import CircuitBreakerOpen, RemoteServiceError

log = logging.getLogger(__name__)


# ─── Circuit breaker ─────────────────────────────────────────────────────────


@dataclass
class CircuitBreaker:
    """Per-target failure tracker.

    Opens after ``failure_threshold`` consecutive failures and stays open
    for ``recovery_seconds`` before allowing a probe call.
    """

    failure_threshold: int = 5
    recovery_seconds: float = 30.0
    _failures: int = 0
    _opened_at: Optional[float] = None

    def before_call(self, name: str) -> None:
        if self._opened_at is None:
            return
        elapsed = time.monotonic() - self._opened_at
        if elapsed < self.recovery_seconds:
            raise CircuitBreakerOpen(name, self.recovery_seconds - elapsed)
        self._opened_at = None
        self._failures = 0

    def record_success(self) -> None:
        self._failures = 0
        self._opened_at = None

    def record_failure(self) -> None:
        self._failures += 1
        if self._failures >= self.failure_threshold and self._opened_at is None:
            self._opened_at = time.monotonic()


# ─── HTTP client with retry ──────────────────────────────────────────────────


@dataclass
class HttpRetryClient:
    """Thin wrapper around ``httpx.AsyncClient`` with retry + circuit breaker."""

    max_retries: int = 3
    timeout_seconds: float = 5.0
    backoff_base: float = 0.25
    breakers: Dict[str, CircuitBreaker] = field(default_factory=dict)

    def _breaker(self, key: str) -> CircuitBreaker:
        if key not in self.breakers:
            self.breakers[key] = CircuitBreaker()
        return self.breakers[key]

    async def request(
        self,
        method: str,
        url: str,
        *,
        service: str,
        headers: Optional[Mapping[str, str]] = None,
        json: Any = None,
        params: Any = None,
    ) -> httpx.Response:
        breaker = self._breaker(service)
        breaker.before_call(service)

        merged_headers: Dict[str, str] = dict(headers or {})
        rid = request_id_ctx.get()
        if rid and "X-Request-ID" not in {k.title() for k in merged_headers}:
            merged_headers["X-Request-ID"] = rid

        last_exc: Optional[BaseException] = None
        for attempt in range(1, self.max_retries + 1):
            try:
                async with httpx.AsyncClient(
                    timeout=self.timeout_seconds
                ) as client:
                    resp = await client.request(
                        method=method,
                        url=url,
                        headers=merged_headers,
                        json=json,
                        params=params,
                    )
                if 500 <= resp.status_code < 600:
                    raise RemoteServiceError(service, resp.status_code, resp.text)
                if resp.status_code >= 400:
                    breaker.record_success()
                    raise RemoteServiceError(service, resp.status_code, resp.text)
                breaker.record_success()
                return resp
            except (httpx.HTTPError, RemoteServiceError) as exc:
                last_exc = exc
                breaker.record_failure()
                if attempt < self.max_retries:
                    await asyncio.sleep(self.backoff_base * (2 ** (attempt - 1)))
                    log.warning(
                        "retry %d/%d %s %s -> %s",
                        attempt,
                        self.max_retries,
                        method,
                        url,
                        exc,
                    )
        assert last_exc is not None
        raise last_exc


_singleton: Optional[HttpRetryClient] = None


def get_internal_client() -> HttpRetryClient:
    """Return the process-wide retry client."""
    global _singleton
    if _singleton is None:
        _singleton = HttpRetryClient()
    return _singleton
