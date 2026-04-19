"""Shared platform code reused across every microservice.

This package owns the authoritative implementation of:
  * RS256 JWT verification (``eco_common.auth``)
  * resilient httpx-based service-to-service client
    (``eco_common.http_client``)
  * typed internal-API wrappers used by the comparison + report services
    (``eco_common.internal``)
  * common exceptions (``eco_common.exceptions``)

Every service imports from here instead of redefining helpers.
"""
from eco_common.auth import (
    JWT_ALGORITHM,
    decode_token,
    get_current_user,
    oauth2_scheme,
)
from eco_common.exceptions import (
    CircuitBreakerOpen,
    InternalServiceError,
    RemoteServiceError,
)
from eco_common.http_client import (
    CircuitBreaker,
    HttpRetryClient,
    get_internal_client,
)
from eco_common.internal import InternalAPI

__all__ = [
    "JWT_ALGORITHM",
    "decode_token",
    "get_current_user",
    "oauth2_scheme",
    "InternalServiceError",
    "RemoteServiceError",
    "CircuitBreakerOpen",
    "CircuitBreaker",
    "HttpRetryClient",
    "get_internal_client",
    "InternalAPI",
]
