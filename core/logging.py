"""
Structured logging configuration.

Provides centralized logging with support for console and file output,
JSON formatting for production, and correlation IDs for request tracing.
"""

from __future__ import annotations

import json
import logging
import logging.handlers
import sys
from datetime import datetime, timezone

from config import settings

# Attributes that exist on every LogRecord by default. Anything else set
# on the record (i.e. passed via `extra={...}`) is "custom" and should be
# surfaced in the JSON output.
_STANDARD_RECORD_ATTRS = frozenset(logging.LogRecord(
    "", 0, "", 0, "", (), None
).__dict__.keys()) | {"message", "asctime"}


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging.

    Every field passed via `logger.info(..., extra={...})` is included in
    the output automatically - the previous version only special-cased
    `correlation_id` and `user_id`, which meant fields like `method`,
    `path`, `status_code`, `duration_ms`, and `error` (used throughout the
    middleware and API layers) were silently dropped whenever JSON logging
    was enabled.
    """

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Pull in every extra field the caller attached, whatever it's named.
        for key, value in record.__dict__.items():
            if key not in _STANDARD_RECORD_ATTRS and key not in log_data:
                log_data[key] = value

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data, default=str)


def configure_logging() -> None:
    """Configure logging based on settings."""

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.getLevelName(settings.logging.level))

    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    formatter = (
        JSONFormatter()
        if settings.logging.use_json
        else logging.Formatter(settings.logging.format)
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.getLevelName(settings.logging.level))
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    if settings.logging.file:
        # Rotating, not a plain FileHandler, so a long-running process
        # doesn't grow one log file without bound.
        file_handler = logging.handlers.RotatingFileHandler(
            settings.logging.file,
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5,
        )
        file_handler.setLevel(logging.getLevelName(settings.logging.level))
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # Suppress noisy third-party loggers.
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance."""
    return logging.getLogger(name)