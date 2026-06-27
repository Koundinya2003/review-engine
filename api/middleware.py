"""
API middleware for request/response handling.

Provides request logging, correlation IDs, rate limiting, and security headers.
"""

from __future__ import annotations

import ipaddress
import time
import uuid
from collections import deque
from typing import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from core import AppException, DatabaseError, get_logger

logger = get_logger(__name__)

# Trusted proxies for X-Forwarded-For header validation.
# Supports both individual IPs and CIDR ranges.
TRUSTED_PROXY_NETWORKS = [
    ipaddress.ip_network("127.0.0.1/32"),
    ipaddress.ip_network("::1/128"),
]

# How long a rate-limit window lasts, and how often stale client
# entries are purged from memory entirely (not just their timestamps).
RATE_LIMIT_WINDOW_SECONDS = 60
RATE_LIMIT_SWEEP_INTERVAL_SECONDS = 300


def get_correlation_id(request: Request) -> str:
    """Read the correlation ID stashed on request.state, if any."""
    return getattr(request.state, "correlation_id", "unknown")


def get_client_ip(request: Request) -> str:
    """Extract the client IP, accounting for reverse proxies.

    Only trusts the X-Forwarded-For header if the immediate connection
    came from a network in TRUSTED_PROXY_NETWORKS.
    """
    forwarded_for = request.headers.get("X-Forwarded-For")
    direct_host = request.client.host if request.client else None

    if forwarded_for and direct_host:
        try:
            direct_ip = ipaddress.ip_address(direct_host)
        except ValueError:
            direct_ip = None

        if direct_ip and any(direct_ip in net for net in TRUSTED_PROXY_NETWORKS):
            # X-Forwarded-For may contain a chain of IPs; the first is the client.
            return forwarded_for.split(",")[0].strip()

    return direct_host or "unknown"


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """Attach a correlation ID to every request and echo it back."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
        request.state.correlation_id = correlation_id

        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log every HTTP request and its outcome."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.monotonic()
        correlation_id = get_correlation_id(request)
        client_ip = get_client_ip(request)

        logger.info(
            f"{request.method} {request.url.path}",
            extra={
                "correlation_id": correlation_id,
                "method": request.method,
                "path": request.url.path,
                "client": client_ip,
            },
        )

        try:
            response = await call_next(request)
        except Exception as e:
            duration_ms = round((time.monotonic() - start_time) * 1000)
            logger.error(
                f"{request.method} {request.url.path} - ERROR",
                extra={
                    "correlation_id": correlation_id,
                    "method": request.method,
                    "path": request.url.path,
                    "error": str(e),
                    "duration_ms": duration_ms,
                },
                exc_info=True,
            )
            raise

        duration_ms = round((time.monotonic() - start_time) * 1000)
        logger.info(
            f"{request.method} {request.url.path} - {response.status_code}",
            extra={
                "correlation_id": correlation_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Attach standard security headers to every response."""

    SECURITY_HEADERS = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
        # X-XSS-Protection is deprecated/ignored by modern browsers in favor
        # of CSP; omitted rather than cargo-culted in. Add a Content-Security-Policy
        # tailored to your app if you serve any HTML/JS from this service.
    }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        for header, value in self.SECURITY_HEADERS.items():
            response.headers[header] = value
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """In-memory sliding-window rate limiter, keyed by client IP.

    Note: this state is per-process. Behind multiple workers/replicas,
    each process enforces its own independent limit. For a real distributed
    limit, back this with Redis (e.g. INCR + EXPIRE, or a sorted set) instead.
    """

    def __init__(self, app: ASGIApp, requests_per_minute: int = 100) -> None:
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.request_times: dict[str, deque[float]] = {}
        self._last_sweep = time.monotonic()

    def _prune_client(self, client_ip: str, now: float) -> deque[float]:
        """Drop timestamps outside the current window for one client."""
        times = self.request_times.setdefault(client_ip, deque())
        while times and now - times[0] >= RATE_LIMIT_WINDOW_SECONDS:
            times.popleft()
        return times

    def _sweep_idle_clients(self, now: float) -> None:
        """Periodically drop clients with no recent activity, so the dict
        doesn't grow unbounded with one-off visitors."""
        if now - self._last_sweep < RATE_LIMIT_SWEEP_INTERVAL_SECONDS:
            return
        self._last_sweep = now
        idle = [ip for ip, times in self.request_times.items() if not times]
        for ip in idle:
            del self.request_times[ip]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        client_ip = get_client_ip(request)
        now = time.monotonic()

        times = self._prune_client(client_ip, now)
        self._sweep_idle_clients(now)

        if len(times) >= self.requests_per_minute:
            return Response(
                content="Rate limit exceeded",
                status_code=429,
                headers={"Retry-After": str(RATE_LIMIT_WINDOW_SECONDS)},
            )

        times.append(now)
        return await call_next(request)


async def exception_handler(request: Request, exc: AppException) -> Response:
    """Handle application-level exceptions with a structured JSON body."""
    correlation_id = get_correlation_id(request)

    logger.error(
        f"Application error: {exc.message}",
        extra={
            "correlation_id": correlation_id,
            "error_code": exc.code.name,
            "status_code": exc.status_code,
            "details": exc.details,
        },
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.code.name,
            "message": exc.message,
            "status_code": exc.status_code,
            "details": exc.details,
            "correlation_id": correlation_id,
        },
    )


async def db_exception_handler(request: Request, exc: SQLAlchemyError) -> Response:
    """Handle database exceptions without leaking internal details."""
    correlation_id = get_correlation_id(request)

    logger.error(
        "Database error",
        extra={"correlation_id": correlation_id, "error": str(exc)},
        exc_info=True,
    )

    return JSONResponse(
        status_code=500,
        content={
            "error": "DATABASE_ERROR",
            "message": "Database operation failed",
            "correlation_id": correlation_id,
        },
    )


async def general_exception_handler(request: Request, exc: Exception) -> Response:
    """Catch-all handler for anything not covered above."""
    correlation_id = get_correlation_id(request)

    logger.error(
        "Unexpected error",
        extra={"correlation_id": correlation_id, "error": str(exc)},
        exc_info=True,
    )

    return JSONResponse(
        status_code=500,
        content={
            "error": "INTERNAL_ERROR",
            "message": "Internal server error",
            "correlation_id": correlation_id,
        },
    )