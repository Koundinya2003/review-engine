"""
Core application infrastructure and utilities.

Provides foundational services, exceptions, logging, and utilities
used throughout the application.
"""

from .exceptions import (
    AppException,
    AuthenticationError,
    ConflictError,
    DatabaseError,
    ErrorCode,
    NotFoundError,
    OperationTimeoutError,
    PermissionError,
    ServiceUnavailableError,
    ValidationError,
)
from .logging import configure_logging, get_logger

__all__ = [
    # Exceptions
    "AppException",
    "AuthenticationError",
    "ConflictError",
    "DatabaseError",
    "ErrorCode",
    "NotFoundError",
    "OperationTimeoutError",
    "PermissionError",
    "ServiceUnavailableError",
    "ValidationError",
    # Logging
    "configure_logging",
    "get_logger",
]
