"""structlog JSON logging with uvicorn/gunicorn integration.

``configure_logging()`` is idempotent and safe to call from every service
during ``create_app(...)``. It:

* installs a single root handler that emits compact JSON to stdout
* routes the standard ``logging`` module through structlog so uvicorn's
  ``access`` / ``error`` and gunicorn's loggers come out in the same
  format as application logs
* injects the X-Request-ID held in ``request_id_ctx`` into every event
  so logs can be joined to specific requests in production
"""
from __future__ import annotations

import logging
import logging.config
import os
import sys

import structlog

from .envelope import request_id_ctx

_CONFIGURED = False


def _level() -> str:
    return os.getenv("LOG_LEVEL", "INFO").upper()


def _add_request_id(_, __, event_dict):
    rid = request_id_ctx.get()
    if rid:
        event_dict["request_id"] = rid
    return event_dict


def configure_logging() -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return

    timestamper = structlog.processors.TimeStamper(fmt="iso", utc=True)
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        timestamper,
        _add_request_id,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    logging.config.dictConfig({
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "()": structlog.stdlib.ProcessorFormatter,
                "processor": structlog.processors.JSONRenderer(),
                "foreign_pre_chain": shared_processors,
            },
        },
        "handlers": {
            "stdout": {
                "class": "logging.StreamHandler",
                "stream": sys.stdout,
                "formatter": "json",
            },
        },
        "root": {"level": _level(), "handlers": ["stdout"]},
        "loggers": {
            "uvicorn": {"level": _level(), "propagate": True},
            "uvicorn.error": {"level": _level(), "propagate": True},
            "uvicorn.access": {"level": _level(), "propagate": True},
            "gunicorn.error": {"level": _level(), "propagate": True},
            "gunicorn.access": {"level": _level(), "propagate": True},
        },
    })

    structlog.configure(
        processors=shared_processors + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, _level(), logging.INFO)
        ),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    _CONFIGURED = True


def get_logger(name: str | None = None):
    configure_logging()
    return structlog.get_logger(name)
