"""
API security module for authentication and authorization.

Provides JWT token handling, password hashing, and permission checking.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from config import settings
from core import get_logger

logger = get_logger(__name__)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT security
security = HTTPBearer(auto_error=False)

# Role hierarchy, defined once and shared by every permission check.
ROLE_HIERARCHY: dict[str, int] = {
    "admin": 3,
    "analyst": 2,
    "viewer": 1,
}

# Sentinel id used for the "system" identity when auth is disabled.
SYSTEM_USER_ID = 0


class CurrentUser(BaseModel):
    """Decoded identity carried by the access token (or the system identity
    when authentication is disabled)."""

    user_id: int
    role: str
    scopes: list[str] = []


def hash_password(password: str) -> str:
    """Hash a plaintext password for storage."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Check a plaintext password against a stored hash."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a signed JWT access token."""
    to_encode = data.copy()

    expire = datetime.now(timezone.utc) + (
        expires_delta
        if expires_delta is not None
        else timedelta(minutes=settings.auth.access_token_expire_minutes)
    )
    to_encode.update({"exp": expire})

    return jwt.encode(
        to_encode,
        settings.auth.secret_key,
        algorithm=settings.auth.algorithm,
    )


def verify_token(token: str) -> dict:
    """Decode and validate a JWT, raising 401 on any failure."""
    try:
        return jwt.decode(
            token,
            settings.auth.secret_key,
            algorithms=[settings.auth.algorithm],
        )
    except JWTError as e:
        logger.warning("token_verification_failed", extra={"error": str(e)})
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> CurrentUser:
    """Resolve the authenticated identity for the current request.

    Returns a fixed "system" identity when authentication is disabled,
    otherwise decodes and validates the bearer token.
    """
    if not settings.auth.enabled:
        return CurrentUser(user_id=SYSTEM_USER_ID, role="admin", scopes=[])

    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication",
        )

    payload = verify_token(credentials.credentials)

    raw_user_id = payload.get("sub")
    if raw_user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    try:
        user_id = int(raw_user_id)
    except (TypeError, ValueError):
        logger.warning("token_invalid_subject", extra={"sub": raw_user_id})
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    return CurrentUser(
        user_id=user_id,
        role=payload.get("role", "viewer"),
        scopes=payload.get("scopes", []),
    )


def require_role(required_role: str):
    """Dependency factory: require at least the given role level."""

    required_level = ROLE_HIERARCHY.get(required_role, 0)

    async def role_checker(
        current_user: CurrentUser = Depends(get_current_user),
    ) -> CurrentUser:
        user_level = ROLE_HIERARCHY.get(current_user.role, 0)

        if user_level < required_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )

        return current_user

    return role_checker


def require_scope(required_scope: str):
    """Dependency factory: require a specific scope on the token."""

    async def scope_checker(
        current_user: CurrentUser = Depends(get_current_user),
    ) -> CurrentUser:
        if required_scope not in current_user.scopes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )

        return current_user

    return scope_checker