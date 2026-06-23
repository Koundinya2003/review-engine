"""
Tests for database repository patterns.

Tests for ReviewRepository, ThemeRepository, and UserRepository.
"""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from database.models import ReviewModel
from database.repository import ReviewRepository, ThemeRepository
from database.auth_models import UserRepository
from database.schemas import ReviewCreate


class TestReviewRepository:
    """Tests for ReviewRepository."""

    @pytest.mark.unit
    @pytest.mark.database
    def test_create_review(self, db_session: Session):
        """Test creating review."""
        review_data = {
            "external_id": "ext-123",
            "source": "app_store",
            "app_name": "TestApp",
            "reviewer": "TestUser",
            "rating": 4.5,
            "title": "Great!",
            "text": "This is a great application.",
        }
        
        review = ReviewRepository.create_review(db_session, **review_data)
        
        assert review.id is not None
        assert review.external_id == "ext-123"
        assert review.source == "app_store"

    @pytest.mark.unit
    @pytest.mark.database
    def test_get_review_by_id(self, db_session: Session):
        """Test getting review by ID."""
        review_data = {
            "source": "app_store",
            "app_name": "App",
            "text": "Test review",
        }
        
        created = ReviewRepository.create_review(db_session, **review_data)
        fetched = ReviewRepository.get_by_id(db_session, created.id)
        
        assert fetched.id == created.id
        assert fetched.text == created.text

    @pytest.mark.unit
    @pytest.mark.database
    def test_get_review_by_external_id(self, db_session: Session):
        """Test getting review by external ID."""
        review_data = {
            "external_id": "unique-ext-id",
            "source": "app_store",
            "app_name": "App",
            "text": "Test",
        }
        
        ReviewRepository.create_review(db_session, **review_data)
        fetched = ReviewRepository.get_by_external_id(db_session, "unique-ext-id")
        
        assert fetched.external_id == "unique-ext-id"

    @pytest.mark.unit
    @pytest.mark.database
    def test_list_reviews(self, db_session: Session):
        """Test listing reviews."""
        for i in range(5):
            ReviewRepository.create_review(
                db_session,
                source="app_store",
                app_name="App",
                text=f"Review {i}",
            )
        
        reviews, total = ReviewRepository.list_reviews(db_session, limit=10)
        
        assert len(reviews) == 5
        assert total == 5

    @pytest.mark.unit
    @pytest.mark.database
    def test_list_reviews_pagination(self, db_session: Session):
        """Test review pagination."""
        for i in range(20):
            ReviewRepository.create_review(
                db_session,
                source="app_store",
                app_name="App",
                text=f"Review {i}",
            )
        
        page1, total1 = ReviewRepository.list_reviews(db_session, skip=0, limit=10)
        page2, total2 = ReviewRepository.list_reviews(db_session, skip=10, limit=10)
        
        assert len(page1) == 10
        assert len(page2) == 10
        assert total1 == 20
        assert total2 == 20

    @pytest.mark.unit
    @pytest.mark.database
    def test_list_reviews_filter_source(self, db_session: Session):
        """Test filtering reviews by source."""
        ReviewRepository.create_review(db_session, source="app_store", app_name="A", text="T1")
        ReviewRepository.create_review(db_session, source="play_store", app_name="B", text="T2")
        
        reviews, total = ReviewRepository.list_reviews(db_session, source="app_store")
        
        assert total == 1
        assert reviews[0].source == "app_store"

    @pytest.mark.unit
    @pytest.mark.database
    def test_update_review(self, db_session: Session):
        """Test updating review."""
        review = ReviewRepository.create_review(
            db_session,
            source="app_store",
            app_name="App",
            text="Original text",
        )
        
        updated = ReviewRepository.update_review(
            db_session,
            review.id,
            text="Updated text",
            theme="updated_theme",
        )
        
        assert updated.text == "Updated text"
        assert updated.theme == "updated_theme"

    @pytest.mark.unit
    @pytest.mark.database
    def test_update_embedding(self, db_session: Session):
        """Test updating review embedding."""
        review = ReviewRepository.create_review(
            db_session,
            source="app_store",
            app_name="App",
            text="Test",
        )
        
        embedding = [0.1, 0.2, 0.3]
        ReviewRepository.update_embedding(db_session, review.id, embedding)
        
        fetched = ReviewRepository.get_by_id(db_session, review.id)
        assert fetched.embedding == embedding

    @pytest.mark.unit
    @pytest.mark.database
    def test_delete_review(self, db_session: Session):
        """Test deleting review."""
        review = ReviewRepository.create_review(
            db_session,
            source="app_store",
            app_name="App",
            text="Test",
        )
        
        ReviewRepository.delete(db_session, review.id)
        fetched = ReviewRepository.get_by_id(db_session, review.id)
        
        assert fetched is None

    @pytest.mark.unit
    @pytest.mark.database
    def test_get_stats(self, db_session: Session):
        """Test getting review statistics."""
        for i in range(5):
            ReviewRepository.create_review(
                db_session,
                source="app_store",
                app_name="App",
                rating=float(i + 1),
                text=f"Review {i}",
            )
        
        stats = ReviewRepository.get_stats(db_session)
        
        assert stats["total_reviews"] == 5
        assert stats["avg_rating"] > 0


class TestThemeRepository:
    """Tests for ThemeRepository."""

    @pytest.mark.unit
    @pytest.mark.database
    def test_create_theme(self, db_session: Session):
        """Test creating theme."""
        theme = ThemeRepository.create(
            db_session,
            topic_id=1,
            theme_name="TestTheme",
            description="Test description",
            count=5,
        )
        
        assert theme.id is not None
        assert theme.theme_name == "TestTheme"
        assert theme.count == 5

    @pytest.mark.unit
    @pytest.mark.database
    def test_get_theme_by_id(self, db_session: Session):
        """Test getting theme by ID."""
        created = ThemeRepository.create(
            db_session,
            topic_id=1,
            theme_name="Theme1",
            count=3,
        )
        
        fetched = ThemeRepository.get_by_id(db_session, created.id)
        assert fetched.id == created.id

    @pytest.mark.unit
    @pytest.mark.database
    def test_get_theme_by_name(self, db_session: Session):
        """Test getting theme by name."""
        ThemeRepository.create(
            db_session,
            topic_id=1,
            theme_name="UniqueTheme",
            count=2,
        )
        
        fetched = ThemeRepository.get_by_name(db_session, "UniqueTheme")
        assert fetched.theme_name == "UniqueTheme"

    @pytest.mark.unit
    @pytest.mark.database
    def test_list_themes(self, db_session: Session):
        """Test listing themes."""
        for i in range(3):
            ThemeRepository.create(
                db_session,
                topic_id=i,
                theme_name=f"Theme{i}",
                count=i + 1,
            )
        
        themes, total = ThemeRepository.list_themes(db_session)
        
        assert len(themes) == 3
        assert total == 3

    @pytest.mark.unit
    @pytest.mark.database
    def test_update_count(self, db_session: Session):
        """Test updating theme count."""
        theme = ThemeRepository.create_theme(
            db_session,
            topic_id=1,
            theme_name="Theme",
            count=5,
        )
        
        ThemeRepository.update_count(db_session, theme.id, 10)
        
        fetched = ThemeRepository.get_by_id(db_session, theme.id)
        assert fetched.count == 10


class TestUserRepository:
    """Tests for UserRepository."""

    @pytest.mark.unit
    @pytest.mark.database
    def test_create_user(self, db_session: Session):
        """Test creating user."""
        user = UserRepository.create_user(
            db_session,
            username="testuser",
            email="test@example.com",
            hashed_password="hashedpass",
            role="viewer",
        )
        
        assert user.id is not None
        assert user.username == "testuser"
        assert user.email == "test@example.com"

    @pytest.mark.unit
    @pytest.mark.database
    def test_get_user_by_username(self, db_session: Session):
        """Test getting user by username."""
        UserRepository.create_user(
            db_session,
            username="unique_user",
            email="unique@example.com",
            hashed_password="pass",
        )
        
        user = UserRepository.get_user_by_username(db_session, "unique_user")
        assert user.username == "unique_user"

    @pytest.mark.unit
    @pytest.mark.database
    def test_get_user_by_email(self, db_session: Session):
        """Test getting user by email."""
        UserRepository.create_user(
            db_session,
            username="user1",
            email="unique@test.com",
            hashed_password="pass",
        )
        
        user = UserRepository.get_user_by_email(db_session, "unique@test.com")
        assert user.email == "unique@test.com"

    @pytest.mark.unit
    @pytest.mark.database
    def test_delete_user(self, db_session: Session):
        """Test soft deleting user."""
        user = UserRepository.create_user(
            db_session,
            username="deluser",
            email="del@example.com",
            hashed_password="pass",
        )
        
        UserRepository.delete_user(db_session, user.id)
        
        fetched = UserRepository.get_user_by_username(db_session, "deluser")
        assert fetched.is_active == 0
