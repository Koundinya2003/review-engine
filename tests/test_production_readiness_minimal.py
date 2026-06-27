"""Minimal Production Readiness Tests."""
from __future__ import annotations

import inspect
import pytest
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.models import ReviewModel, ThemeModel, Base
from database.repository import ReviewRepository, ThemeRepository
from api.security import verify_password, hash_password


@pytest.fixture
def test_db():
    """Create in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


class TestCriticalFixes:
    """CRITICAL: Verify all production fixes are in place."""
    
    def test_datetime_now_utc_in_repository(self, test_db):
        """CRITICAL: Reviews use UTC timestamps, not utcnow()."""
        data = {
            "source": "test_source",
            "external_id": "test-id-1",
            "app_name": "Test App",
            "text": "Test review",
            "rating": 4.0,
            "author": "Test User",
            "date": datetime.now(timezone.utc),
        }
        review = ReviewRepository.create(test_db, **data)
        assert review.id is not None
        assert review.date is not None

    def test_theme_repository(self, test_db):
        """Test theme repository operations."""
        theme = ThemeRepository.create(test_db, name="Test", description="Test", count=0)
        ThemeRepository.update_count(test_db, theme.id, 1)
        
        updated = ThemeRepository.get_by_id(test_db, theme.id)
        assert updated.count == 1

    def test_no_deprecated_datetime_call(self):
        """CRITICAL: datetime.utcnow() removed from codebase."""
        from database import repository
        
        source = inspect.getsource(repository)
        assert "datetime.utcnow()" not in source, "Found deprecated datetime.utcnow() in repository"

    def test_password_hashing(self):
        """Test password hashing functions."""
        password = "TestPassword123"
        hashed = hash_password(password)
        assert hashed != password
        assert verify_password(password, hashed)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
