"""
Data access patterns for database operations.

Provides repository pattern for all database entities with support for:
- CRUD operations
- Filtering and pagination
- Bulk operations
- Transaction management
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import and_, desc, func
from sqlalchemy.orm import Session

from database.models import ReviewModel, ThemeModel


# ============================================================================
# REVIEW REPOSITORY
# ============================================================================

class ReviewRepository:
    """Repository for Review model operations."""
    
    @staticmethod
    def get_by_id(db: Session, review_id: int) -> ReviewModel | None:
        """Get review by ID."""
        return db.query(ReviewModel).filter(ReviewModel.id == review_id).first()
    
    @staticmethod
    def get_by_external_id(db: Session, source: str, external_id: str) -> ReviewModel | None:
        """Get review by external ID."""
        return db.query(ReviewModel).filter(
            and_(
                ReviewModel.source == source,
                ReviewModel.external_id == external_id
            )
        ).first()
    
    @staticmethod
    def list_reviews(
        db: Session,
        skip: int = 0,
        limit: int = 50,
        source: Optional[str] = None,
        theme: Optional[str] = None,
        sentiment: Optional[str] = None,
        min_rating: Optional[int] = None,
        sort_by: str = "created_at",
        desc_order: bool = True,
    ) -> tuple[list[ReviewModel], int]:
        """List reviews with filtering and pagination."""
        
        query = db.query(ReviewModel)
        
        # Apply filters
        if source:
            query = query.filter(ReviewModel.source == source)
        if theme:
            query = query.filter(ReviewModel.theme == theme)
        if sentiment:
            query = query.filter(ReviewModel.sentiment == sentiment)
        if min_rating is not None:
            query = query.filter(ReviewModel.rating >= min_rating)
        
        # Count total before pagination
        total = query.count()
        
        # Apply sorting
        if hasattr(ReviewModel, sort_by):
            sort_col = getattr(ReviewModel, sort_by)
            if desc_order:
                query = query.order_by(desc(sort_col))
            else:
                query = query.order_by(sort_col)
        
        # Apply pagination
        items = query.offset(skip).limit(limit).all()
        
        return items, total
    
    @staticmethod
    def create(db: Session, **kwargs) -> ReviewModel:
        """Create new review."""
        if "date" not in kwargs:
            kwargs["date"] = datetime.utcnow()
        if "external_id" not in kwargs:
            kwargs["external_id"] = ReviewRepository._generate_external_id(kwargs)
        
        db_review = ReviewModel(**kwargs)
        db.add(db_review)
        db.commit()
        db.refresh(db_review)
        return db_review
    
    @staticmethod
    def update(db: Session, review_id: int, **kwargs) -> ReviewModel | None:
        """Update existing review."""
        db_review = ReviewRepository.get_by_id(db, review_id)
        if not db_review:
            return None
        
        kwargs["updated_at"] = datetime.utcnow()
        for key, value in kwargs.items():
            setattr(db_review, key, value)
        
        db.commit()
        db.refresh(db_review)
        return db_review
    
    @staticmethod
    def update_embedding(db: Session, review_id: int, embedding: list[float]) -> None:
        """Update review embedding."""
        db.query(ReviewModel).filter(ReviewModel.id == review_id).update(
            {ReviewModel.embedding: embedding, ReviewModel.updated_at: datetime.utcnow()}
        )
        db.commit()
    
    @staticmethod
    def update_theme(
        db: Session,
        review_id: int,
        theme: str,
        theme_confidence: float,
    ) -> None:
        """Update review theme."""
        db.query(ReviewModel).filter(ReviewModel.id == review_id).update(
            {
                ReviewModel.theme: theme,
                ReviewModel.theme_confidence: theme_confidence,
                ReviewModel.updated_at: datetime.utcnow(),
            }
        )
        db.commit()
    
    @staticmethod
    def delete(db: Session, review_id: int) -> bool:
        """Delete review."""
        review = ReviewRepository.get_by_id(db, review_id)
        if not review:
            return False
        db.delete(review)
        db.commit()
        return True
    
    @staticmethod
    def bulk_upsert(db: Session, reviews: list[dict]) -> tuple[int, int]:
        """Bulk insert/update reviews."""
        import hashlib
        
        inserted = 0
        skipped = 0
        
        for review_data in reviews:
            external_id = review_data.get("external_id")
            if not external_id:
                external_id = ReviewRepository._generate_external_id(review_data)
            
            existing = ReviewRepository.get_by_external_id(
                db, review_data["source"], external_id
            )
            
            if existing:
                skipped += 1
            else:
                review_data["external_id"] = external_id
                ReviewRepository.create(db, **review_data)
                inserted += 1
        
        return inserted, skipped
    
    @staticmethod
    def get_stats(db: Session) -> dict[str, Any]:
        """Get review statistics."""
        total = db.query(func.count(ReviewModel.id)).scalar() or 0
        avg_rating = db.query(func.avg(ReviewModel.rating)).scalar() or 0
        
        sentiment_stats = db.query(
            ReviewModel.sentiment,
            func.count(ReviewModel.id),
        ).group_by(ReviewModel.sentiment).all()
        
        source_stats = db.query(
            ReviewModel.source,
            func.count(ReviewModel.id),
        ).group_by(ReviewModel.source).all()
        
        return {
            "total_reviews": total,
            "average_rating": float(avg_rating),
            "by_sentiment": {s[0]: s[1] for s in sentiment_stats if s[0]},
            "by_source": {s[0]: s[1] for s in source_stats if s[0]},
        }
    
    @staticmethod
    def _generate_external_id(review_data: dict) -> str:
        """Generate deterministic external ID."""
        import hashlib
        
        combined = f"{review_data.get('source', '')}|{review_data.get('app_name', '')}|{review_data.get('reviewer', '')}|{review_data.get('title', '')}|{review_data.get('text', '')}"
        return hashlib.sha256(combined.encode()).hexdigest()[:16]


# ============================================================================
# THEME REPOSITORY
# ============================================================================

class ThemeRepository:
    """Repository for Theme model operations."""
    
    @staticmethod
    def get_by_id(db: Session, theme_id: int) -> ThemeModel | None:
        """Get theme by ID."""
        return db.query(ThemeModel).filter(ThemeModel.id == theme_id).first()
    
    @staticmethod
    def get_by_name(db: Session, theme_name: str) -> ThemeModel | None:
        """Get theme by name."""
        return db.query(ThemeModel).filter(ThemeModel.theme_name == theme_name).first()
    
    @staticmethod
    def get_by_topic_id(db: Session, topic_id: int) -> ThemeModel | None:
        """Get theme by topic ID."""
        return db.query(ThemeModel).filter(ThemeModel.topic_id == topic_id).first()
    
    @staticmethod
    def list_themes(
        db: Session,
        skip: int = 0,
        limit: int = 50,
        sort_by: str = "count",
        desc_order: bool = True,
    ) -> tuple[list[ThemeModel], int]:
        """List themes with pagination."""
        
        query = db.query(ThemeModel)
        total = query.count()
        
        # Apply sorting
        if hasattr(ThemeModel, sort_by):
            sort_col = getattr(ThemeModel, sort_by)
            if desc_order:
                query = query.order_by(desc(sort_col))
            else:
                query = query.order_by(sort_col)
        
        items = query.offset(skip).limit(limit).all()
        return items, total
    
    @staticmethod
    def create(db: Session, **kwargs) -> ThemeModel:
        """Create new theme."""
        db_theme = ThemeModel(**kwargs)
        db.add(db_theme)
        db.commit()
        db.refresh(db_theme)
        return db_theme
    
    @staticmethod
    def update_count(db: Session, theme_id: int, count: int) -> None:
        """Update theme count."""
        db.query(ThemeModel).filter(ThemeModel.id == theme_id).update(
            {ThemeModel.count: count, ThemeModel.updated_at: datetime.utcnow()}
        )
        db.commit()
    
    @staticmethod
    def delete(db: Session, theme_id: int) -> bool:
        """Delete theme."""
        theme = ThemeRepository.get_by_id(db, theme_id)
        if not theme:
            return False
        db.delete(theme)
        db.commit()
        return True
    
    @staticmethod
    def get_top_themes(db: Session, limit: int = 10) -> list[ThemeModel]:
        """Get top themes by count."""
        return (
            db.query(ThemeModel)
            .order_by(desc(ThemeModel.count))
            .limit(limit)
            .all()
        )


# ============================================================================
# BULK OPERATIONS
# ============================================================================

class BulkOperations:
    """Bulk database operations."""
    
    @staticmethod
    def delete_all_reviews(db: Session) -> int:
        """Delete all reviews."""
        count = db.query(ReviewModel).delete()
        db.commit()
        return count
    
    @staticmethod
    def delete_all_themes(db: Session) -> int:
        """Delete all themes."""
        count = db.query(ThemeModel).delete()
        db.commit()
        return count
    
    @staticmethod
    def reset_database(db: Session) -> dict[str, int]:
        """Reset entire database."""
        reviews_deleted = BulkOperations.delete_all_reviews(db)
        themes_deleted = BulkOperations.delete_all_themes(db)
        return {
            "reviews_deleted": reviews_deleted,
            "themes_deleted": themes_deleted,
        }
