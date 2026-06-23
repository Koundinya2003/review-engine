"""
Clustering and theme discovery service.

Provides theme detection and topic clustering using BERTopic.
"""

from __future__ import annotations

from typing import Any, Optional

import numpy as np
from sqlalchemy.orm import Session

from config import settings
from core import get_logger
from database.models import ReviewModel, ThemeModel
from database.repository import ReviewRepository, ThemeRepository

logger = get_logger(__name__)


class ClusteringService:
    """Theme clustering service using BERTopic."""
    
    @staticmethod
    def discover_themes(
        db: Session,
        n_themes: Optional[int] = None,
    ) -> dict[str, Any]:
        """
        Discover themes from reviews using BERTopic.
        
        Args:
            db: Database session
            n_themes: Target number of themes (default from config)
        
        Returns:
            Discovery results with theme information
        """
        try:
            from bertopic import BERTopic
            from umap import UMAP
            
            # Try HDBSCAN, fallback to KMeans if not available
            try:
                from hdbscan import HDBSCAN
                logger.debug("Using HDBSCAN for clustering")
                use_hdbscan = True
            except ImportError:
                logger.warning(
                    "HDBSCAN not available, using KMeans clustering. "
                    "Install hdbscan for better clustering: pip install hdbscan"
                )
                from sklearn.cluster import KMeans
                use_hdbscan = False
            
            n_themes = n_themes or settings.clustering.n_themes
            
            logger.info(f"Starting theme discovery with {n_themes} themes")
            
            # Get reviews with text
            reviews = db.query(ReviewModel).all()
            if not reviews:
                logger.warning("No reviews found for clustering")
                return {"themes_found": 0, "reviews_processed": 0}
            
            texts = [f"{r.title} {r.text}" for r in reviews]
            
            # Get embeddings
            from services.embedding_service import get_embedding_service
            embedding_service = get_embedding_service()
            embeddings = embedding_service.encode(texts)
            
            # Configure BERTopic
            umap_model = UMAP(
                n_neighbors=settings.clustering.umap_n_neighbors,
                n_components=settings.clustering.umap_n_components,
                metric="cosine",
            )
            
            # Configure clustering model (HDBSCAN or KMeans fallback)
            if use_hdbscan:
                from hdbscan import HDBSCAN
                hdbscan_model = HDBSCAN(
                    min_cluster_size=settings.clustering.hdbscan_min_cluster_size,
                    prediction_data=True,
                )
            else:
                from sklearn.cluster import KMeans
                hdbscan_model = KMeans(n_clusters=n_themes, random_state=42, n_init=10)
            
            # Run BERTopic
            topic_model = BERTopic(
                language=settings.clustering.language,
                nr_topics=n_themes,
                umap_model=umap_model,
                hdbscan_model=hdbscan_model,
                verbose=False,
            )
            
            topics, probabilities = topic_model.fit_transform(texts, embeddings)
            
            # Save themes to database
            themes_created = 0
            for topic_id in set(topics):
                if topic_id == -1:  # Outliers
                    continue
                
                # Get theme name and keywords
                freq_dict = topic_model.get_topic(topic_id)
                if not freq_dict:
                    continue
                
                keywords = [word for word, _ in freq_dict[:5]]
                theme_name = " + ".join(keywords[:3])
                
                # Check if theme exists
                existing = ThemeRepository.get_by_topic_id(db, topic_id)
                if existing:
                    ThemeRepository.update_count(db, existing.id, len([t for t in topics if t == topic_id]))
                else:
                    ThemeRepository.create(
                        db,
                        topic_id=topic_id,
                        theme_name=theme_name,
                        description="",
                        keywords=keywords,
                        count=len([t for t in topics if t == topic_id]),
                    )
                    themes_created += 1
                
                # Update review themes
                for review, assigned_topic in zip(reviews, topics):
                    if assigned_topic == topic_id:
                        confidence = float(probabilities[reviews.index(review)][topic_id])
                        ReviewRepository.update_theme(
                            db, review.id, theme_name, confidence
                        )
            
            logger.info(f"Theme discovery completed: {themes_created} themes created")
            return {
                "themes_found": len(set(topics)) - (1 if -1 in topics else 0),
                "reviews_processed": len(reviews),
                "themes_created": themes_created,
            }
        
        except ImportError as e:
            logger.error(f"BERTopic dependencies not available: {e}")
            return {"error": "BERTopic not available", "themes_found": 0}
        except Exception as e:
            logger.error(f"Theme discovery failed: {e}", exc_info=True)
            return {"error": str(e), "themes_found": 0}
    
    @staticmethod
    def get_theme_samples(
        db: Session,
        theme_id: int,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Get sample reviews for a theme."""
        theme = ThemeRepository.get_by_id(db, theme_id)
        if not theme:
            return []
        
        reviews, _ = ReviewRepository.list_reviews(
            db,
            theme=theme.theme_name,
            limit=limit,
        )
        
        return [
            {
                "id": r.id,
                "title": r.title,
                "text": r.text[:100],
                "rating": r.rating,
                "sentiment": r.sentiment,
            }
            for r in reviews
        ]


from typing import Optional
