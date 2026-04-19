"""Exceptions shared by every service."""

from __future__ import annotations


class InternalServiceError(Exception):
    """A failure that occurred while talking to another internal service."""


class RemoteServiceError(InternalServiceError):
    """The remote service returned a 4xx/5xx response."""

    def __init__(self, service: str, status_code: int, body: str) -> None:
        super().__init__(f"{service} returned {status_code}: {body[:300]}")
        self.service = service
        self.status_code = status_code
        self.body = body


class CircuitBreakerOpen(InternalServiceError):
    """The circuit breaker for this service is open and refusing calls."""

    def __init__(self, service: str, retry_after_seconds: float) -> None:
        super().__init__(
            f"Circuit breaker open for '{service}'; retry after {retry_after_seconds:.1f}s"
        )
        self.service = service
        self.retry_after_seconds = retry_after_seconds
