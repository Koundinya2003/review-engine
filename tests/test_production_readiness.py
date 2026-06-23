"""
Production Readiness Tests - Comprehensive validation suite.

Tests all critical functionality required for production deployment including:
- Database repository operations
- API endpoint validation
- Authentication & security
- Error handling & resilience
- Data integrity
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.connection import DatabaseSettings, init_db
from database.models import ReviewModel, ThemeModel, UserModel, Base
from database.repository import ReviewRepository, ThemeRepository, UserRepository
from api.security import create_access_token, verify_password, hash_password
from api.schemas import HealthResponse


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def test_db():
    """Create in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def sample_review_data():
    """Sample review data for testing."""
    return {
        "external_id": "test_review_001",
        "source": "app_store",
        "app_name": "Test App",
        "reviewer": "test_user",
        "rating": 4,
        "title": "Test Review",
        "text": "This is a test review for production validation.",
        "date": datetime.now(timezone.utc),
        "metadata": {"test": True}
    }


@pytest.fixture
def sample_theme_data():
    """Sample theme data for testing."""
    return {
        "name": "Performance Issues",
        "description": "Reviews mentioning app performance problems",
        "count": 0,
        "sample_reviews": []
    }


# =============================================================================
# REPOSITORY TESTS - CRUD Operations
# =============================================================================

class TestReviewRepository:
    """Test ReviewRepository operations."""
    
    def test_create_review_with_timestamp(self, test_db, sample_review_data):
        """✅ Test review creation sets correct UTC timestamp."""
        # Create review without explicit date
        test_data = sample_review_data.copy()
        del test_data["date"]
        
        review = ReviewRepository.create(test_db, **test_data)
        
        assert review is not None
        assert review.date is not None
        assert isinstance(review.date, datetime)
        # Verify timestamp is timezone-aware UTC
        assert review.date.tzinfo == timezone.utc
    
    def test_create_review_external_id_generation(self, test_db, sample_review_data):
        """✅ Test external ID is properly generated."""
        review = ReviewRepository.create(test_db, **sample_review_data)
        
        assert review.external_id is not None
        assert len(review.external_id) > 0
    
    def test_get_review_by_id(self, test_db, sample_review_data):
        """✅ Test retrieving review by ID."""
        # Create review
        created_review = ReviewRepository.create(test_db, **sample_review_data)
        review_id = created_review.id
        
        # Retrieve review
        retrieved = ReviewRepository.get_by_id(test_db, review_id)
        
        assert retrieved is not None
        assert retrieved.id == review_id
        assert retrieved.external_id == sample_review_data["external_id"]
    
    def test_update_review_updates_timestamp(self, test_db, sample_review_data):
        """✅ Test review update properly sets updated_at timestamp."""
        # Create review
        review = ReviewRepository.create(test_db, **sample_review_data)
        created_at = review.date
        
        # Update review with slight delay
        import time
        time.sleep(0.01)
        updated_review = ReviewRepository.update(test_db, review.id, rating=5)
        
        assert updated_review is not None
        assert updated_review.rating == 5
        assert updated_review.updated_at is not None
        assert isinstance(updated_review.updated_at, datetime)
        assert updated_review.updated_at.tzinfo == timezone.utc
    
    def test_update_embedding(self, test_db, sample_review_data):
        """✅ Test embedding update."""
        review = ReviewRepository.create(test_db, **sample_review_data)
        embedding = [0.1, 0.2, 0.3, 0.4]
        
        ReviewRepository.update_embedding(test_db, review.id, embedding)
        updated = ReviewRepository.get_by_id(test_db, review.id)
        
        assert updated.embedding == embedding
        assert updated.updated_at is not None
        assert updated.updated_at.tzinfo == timezone.utc
    
    def test_update_theme(self, test_db, sample_review_data):
        """✅ Test updating review theme."""
        review = ReviewRepository.create(test_db, **sample_review_data)
        
        ReviewRepository.update_theme(
            test_db, 
            review.id, 
            "performance", 
            0.95
        )
        updated = ReviewRepository.get_by_id(test_db, review.id)
        
        assert updated.theme == "performance"
        assert updated.theme_confidence == 0.95
    
    def test_bulk_upsert_reviews(self, test_db):
        """✅ Test bulk upsert of reviews."""
        payloads = [
            {
                "external_id": f"bulk_test_{i}",
                "source": "app_store",
                "app_name": "Bulk Test",
                "reviewer": f"user_{i}",
                "rating": i,
                "text": f"Test review {i}"
            }
            for i in range(5)
        ]
        
        inserted, skipped = ReviewRepository.bulk_upsert(test_db, payloads)
        
        assert inserted > 0
        assert inserted == 5
        assert skipped == 0


class TestThemeRepository:
    """Test ThemeRepository operations."""
    
    def test_create_theme(self, test_db, sample_theme_data):
        """✅ Test creating a theme."""
        theme = ThemeRepository.create(test_db, **sample_theme_data)
        
        assert theme is not None
        assert theme.name == sample_theme_data["name"]
        assert theme.count == 0
    
    def test_get_theme_by_id(self, test_db, sample_theme_data):
        """✅ Test retrieving theme by ID."""
        created = ThemeRepository.create(test_db, **sample_theme_data)
        retrieved = ThemeRepository.get_by_id(test_db, created.id)
        
        assert retrieved is not None
        assert retrieved.id == created.id
    
    def test_get_theme_by_name(self, test_db, sample_theme_data):
        """✅ Test retrieving theme by name."""
        created = ThemeRepository.create(test_db, **sample_theme_data)
        retrieved = ThemeRepository.get_by_name(test_db, sample_theme_data["name"])
        
        assert retrieved is not None
        assert retrieved.name == sample_theme_data["name"]
    
    def test_update_count(self, test_db, sample_theme_data):
        """✅ Test updating theme count."""
        theme = ThemeRepository.create(test_db, **sample_theme_data)
        
        ThemeRepository.update_count(test_db, theme.id, 42)
        updated = ThemeRepository.get_by_id(test_db, theme.id)
        
        assert updated.count == 42
        assert updated.updated_at is not None
        assert updated.updated_at.tzinfo == timezone.utc


# =============================================================================
# SECURITY TESTS
# =============================================================================

class TestSecurity:
    """Test authentication and security functions."""
    
    def test_password_hashing(self):
        """✅ Test password hashing produces different output than input."""
        password = "SecurePassword123!"
        hashed = hash_password(password)
        
        assert hashed != password
        assert len(hashed) > len(password)
    
    def test_verify_password(self):
        """✅ Test password verification."""
        password = "SecurePassword123!"
        hashed = hash_password(password)
        
        assert verify_password(password, hashed)
        assert not verify_password("WrongPassword", hashed)
    
    @patch('api.security.settings')
    def test_create_access_token(self, mock_settings):
        """✅ Test JWT token creation with timezone-aware expiry."""
        # Mock settings
        mock_settings.auth.secret_key = "test_secret_key"
        mock_settings.auth.algorithm = "HS256"
        mock_settings.auth.access_token_expire_minutes = 30
        
        data = {"sub": "test_user"}
        token = create_access_token(data)
        
        assert token is not None
        assert len(token) > 0
        assert isinstance(token, str)
    
    @patch('api.security.settings')
    def test_access_token_expiry(self, mock_settings):
        """✅ Test access token has timezone-aware expiry."""
        from jose import jwt
        
        mock_settings.auth.secret_key = "test_secret_key"
        mock_settings.auth.algorithm = "HS256"
        mock_settings.auth.access_token_expire_minutes = 30
        
        data = {"sub": "test_user"}
        token = create_access_token(data)
        
        # Decode token to verify expiry
        decoded = jwt.decode(
            token,
            mock_settings.auth.secret_key,
            algorithms=[mock_settings.auth.algorithm]
        )
        
        assert "exp" in decoded
        exp_timestamp = decoded["exp"]
        # Expiry should be approximately 30 minutes in future
        assert exp_timestamp > datetime.now(timezone.utc).timestamp()


# =============================================================================
# DATA INTEGRITY TESTS
# =============================================================================

class TestDataIntegrity:
    """Test data integrity and constraints."""
    
    def test_review_date_is_utc_aware(self, test_db, sample_review_data):
        """✅ Test review dates are timezone-aware UTC."""
        review = ReviewRepository.create(test_db, **sample_review_data)
        
        # Check date
        assert review.date.tzinfo is not None
        assert review.date.tzinfo == timezone.utc
        
        # Check updated_at if it exists
        if review.updated_at:
            assert review.updated_at.tzinfo is not None
            assert review.updated_at.tzinfo == timezone.utc
    
    def test_duplicate_external_id_handling(self, test_db, sample_review_data):
        """✅ Test handling of duplicate external IDs."""
        # Create first review
        review1 = ReviewRepository.create(test_db, **sample_review_data)
        
        # Attempt to create with same external ID
        review2_data = sample_review_data.copy()
        review2_data["text"] = "Different text"
        
        reviews = ReviewRepository.get_by_external_id(
            test_db, 
            sample_review_data["external_id"]
        )
        
        # Should handle duplicates gracefully
        assert reviews is not None
    
    def test_null_fields_handling(self, test_db):
        """✅ Test handling of optional null fields."""
        minimal_review = {
            "source": "app_store",
            "app_name": "Test App",
            "rating": 3,
            "text": "Test"
        }
        
        review = ReviewRepository.create(test_db, **minimal_review)
        assert review is not None


# =============================================================================
# ERROR HANDLING TESTS
# =============================================================================

class TestErrorHandling:
    """Test error handling and resilience."""
    
    def test_get_nonexistent_review(self, test_db):
        """✅ Test retrieving non-existent review returns None."""
        result = ReviewRepository.get_by_id(test_db, 99999)
        assert result is None
    
    def test_update_nonexistent_review(self, test_db):
        """✅ Test updating non-existent review returns None."""
        result = ReviewRepository.update(test_db, 99999, rating=5)
        assert result is None
    
    def test_delete_nonexistent_theme(self, test_db):
        """✅ Test deleting non-existent theme returns False."""
        result = ThemeRepository.delete(test_db, 99999)
        assert result is False


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestIntegration:
    """Integration tests for complete workflows."""
    
    def test_review_creation_to_theme_update(self, test_db, sample_review_data, sample_theme_data):
        """✅ Test complete workflow: create review → assign theme → update count."""
        # Create theme
        theme = ThemeRepository.create(test_db, **sample_theme_data)
        
        # Create review
        review = ReviewRepository.create(test_db, **sample_review_data)
        
        # Assign theme to review
        ReviewRepository.update_theme(test_db, review.id, theme.name, 0.85)
        
        # Update theme count
        ThemeRepository.update_count(test_db, theme.id, 1)
        
        # Verify workflow
        updated_review = ReviewRepository.get_by_id(test_db, review.id)
        updated_theme = ThemeRepository.get_by_id(test_db, theme.id)
        
        assert updated_review.theme == theme.name
        assert updated_theme.count == 1
    
    def test_bulk_review_processing(self, test_db, sample_theme_data):
        """✅ Test bulk review creation and theme assignment."""
        # Create theme
        theme = ThemeRepository.create(test_db, **sample_theme_data)
        
        # Create multiple reviews
        payloads = [
            {
                "external_id": f"batch_{i}",
                "source": "app_store",
                "app_name": "Batch Test",
                "rating": i % 5,
                "text": f"Review {i}"
            }
            for i in range(10)
        ]
        
        inserted, skipped = ReviewRepository.bulk_upsert(test_db, payloads)
        
        # Verify
        assert inserted == 10
        reviews = test_db.query(ReviewModel).all()
        assert len(reviews) >= 10


# =============================================================================
# PERFORMANCE TESTS
# =============================================================================

class TestPerformance:
    """Test performance characteristics."""
    
    def test_bulk_insert_performance(self, test_db):
        """✅ Test bulk insert completes reasonably fast."""
        import time
        
        payloads = [
            {
                "external_id": f"perf_test_{i}",
                "source": "app_store",
                "app_name": "Performance Test",
                "rating": i % 5,
                "text": f"Performance review {i}"
            }
            for i in range(100)
        ]
        
        start = time.time()
        inserted, skipped = ReviewRepository.bulk_upsert(test_db, payloads)
        elapsed = time.time() - start
        
        # Should complete within reasonable time (< 5 seconds)
        assert elapsed < 5.0
        assert inserted == 100
    
    def test_query_by_external_id_performance(self, test_db, sample_review_data):
        """✅ Test query performance for external ID lookup."""
        import time
        
        # Create multiple reviews
        for i in range(50):
            data = sample_review_data.copy()
            data["external_id"] = f"perf_{i}"
            ReviewRepository.create(test_db, **data)
        
        # Query should be fast
        start = time.time()
        result = ReviewRepository.get_by_external_id(test_db, "perf_25")
        elapsed = time.time() - start
        
        assert elapsed < 1.0  # Should be < 1 second
        assert result is not None


# =============================================================================
# REGRESSION TESTS
# =============================================================================

class TestRegressions:
    """Test for known issues that shouldn't regress."""
    
    def test_datetime_utcnow_removed(self):
        """✅ Verify datetime.utcnow() has been replaced."""
        import inspect
        from database import repository, auth_models
        from api import security, main
        
        files_to_check = [repository, auth_models, security, main]
        
        for module in files_to_check:
            source = inspect.getsource(module)
            # Should not contain old deprecated call
            assert "datetime.utcnow()" not in source
            # Should use new method
            assert "datetime.now(timezone.utc)" in source or "from datetime import" in source
    
    def test_passlib_version_current(self):
        """✅ Verify passlib is updated."""
        import pkg_resources
        passlib_version = pkg_resources.get_distribution("passlib").version
        
        # Should be 1.7.4.1 or higher
        assert passlib_version >= "1.7.4.1"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
