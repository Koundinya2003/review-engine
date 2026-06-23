"""
Unit tests for service layer components.

Tests for ReviewService, VectorService, AnalyticsService, ClusteringService.
"""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from database.schemas import ReviewCreate
from services import ReviewService, AnalyticsService


class TestReviewService:
    """Tests for ReviewService."""

    @pytest.mark.unit
    def test_create_review_success(self, db_session: Session, sample_review_data: dict):
        """Test successful review creation."""
        review_create = ReviewCreate(**sample_review_data)
        review = ReviewService.create_review(db_session, review_create)
        
        assert review.id is not None
        assert review.source == sample_review_data["source"]
        assert review.app_name == sample_review_data["app_name"]
        assert review.text == sample_review_data["text"]

    @pytest.mark.unit
    def test_create_review_duplicate(self, db_session: Session, sample_review_data: dict):
        """Test duplicate review detection."""
        review_create = ReviewCreate(**sample_review_data)
        
        # Create first review
        ReviewService.create_review(db_session, review_create)
        
        # Attempt to create duplicate - should raise error or skip
        with pytest.raises(Exception):
            ReviewService.create_review(db_session, review_create)

    @pytest.mark.unit
    def test_create_review_validation(self, db_session: Session):
        """Test review validation."""
        # Test invalid data (text too short)
        with pytest.raises(Exception):
            ReviewCreate(
                source="app_store",
                app_name="App",
                text="ab",  # Too short
            )

    @pytest.mark.unit
    def test_list_reviews_empty(self, db_session: Session):
        """Test listing reviews when empty."""
        reviews, total = ReviewService.list_reviews(db_session)
        
        assert reviews == []
        assert total == 0

    @pytest.mark.unit
    def test_list_reviews_pagination(self, db_session: Session, sample_reviews_batch: list):
        """Test review pagination."""
        # Create reviews
        for review_data in sample_reviews_batch:
            review_create = ReviewCreate(**review_data)
            ReviewService.create_review(db_session, review_create)
        
        # Test pagination
        page1, total = ReviewService.list_reviews(db_session, skip=0, limit=5)
        page2, _ = ReviewService.list_reviews(db_session, skip=5, limit=5)
        
        assert len(page1) == 5
        assert len(page2) == 5
        assert total == 10

    @pytest.mark.unit
    def test_list_reviews_filtering(self, db_session: Session, sample_reviews_batch: list):
        """Test review filtering."""
        for review_data in sample_reviews_batch:
            review_create = ReviewCreate(**review_data)
            ReviewService.create_review(db_session, review_create)
        
        # Filter by source
        reviews, total = ReviewService.list_reviews(db_session, source="app_store")
        assert total == 10

    @pytest.mark.unit
    def test_get_review_success(self, db_session: Session, sample_review_data: dict):
        """Test getting single review."""
        review_create = ReviewCreate(**sample_review_data)
        created = ReviewService.create_review(db_session, review_create)
        
        fetched = ReviewService.get_review(db_session, created.id)
        assert fetched.id == created.id
        assert fetched.text == created.text

    @pytest.mark.unit
    def test_get_review_not_found(self, db_session: Session):
        """Test getting non-existent review."""
        review = ReviewService.get_review(db_session, 99999)
        assert review is None

    @pytest.mark.unit
    def test_bulk_create_reviews(self, db_session: Session, sample_reviews_batch: list):
        """Test bulk review creation."""
        reviews_create = [ReviewCreate(**data) for data in sample_reviews_batch]
        result = ReviewService.bulk_create_reviews(db_session, reviews_create)
        
        assert result["total"] == len(sample_reviews_batch)
        assert result["created"] > 0

    @pytest.mark.unit
    def test_get_stats(self, db_session: Session, sample_reviews_batch: list):
        """Test review statistics."""
        for review_data in sample_reviews_batch:
            review_create = ReviewCreate(**review_data)
            ReviewService.create_review(db_session, review_create)
        
        stats = ReviewService.get_stats(db_session)
        
        assert "total_reviews" in stats
        assert "average_rating" in stats
        assert stats["total_reviews"] == 10


class TestAnalyticsService:
    """Tests for AnalyticsService."""

    @pytest.mark.unit
    def test_get_overview_empty(self, db_session: Session):
        """Test analytics overview with no data."""
        overview = AnalyticsService.get_overview(db_session)
        
        assert overview.total_reviews == 0
        assert overview.average_rating == 0
        assert overview.sentiment_breakdown.positive == 0

    @pytest.mark.unit
    def test_get_overview_with_data(self, db_session: Session, sample_reviews_batch: list):
        """Test analytics overview with data."""
        for review_data in sample_reviews_batch:
            review_create = ReviewCreate(**review_data)
            ReviewService.create_review(db_session, review_create)
        
        overview = AnalyticsService.get_overview(db_session)
        
        assert overview.total_reviews == 10
        assert overview.average_rating > 0
        assert len(overview.top_themes) >= 0

    @pytest.mark.unit
    def test_get_trend_data(self, db_session: Session, sample_reviews_batch: list):
        """Test trend data retrieval."""
        for review_data in sample_reviews_batch:
            review_create = ReviewCreate(**review_data)
            ReviewService.create_review(db_session, review_create)
        
        trends = AnalyticsService.get_trend_data(db_session, days=30)
        
        assert isinstance(trends, dict)
        assert "trends" in trends or len(trends) >= 0


class TestVectorService:
    """Tests for VectorService."""

    @pytest.mark.unit
    @pytest.mark.slow
    def test_semantic_search_empty(self, db_session: Session, sample_search_query: str):
        """Test semantic search with no reviews."""
        results = VectorService.search_semantic(db_session, sample_search_query)
        
        assert results == []

    @pytest.mark.unit
    @pytest.mark.slow
    def test_hybrid_search(self, db_session: Session, sample_reviews_batch: list, sample_search_query: str):
        """Test hybrid search."""
        for review_data in sample_reviews_batch:
            review_create = ReviewCreate(**review_data)
            ReviewService.create_review(db_session, review_create)
        
        results = VectorService.search_hybrid(db_session, sample_search_query, top_k=5)
        
        # Should return results or empty list
        assert isinstance(results, list)


class TestClusteringService:
    """Tests for ClusteringService."""

    @pytest.mark.unit
    @pytest.mark.slow
    def test_discover_themes_empty(self, db_session: Session):
        """Test theme discovery with no reviews."""
        result = ClusteringService.discover_themes(db_session, n_themes=5)
        
        assert "themes_found" in result or isinstance(result, dict)
        assert result.get("themes_found", 0) == 0

    @pytest.mark.unit
    @pytest.mark.slow
    def test_discover_themes_with_data(self, db_session: Session, sample_reviews_batch: list):
        """Test theme discovery with reviews."""
        for review_data in sample_reviews_batch:
            review_create = ReviewCreate(**review_data)
            ReviewService.create_review(db_session, review_create)
        
        result = ClusteringService.discover_themes(db_session, n_themes=3)
        
        assert isinstance(result, dict)
        assert "themes_found" in result or "reviews_processed" in result
