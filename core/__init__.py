"""
Core application infrastructure and utilities.

Provides foundational services, exceptions, logging, and utilities
used throughout the application.
"""

from .exceptions import (
    AppException,
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    DatabaseError,
    ErrorCode,
    NotFoundError,
    OperationTimeoutError,
    ServiceUnavailableError,
    ValidationError,
)
from .logging import configure_logging, get_logger
from .metrics import get_metrics

__all__ = [
    # Exceptions
    "AppException",
    "AuthenticationError",
    "AuthorizationError",
    "ConflictError",
    "DatabaseError",
    "ErrorCode",
    "NotFoundError",
    "OperationTimeoutError",
    "ServiceUnavailableError",
    "ValidationError",
    # Logging
    "configure_logging",
    "get_logger",
    # Metrics
    "get_metrics",
]