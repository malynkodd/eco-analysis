"""Unit tests for the circuit breaker in eco_common.http_client."""
from __future__ import annotations

import time

import pytest

from eco_common.exceptions import CircuitBreakerOpen
from eco_common.http_client import CircuitBreaker


def test_breaker_starts_closed():
    cb = CircuitBreaker(failure_threshold=3, recovery_seconds=60)
    cb.before_call("svc")  # must not raise


def test_breaker_opens_after_threshold_failures():
    cb = CircuitBreaker(failure_threshold=3, recovery_seconds=60)
    for _ in range(3):
        cb.record_failure()
    with pytest.raises(CircuitBreakerOpen):
        cb.before_call("svc")


def test_success_resets_failure_counter():
    cb = CircuitBreaker(failure_threshold=3, recovery_seconds=60)
    cb.record_failure()
    cb.record_failure()
    cb.record_success()
    cb.record_failure()
    cb.record_failure()
    cb.before_call("svc")  # 2 < threshold, still closed


def test_breaker_recloses_after_recovery_window(monkeypatch):
    cb = CircuitBreaker(failure_threshold=2, recovery_seconds=1.0)
    cb.record_failure()
    cb.record_failure()

    # Advance the monotonic clock past the recovery window.
    real_time = time.monotonic()
    monkeypatch.setattr(time, "monotonic", lambda: real_time + 5.0)

    cb.before_call("svc")  # half-open probe -> allowed
    cb.record_success()
    cb.before_call("svc")  # fully reset


def test_circuit_breaker_open_carries_retry_after():
    exc = CircuitBreakerOpen("svc-x", 12.5)
    assert exc.service == "svc-x"
    assert exc.retry_after_seconds == 12.5
