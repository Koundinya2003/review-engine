"""
Pytest configuration and fixtures for all tests.

Provides fixtures for database, services, API client, and mock data.
"""

from __future__ import annotations

import os
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from api.main import app
from config import Settings, settings
from core import get_logger
from database.connection import get_session
from database.models import Base, init_db
from services import AnalyticsService, ClusteringService, ReviewService, VectorService

logger = get_logger(__name__)


# ============================================================================
# SESSION SCOPE FIXTURES
# ============================================================================

@pytest.fixture(scope="session")
def test_db_url():
    """Test database URL (SQLite in-memory)."""
    return "sqlite:///:memory:"


@pytest.fixture(scope="session")
def test_engine(test_db_url):
    """Create test database engine."""
    engine = create_engine(test_db_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture(scope="session")
def test_session_factory(test_engine):
    """Create session factory for tests."""
    return sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


# ============================================================================
# FUNCTION SCOPE FIXTURES
# ============================================================================

@pytest.fixture
def db_session(test_session_factory) -> Generator[Session, None, None]:
    """Provide database session for each test."""
    session = test_session_factory()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def client(db_session):
    """Provide FastAPI test client with test database."""
    def override_get_session():
        return db_session
    
    app.dependency_overrides[get_session] = override_get_session
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers(client):
    """Get authentication headers with valid JWT token."""
    # Register user
    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "testpass123",
        },
    )
    assert register_response.status_code == 200
    token = register_response.json()["access_token"]
    
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_headers(client):
    """Get authentication headers for admin user."""
    # For testing, we'll mock an admin token
    from api.security import create_access_token
    
    token = create_access_token(data={"sub": "1", "role": "admin"})
    return {"Authorization": f"Bearer {token}"}


# ============================================================================
# MOCK DATA FIXTURES
# ============================================================================

@pytest.fixture
def sample_review_data():
    """Sample review data for testing."""
    return {
        "external_id": "test-review-1",
        "source": "app_store",
        "app_name": "TestApp",
        "reviewer": "TestUser",
        "rating": 4.5,
        "title": "Great app!",
        "text": "This is a great application with excellent features.",
        "date": "2024-01-01T00:00:00",
        "url": "https://example.com/review",
        "metadata": {"device": "iPhone"},
    }


@pytest.fixture
def sample_reviews_batch():
    """Batch of sample reviews for bulk testing."""
    return [
        {
            "source": "app_store",
            "app_name": "TestApp",
            "reviewer": f"User{i}",
            "rating": float(i % 5 + 1),
            "title": f"Review {i}",
            "text": f"This is review number {i} with test content.",
            "date": f"2024-01-{str(i+1).zfill(2)}T00:00:00",
        }
        for i in range(10)
    ]


@pytest.fixture
def sample_search_query():
    """Sample search query for testing."""
    return "excellent features and great user experience"


# ============================================================================
# SERVICE FIXTURES
# ============================================================================

@pytest.fixture
def review_service():
    """Provide ReviewService for testing."""
    return ReviewService


@pytest.fixture
def vector_service():
    """Provide VectorService for testing."""
    return VectorService


@pytest.fixture
def clustering_service():
    """Provide ClusteringService for testing."""
    return ClusteringService


@pytest.fixture
def analytics_service():
    """Provide AnalyticsService for testing."""
    return AnalyticsService


# ============================================================================
# UTILITY FIXTURES
# ============================================================================

@pytest.fixture
def clear_db(db_session):
    """Clear database before each test."""
    from database.models import ReviewModel, ThemeModel
    from database.auth_models import UserModel
    
    db_session.query(ReviewModel).delete()
    db_session.query(ThemeModel).delete()
    db_session.query(UserModel).delete()
    db_session.commit()
    
    yield
    
    db_session.query(ReviewModel).delete()
    db_session.query(ThemeModel).delete()
    db_session.query(UserModel).delete()
    db_session.commit()


# ============================================================================
# PYTEST HOOKS
# ============================================================================

def pytest_configure(config):
    """Configure pytest."""
    logger.info("Test session started")


def pytest_unconfigure(config):
    """Cleanup after pytest."""
    logger.info("Test session completed")


def pytest_collection_modifyitems(config, items):
    """Modify test collection."""
    for item in items:
        # Mark async tests
        if "async" in item.nodeid.lower():
            item.add_marker(pytest.mark.asyncio)
        
        # Add markers based on file location
        if "unit" in item.nodeid:
            item.add_marker(pytest.mark.unit)
        elif "integration" in item.nodeid:
            item.add_marker(pytest.mark.integration)
