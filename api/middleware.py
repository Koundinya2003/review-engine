"""
API middleware for request/response handling.

Provides request logging, correlation IDs, rate limiting, and security headers.
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Callable

from fastapi import Request, Response
from sqlalchemy.exc import SQLAlchemyError
from starlette.middleware.base import BaseHTTPMiddleware

from core import AppException, DatabaseError, get_logger

logger = get_logger(__name__)

# Trusted proxies for X-Forwarded-For header validation
TRUSTED_PROXIES = {"127.0.0.1", "localhost"}


def get_client_ip(request: Request) -> str:
    """Extract client IP, accounting for reverse proxies.
    
    Only trusts X-Forwarded-For header if request came from trusted proxy.
    """
    # Check for X-Forwarded-For header (set by reverse proxy)
    if "X-Forwarded-For" in request.headers:
        # Only trust if request came from trusted proxy
        if request.client and request.client.host in TRUSTED_PROXIES:
            # X-Forwarded-For can contain multiple IPs, take first
            return request.headers["X-Forwarded-For"].split(",")[0].strip()
    
    # Fall back to direct connection IP
    return request.client.host if request.client else "unknown"


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """Add correlation IDs to all requests."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add correlation ID to request."""
        correlation_id = request.headers.get("X-Correlation-ID")
        if not correlation_id:
            correlation_id = str(uuid.uuid4())
        
        request.state.correlation_id = correlation_id
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log all HTTP requests and responses."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Log request and response."""
        start_time = time.time()
        correlation_id = getattr(request.state, "correlation_id", "unknown")
        
        # Log request
        logger.info(
            f"{request.method} {request.url.path}",
            extra={
                "correlation_id": correlation_id,
                "method": request.method,
                "path": request.url.path,
                "client": request.client.host if request.client else "unknown",
            },
        )
        
        try:
            response = await call_next(request)
            duration = time.time() - start_time
            
            # Log response
            logger.info(
                f"{request.method} {request.url.path} - {response.status_code}",
                extra={
                    "correlation_id": correlation_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": round(duration * 1000),
                },
            )
            
            return response
        
        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                f"{request.method} {request.url.path} - ERROR",
                extra={
                    "correlation_id": correlation_id,
                    "method": request.method,
                    "path": request.url.path,
                    "error": str(e),
                    "duration_ms": round(duration * 1000),
                },
                exc_info=True,
            )
            raise


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add security headers."""
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple rate limiting middleware with proxy-aware client detection."""
    
    def __init__(self, app, requests_per_minute: int = 100):
        """Initialize with rate limit."""
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.request_times: dict[str, list[float]] = {}
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Rate limit requests using validated client IP."""
        client_ip = get_client_ip(request)  # Use proxy-aware IP detection
        current_time = time.time()
        
        # Clean old entries (older than 1 minute)
        if client_ip in self.request_times:
            self.request_times[client_ip] = [
                t for t in self.request_times[client_ip]
                if current_time - t < 60
            ]
        else:
            self.request_times[client_ip] = []
        
        # Check rate limit
        if len(self.request_times[client_ip]) >= self.requests_per_minute:
            return Response(
                content="Rate limit exceeded",
                status_code=429,
                headers={"Retry-After": "60"},
            )
        
        self.request_times[client_ip].append(current_time)
        return await call_next(request)


async def exception_handler(request: Request, exc: AppException) -> Response:
    """Handle application exceptions."""
    correlation_id = getattr(request.state, "correlation_id", "unknown")
    
    logger.error(
        f"Application error: {exc.message}",
        extra={
            "correlation_id": correlation_id,
            "error_code": exc.code.name,
            "status_code": exc.status_code,
            "details": exc.details,
        },
    )
    
    from fastapi import JSONResponse
    
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
    """Handle database exceptions."""
    correlation_id = getattr(request.state, "correlation_id", "unknown")
    
    logger.error(
        "Database error",
        extra={
            "correlation_id": correlation_id,
            "error": str(exc),
        },
        exc_info=True,
    )
    
    from fastapi import JSONResponse
    
    # Don't expose raw database errors to client
    return JSONResponse(
        status_code=500,
        content={
            "error": "DATABASE_ERROR",
            "message": "Database operation failed",
            "correlation_id": correlation_id,
        },
    )


async def general_exception_handler(request: Request, exc: Exception) -> Response:
    """Handle all other exceptions."""
    correlation_id = getattr(request.state, "correlation_id", "unknown")
    
    logger.error(
        "Unexpected error",
        extra={
            "correlation_id": correlation_id,
            "error": str(exc),
        },
        exc_info=True,
    )
    
    from fastapi import JSONResponse
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "INTERNAL_ERROR",
            "message": "Internal server error",
            "correlation_id": correlation_id,
        },
    )
