"""
Pytest configuration and shared fixtures for all tests.

Provides database, API client, and authentication fixtures used across
unit and integration tests.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from api.main import app
from database.connection import get_session
from database.models import Base, ReviewModel, ThemeModel
from database.schemas import ReviewCreate


# ============================================================================
# DATABASE FIXTURES
# ============================================================================

@pytest.fixture(scope="function")
def db_engine():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=None,  # Disable connection pooling for in-memory DB
    )
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture(scope="function")
def db_session(db_engine):
    """Create a database session for a test."""
    SessionLocal = sessionmaker(bind=db_engine)
    session = SessionLocal()
    
    # Override the dependency
    def get_session_override():
        return session
    
    app.dependency_overrides[get_session] = get_session_override
    
    yield session
    
    session.close()
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def test_db():
    """Deprecated: Use db_session instead."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


# ============================================================================
# API CLIENT FIXTURES
# ============================================================================

@pytest.fixture(scope="function")
def client(db_session: Session):
    """FastAPI test client with database session overridden."""
    return TestClient(app)


# ============================================================================
# AUTHENTICATION FIXTURES
# ============================================================================

@pytest.fixture(scope="function")
def auth_headers(client: TestClient) -> dict[str, str]:
    """Generate valid authentication headers."""
    # Note: This assumes auth is not enforced or uses test credentials
    # Modify based on your actual authentication implementation
    return {
        "Authorization": "Bearer test-token",
        "Content-Type": "application/json",
    }


# ============================================================================
# SAMPLE DATA FIXTURES
# ============================================================================

@pytest.fixture(scope="function")
def sample_review_data() -> dict:
    """Provide sample review data for tests."""
    return {
        "source": "test_source",
        "external_id": "test-review-id-123",
        "app_name": "Test App",
        "text": "This is a test review.",
        "rating": 4.5,
        "author": "Test User",
        "date": datetime.now(timezone.utc),
    }


@pytest.fixture(scope="function")
def sample_reviews(db_session: Session, sample_review_data: dict) -> list[ReviewModel]:
    """Create sample reviews in the database."""
    reviews = []
    for i in range(5):
        data = sample_review_data.copy()
        data["external_id"] = f"test-review-{i}"
        data["rating"] = 2.0 + (i * 0.5)
        
        review = ReviewModel(**data)
        db_session.add(review)
        reviews.append(review)
    
    db_session.commit()
    return reviews


@pytest.fixture(scope="function")
def sample_themes(db_session: Session) -> list[ThemeModel]:
    """Create sample themes in the database."""
    themes = []
    theme_names = ["Performance", "UI/UX", "Bug Reports", "Feature Requests"]
    
    for i, name in enumerate(theme_names):
        theme = ThemeModel(
            name=name,
            description=f"Theme for {name.lower()}",
            count=10 + (i * 5),
        )
        db_session.add(theme)
        themes.append(theme)
    
    db_session.commit()
    return themes


# ============================================================================
# MARKER CONFIGURATION
# ============================================================================

def pytest_configure(config):
    """Register custom markers."""
    markers = [
        "unit: Unit tests",
        "integration: Integration tests",
        "api: API tests",
        "database: Database tests",
        "service: Service tests",
        "slow: Slow tests",
        "async: Async tests",
    ]
    for marker_name, marker_desc in (m.split(": ") for m in markers):
        config.addinivalue_line("markers", f"{marker_name}: {marker_desc}")
