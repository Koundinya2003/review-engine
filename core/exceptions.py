"""
Application exception hierarchy.

Defines custom exceptions for different error scenarios with proper
error codes and user-friendly messages.
"""

from __future__ import annotations

from enum import Enum


class ErrorCode(str, Enum):
    """Standard error codes."""

    # Validation
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_INPUT = "INVALID_INPUT"

    # Authentication
    AUTH_REQUIRED = "AUTH_REQUIRED"
    AUTH_FAILED = "AUTH_FAILED"
    INSUFFICIENT_PERMISSIONS = "INSUFFICIENT_PERMISSIONS"

    # Resources
    NOT_FOUND = "NOT_FOUND"
    ALREADY_EXISTS = "ALREADY_EXISTS"
    CONFLICT = "CONFLICT"

    # Operations
    OPERATION_FAILED = "OPERATION_FAILED"
    OPERATION_TIMEOUT = "OPERATION_TIMEOUT"
    OPERATION_UNAVAILABLE = "OPERATION_UNAVAILABLE"

    # Database
    DB_ERROR = "DB_ERROR"
    DB_CONNECTION_ERROR = "DB_CONNECTION_ERROR"

    # External services
    SERVICE_ERROR = "SERVICE_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"

    # Generic
    INTERNAL_ERROR = "INTERNAL_ERROR"


class AppException(Exception):
    """Base application exception.

    Every subclass accepts an optional `details` dict so callers always
    have a consistent way to attach structured context, instead of some
    exceptions supporting it and others silently dropping it.
    """

    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.INTERNAL_ERROR,
        status_code: int = 500,
        details: dict | None = None,
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)

    def to_dict(self) -> dict:
        """Serialize to the shape used by the API's exception handlers."""
        return {
            "error": self.code.name,
            "message": self.message,
            "status_code": self.status_code,
            "details": self.details,
        }


class ValidationError(AppException):
    """Raised when validation fails."""

    def __init__(self, message: str, details: dict | None = None):
        super().__init__(
            message=message,
            code=ErrorCode.VALIDATION_ERROR,
            status_code=422,
            details=details,
        )


class NotFoundError(AppException):
    """Raised when a resource is not found."""

    def __init__(self, message: str, resource_type: str = "", details: dict | None = None):
        super().__init__(
            message=message,
            code=ErrorCode.NOT_FOUND,
            status_code=404,
            details={"resource_type": resource_type, **(details or {})},
        )


class AuthenticationError(AppException):
    """Raised when authentication fails (no/invalid/expired credentials)."""

    def __init__(self, message: str = "Authentication required", details: dict | None = None):
        super().__init__(
            message=message,
            code=ErrorCode.AUTH_FAILED,
            status_code=401,
            details=details,
        )


class AuthorizationError(AppException):
    """Raised when an authenticated user lacks permission for an action.

    NOTE: this was previously named `PermissionError`, which shadowed the
    Python builtin of the same name (raised for OS-level permission
    failures, e.g. file access). Any code importing `core.PermissionError`
    needs to be updated to `core.AuthorizationError`.
    """

    def __init__(self, message: str = "Insufficient permissions", details: dict | None = None):
        super().__init__(
            message=message,
            code=ErrorCode.INSUFFICIENT_PERMISSIONS,
            status_code=403,
            details=details,
        )


class DatabaseError(AppException):
    """Raised when a database operation fails."""

    def __init__(self, message: str, details: dict | None = None):
        super().__init__(
            message=message,
            code=ErrorCode.DB_ERROR,
            status_code=500,
            details=details,
        )


class ServiceUnavailableError(AppException):
    """Raised when a dependent service is unavailable."""

    def __init__(self, message: str, details: dict | None = None):
        super().__init__(
            message=message,
            code=ErrorCode.SERVICE_UNAVAILABLE,
            status_code=503,
            details=details,
        )


class OperationTimeoutError(AppException):
    """Raised when an operation times out."""

    def __init__(self, message: str, details: dict | None = None):
        super().__init__(
            message=message,
            code=ErrorCode.OPERATION_TIMEOUT,
            status_code=504,
            details=details,
        )


class ConflictError(AppException):
    """Raised when there's a conflict (e.g. duplicate resource)."""

    def __init__(self, message: str, details: dict | None = None):
        super().__init__(
            message=message,
            code=ErrorCode.CONFLICT,
            status_code=409,
            details=details,
        )