"""
Review management service.

Provides business logic for review operations with validation and enrichment.
"""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy.orm import Session

from core import get_logger, ValidationError
from database.models import ReviewModel
from database.repository import ReviewRepository
from database.schemas import ReviewCreate, ReviewResponse, ReviewUpdate

logger = get_logger(__name__)


class ReviewService:
    """Review business logic service."""
    
    @staticmethod
    def get_review(db: Session, review_id: int) -> ReviewResponse | None:
        """Get single review by ID."""
        review = ReviewRepository.get_by_id(db, review_id)
        if not review:
            logger.debug(f"Review {review_id} not found")
            return None
        return ReviewResponse.model_validate(review)
    
    @staticmethod
    def list_reviews(
        db: Session,
        skip: int = 0,
        limit: int = 50,
        **filters,
    ) -> tuple[list[ReviewResponse], int]:
        """List reviews with filters and pagination."""
        reviews, total = ReviewRepository.list_reviews(
            db, skip=skip, limit=limit, **filters
        )
        return (
            [ReviewResponse.model_validate(r) for r in reviews],
            total,
        )
    
    @staticmethod
    def create_review(db: Session, review_data: ReviewCreate) -> ReviewResponse:
        """Create new review with validation."""
        
        # Validate source
        if review_data.source not in {"app-store", "play-store", "reddit"}:
            raise ValidationError(
                f"Invalid source: {review_data.source}",
                details={"field": "source"}
            )
        
        # Validate text length
        if len(review_data.text) < 10:
            raise ValidationError(
                "Review text must be at least 10 characters",
                details={"field": "text"}
            )
        
        # Check for duplicates
        external_id = review_data.external_id or ReviewRepository._generate_external_id(
            review_data.model_dump()
        )
        existing = ReviewRepository.get_by_external_id(
            db, review_data.source, external_id
        )
        if existing:
            logger.info(f"Review already exists: {external_id}")
            return ReviewResponse.model_validate(existing)
        
        # Create review
        review = ReviewRepository.create(db, **review_data.model_dump())
        logger.info(f"Created review {review.id}")
        return ReviewResponse.model_validate(review)
    
    @staticmethod
    def update_review(
        db: Session,
        review_id: int,
        update_data: ReviewUpdate,
    ) -> ReviewResponse | None:
        """Update existing review."""
        
        review = ReviewRepository.update(
            db, review_id, **update_data.model_dump(exclude_unset=True)
        )
        if not review:
            logger.warning(f"Review {review_id} not found for update")
            return None
        
        logger.info(f"Updated review {review_id}")
        return ReviewResponse.model_validate(review)
    
    @staticmethod
    def delete_review(db: Session, review_id: int) -> bool:
        """Delete review."""
        success = ReviewRepository.delete(db, review_id)
        if success:
            logger.info(f"Deleted review {review_id}")
        else:
            logger.warning(f"Review {review_id} not found for deletion")
        return success
    
    @staticmethod
    def bulk_create_reviews(
        db: Session,
        reviews: list[ReviewCreate],
    ) -> dict[str, Any]:
        """Bulk create reviews."""
        review_dicts = [r.model_dump() for r in reviews]
        inserted, skipped = ReviewRepository.bulk_upsert(db, review_dicts)
        
        logger.info(f"Bulk created: {inserted} inserted, {skipped} skipped")
        return {
            "created": inserted,
            "skipped": skipped,
            "total": len(reviews),
        }
    
    @staticmethod
    def set_theme(
        db: Session,
        review_id: int,
        theme: str,
        confidence: float,
    ) -> ReviewResponse | None:
        """Set review theme."""
        
        if not 0 <= confidence <= 1:
            raise ValidationError(
                "Confidence must be between 0 and 1",
                details={"field": "confidence"}
            )
        
        ReviewRepository.update_theme(db, review_id, theme, confidence)
        return ReviewService.get_review(db, review_id)
    
    @staticmethod
    def set_embedding(
        db: Session,
        review_id: int,
        embedding: list[float],
    ) -> None:
        """Set review embedding."""
        ReviewRepository.update_embedding(db, review_id, embedding)
    
    @staticmethod
    def get_stats(db: Session) -> dict[str, Any]:
        """Get review statistics."""
        return ReviewRepository.get_stats(db)
    
    @staticmethod
    def search_by_text(
        db: Session,
        text: str,
        limit: int = 50,
    ) -> list[ReviewResponse]:
        """Full-text search reviews."""
        reviews, _ = ReviewRepository.list_reviews(
            db,
            limit=limit,
        )
        
        # Filter by text match
        text_lower = text.lower()
        matching = [
            r for r in reviews
            if text_lower in r.title.lower() or text_lower in r.text.lower()
        ]
        
        return [ReviewResponse.model_validate(r) for r in matching]
