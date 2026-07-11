"""
core/logger.py
──────────────
Structured logging setup using structlog.

Call `setup_logging()` once at application startup (in api/main.py,
dashboard/app.py, or the ingestion scheduler entry point).

After setup, get a logger in any module with:
    import structlog
    log = structlog.get_logger(__name__)
    log.info("event_name", key="value")

In development:  colourful console output with timestamps.
In production:   JSON lines for log aggregation (e.g. Cloud Logging).
"""
from __future__ import annotations

import logging
import sys
from typing import Any

import structlog


def setup_logging(log_level: str = "INFO", is_production: bool = False) -> None:
    """
    Configure structlog + stdlib logging.

    Args:
        log_level:     Standard Python log level string (INFO, DEBUG, …).
        is_production: If True, emit JSON-formatted log lines.
                       If False, use the pretty developer console renderer.
    """
    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    if is_production:
        renderer: Any = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=shared_processors + [renderer],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Wire stdlib logging into structlog so third-party libraries
    # (FastAPI, uvicorn, APScheduler) also produce structured output.
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper(), logging.INFO),
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """
    Convenience wrapper — identical to structlog.get_logger() but typed.

    Args:
        name: Usually __name__ of the calling module.

    Returns:
        A bound structlog logger.
    """
    return structlog.get_logger(name)  # type: ignore[return-value]
