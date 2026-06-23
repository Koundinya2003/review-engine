"""
Vector search service for semantic similarity operations.

Provides semantic search capabilities using embeddings and pgvector (when available).
Supports hybrid search combining keyword and semantic matching.
"""

from __future__ import annotations

from typing import Optional

import numpy as np
from sqlalchemy.orm import Session

from core import get_logger
from database.models import ReviewModel
from database.repository import ReviewRepository
from services.embedding_service import get_embedding_service

logger = get_logger(__name__)


class VectorService:
    """Semantic vector search service."""
    
    @staticmethod
    def search_semantic(
        db: Session,
        query: str,
        top_k: int = 20,
        threshold: float = 0.3,
    ) -> list[tuple[ReviewModel, float]]:
        """
        Search reviews by semantic similarity.
        
        Args:
            db: Database session
            query: Search query
            top_k: Number of results to return
            threshold: Minimum similarity score (0-1)
        
        Returns:
            List of (review, similarity_score) tuples
        """
        try:
            # Get embedding service
            embedding_service = get_embedding_service()
            
            # Encode query
            query_embedding = embedding_service.encode_single(query)
            
            # Get all reviews with embeddings
            reviews_with_embeddings = db.query(ReviewModel).filter(
                ReviewModel.embedding.isnot(None)
            ).all()
            
            if not reviews_with_embeddings:
                logger.warning("No reviews with embeddings found")
                return []
            
            # Convert embeddings to numpy array
            embeddings = np.array([
                review.embedding for review in reviews_with_embeddings
            ])
            
            # Calculate similarity
            similarities = embedding_service.similarity(
                np.array([query_embedding]),
                embeddings
            )[0]
            
            # Filter by threshold and get top k
            results = [
                (review, float(score))
                for review, score in zip(reviews_with_embeddings, similarities)
                if score >= threshold
            ]
            
            results.sort(key=lambda x: x[1], reverse=True)
            return results[:top_k]
        
        except Exception as e:
            logger.error(f"Semantic search failed: {e}", exc_info=True)
            return []
    
    @staticmethod
    def search_hybrid(
        db: Session,
        query: str,
        top_k: int = 20,
        keyword_weight: float = 0.3,
        semantic_weight: float = 0.7,
    ) -> list[tuple[ReviewModel, float]]:
        """
        Hybrid search combining keyword and semantic matching.
        
        Args:
            db: Database session
            query: Search query
            top_k: Number of results to return
            keyword_weight: Weight for keyword matching (0-1)
            semantic_weight: Weight for semantic matching (0-1)
        
        Returns:
            List of (review, combined_score) tuples
        """
        try:
            # Keyword search (full-text search in SQLite/PostgreSQL)
            query_lower = query.lower()
            keyword_reviews = db.query(ReviewModel).filter(
                ReviewModel.text.ilike(f"%{query_lower}%")
            ).all()
            
            # Semantic search
            semantic_results = VectorService.search_semantic(
                db, query, top_k=top_k * 2
            )
            
            # Combine results
            combined_scores: dict[int, float] = {}
            
            # Add keyword scores
            for review in keyword_reviews:
                combined_scores[review.id] = keyword_weight
            
            # Add semantic scores
            for review, sem_score in semantic_results:
                current_score = combined_scores.get(review.id, 0)
                combined_scores[review.id] = current_score + (sem_score * semantic_weight)
            
            # Get review objects and sort
            results = []
            for review_id, score in combined_scores.items():
                review = ReviewRepository.get_by_id(db, review_id)
                if review:
                    results.append((review, score))
            
            results.sort(key=lambda x: x[1], reverse=True)
            return results[:top_k]
        
        except Exception as e:
            logger.error(f"Hybrid search failed: {e}", exc_info=True)
            return []
    
    @staticmethod
    def index_embeddings(db: Session) -> int:
        """
        Generate and index embeddings for all reviews.
        
        Returns:
            Number of reviews indexed
        """
        try:
            embedding_service = get_embedding_service()
            
            # Get reviews without embeddings
            reviews = db.query(ReviewModel).filter(
                ReviewModel.embedding.is_(None)
            ).all()
            
            if not reviews:
                logger.info("No reviews to index")
                return 0
            
            # Get texts
            texts = [f"{r.title} {r.text}" for r in reviews]
            
            # Encode in batches
            embeddings = embedding_service.encode(texts)
            
            # Update database
            for review, embedding in zip(reviews, embeddings):
                ReviewRepository.update_embedding(
                    db, review.id, embedding.tolist()
                )
            
            logger.info(f"Indexed {len(reviews)} reviews")
            return len(reviews)
        
        except Exception as e:
            logger.error(f"Embedding indexing failed: {e}", exc_info=True)
            return 0
    
    @staticmethod
    def find_similar(
        db: Session,
        review_id: int,
        top_k: int = 10,
    ) -> list[tuple[ReviewModel, float]]:
        """Find similar reviews to a given review."""
        review = ReviewRepository.get_by_id(db, review_id)
        if not review or not review.embedding:
            return []
        
        query_text = f"{review.title} {review.text}"
        return VectorService.search_semantic(db, query_text, top_k)
