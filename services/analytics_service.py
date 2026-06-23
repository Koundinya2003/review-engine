"""
Analytics and metrics service.

Provides aggregations, statistics, and trend analysis for reviews and themes.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from core import get_logger
from database.models import ReviewModel, ThemeModel
from database.repository import ReviewRepository, ThemeRepository
from database.schemas import (
    AnalyticsResponse,
    RatingBreakdown,
    SentimentBreakdown,
)

logger = get_logger(__name__)


class AnalyticsService:
    """Analytics and metrics service."""
    
    @staticmethod
    def get_overview(db: Session) -> AnalyticsResponse:
        """Get comprehensive analytics overview."""
        try:
            # Get stats
            stats = ReviewRepository.get_stats(db)
            
            # Get sentiment breakdown
            sentiment_query = db.query(
                ReviewModel.sentiment,
                func.count(ReviewModel.id),
            ).group_by(ReviewModel.sentiment).all()
            
            sentiment_dict = {s[0]: s[1] for s in sentiment_query if s[0]}
            sentiment_breakdown = SentimentBreakdown(
                positive=sentiment_dict.get("positive", 0),
                negative=sentiment_dict.get("negative", 0),
                neutral=sentiment_dict.get("neutral", 0),
                unknown=stats["total_reviews"] - sum(sentiment_dict.values()),
            )
            
            # Get rating breakdown
            rating_breakdown_data = db.query(
                ReviewModel.rating,
                func.count(ReviewModel.id),
            ).group_by(ReviewModel.rating).all()
            
            rating_dict = {r[0]: r[1] for r in rating_breakdown_data}
            rating_breakdown = RatingBreakdown(
                one_star=rating_dict.get(1, 0),
                two_star=rating_dict.get(2, 0),
                three_star=rating_dict.get(3, 0),
                four_star=rating_dict.get(4, 0),
                five_star=rating_dict.get(5, 0),
            )
            
            # Get top themes
            top_themes_objs = ThemeRepository.get_top_themes(db, limit=10)
            top_themes = [
                {
                    "id": t.id,
                    "name": t.theme_name,
                    "count": t.count,
                    "keywords": t.keywords,
                }
                for t in top_themes_objs
            ]
            
            # Get unique counts
            unique_themes = db.query(func.count(ThemeModel.id)).scalar() or 0
            unique_sources = db.query(func.count(func.distinct(ReviewModel.source))).scalar() or 0
            
            return AnalyticsResponse(
                total_reviews=stats["total_reviews"],
                average_rating=stats["average_rating"],
                sentiment_breakdown=sentiment_breakdown,
                rating_breakdown=rating_breakdown,
                unique_themes=unique_themes,
                unique_sources=unique_sources,
                reviews_by_source=stats["by_source"],
                top_themes=top_themes,
            )
        
        except Exception as e:
            logger.error(f"Analytics overview failed: {e}", exc_info=True)
            # Return empty analytics
            return AnalyticsResponse(
                total_reviews=0,
                average_rating=0,
                sentiment_breakdown=SentimentBreakdown(positive=0, negative=0, neutral=0, unknown=0),
                rating_breakdown=RatingBreakdown(one_star=0, two_star=0, three_star=0, four_star=0, five_star=0),
                unique_themes=0,
                unique_sources=0,
                reviews_by_source={},
                top_themes=[],
            )
    
    @staticmethod
    def get_theme_analytics(db: Session, theme_id: int) -> dict[str, Any]:
        """Get analytics for specific theme."""
        theme = ThemeRepository.get_by_id(db, theme_id)
        if not theme:
            return {}
        
        reviews, total = ReviewRepository.list_reviews(
            db,
            theme=theme.theme_name,
            limit=10000,  # Get all
        )
        
        if not reviews:
            return {
                "theme_id": theme_id,
                "theme_name": theme.theme_name,
                "total_reviews": 0,
            }
        
        # Calculate stats
        ratings = [r.rating for r in reviews if r.rating]
        avg_rating = sum(ratings) / len(ratings) if ratings else 0
        
        sentiments = {}
        for review in reviews:
            sentiment = review.sentiment or "unknown"
            sentiments[sentiment] = sentiments.get(sentiment, 0) + 1
        
        sources = {}
        for review in reviews:
            source = review.source
            sources[source] = sources.get(source, 0) + 1
        
        return {
            "theme_id": theme_id,
            "theme_name": theme.theme_name,
            "description": theme.description,
            "keywords": theme.keywords,
            "total_reviews": len(reviews),
            "average_rating": float(avg_rating),
            "sentiment_distribution": sentiments,
            "source_distribution": sources,
            "created_at": theme.created_at,
            "updated_at": theme.updated_at,
        }
    
    @staticmethod
    def get_source_analytics(db: Session, source: str) -> dict[str, Any]:
        """Get analytics for specific source."""
        reviews, total = ReviewRepository.list_reviews(
            db,
            source=source,
            limit=10000,
        )
        
        if not reviews:
            return {
                "source": source,
                "total_reviews": 0,
            }
        
        ratings = [r.rating for r in reviews if r.rating]
        avg_rating = sum(ratings) / len(ratings) if ratings else 0
        
        sentiments = {}
        for review in reviews:
            sentiment = review.sentiment or "unknown"
            sentiments[sentiment] = sentiments.get(sentiment, 0) + 1
        
        themes = {}
        for review in reviews:
            if review.theme:
                themes[review.theme] = themes.get(review.theme, 0) + 1
        
        return {
            "source": source,
            "total_reviews": len(reviews),
            "average_rating": float(avg_rating),
            "rating_distribution": {
                "1_star": len([r for r in reviews if r.rating == 1]),
                "2_star": len([r for r in reviews if r.rating == 2]),
                "3_star": len([r for r in reviews if r.rating == 3]),
                "4_star": len([r for r in reviews if r.rating == 4]),
                "5_star": len([r for r in reviews if r.rating == 5]),
            },
            "sentiment_distribution": sentiments,
            "top_themes": sorted(
                themes.items(),
                key=lambda x: x[1],
                reverse=True,
            )[:10],
        }
    
    @staticmethod
    def get_trend_data(db: Session, days: int = 30) -> dict[str, Any]:
        """Get trend data for the past N days."""
        from datetime import datetime, timedelta
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        recent_reviews = db.query(ReviewModel).filter(
            ReviewModel.created_at >= cutoff_date
        ).all()
        
        # Group by date
        daily_data = {}
        for review in recent_reviews:
            date_key = review.created_at.strftime("%Y-%m-%d")
            if date_key not in daily_data:
                daily_data[date_key] = {
                    "count": 0,
                    "avg_rating": 0,
                    "ratings": [],
                }
            daily_data[date_key]["count"] += 1
            if review.rating:
                daily_data[date_key]["ratings"].append(review.rating)
        
        # Calculate averages
        for date_key, data in daily_data.items():
            data["avg_rating"] = (
                sum(data["ratings"]) / len(data["ratings"])
                if data["ratings"]
                else 0
            )
            del data["ratings"]
        
        return {
            "period_days": days,
            "total_reviews": len(recent_reviews),
            "daily_data": daily_data,
        }
