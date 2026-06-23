"""End-to-end embedding and theme-discovery job."""

from __future__ import annotations

import logging
from collections import Counter

import numpy as np
from sqlalchemy.orm import Session

from database.models import ReviewModel, ThemeModel
from pipelines.embedding_pipeline import get_embedding_pipeline
from pipelines.theme_discovery import ThemeDiscoveryPipeline

logger = logging.getLogger(__name__)


def _sentiment(rating: float | None, text: str) -> str:
    if rating is not None:
        return "positive" if rating >= 4 else "negative" if rating <= 2 else "neutral"
    words = text.lower()
    positive = sum(w in words for w in ("love", "great", "fast", "easy", "helpful"))
    negative = sum(w in words for w in ("crash", "slow", "bug", "hate", "broken", "fail"))
    return "positive" if positive > negative else "negative" if negative > positive else "neutral"


def analyze_reviews(db: Session, n_themes: int = 8) -> dict:
    try:
        logger.info(f"Starting analysis with n_themes={n_themes}")
        reviews = db.query(ReviewModel).filter(ReviewModel.text != "").order_by(ReviewModel.id).all()
        logger.info(f"Loaded {len(reviews)} reviews for analysis")
        
        if not reviews:
            logger.warning("No reviews found for analysis")
            return {"reviews_processed": 0, "themes_discovered": 0}

        texts = [r.text for r in reviews]
        logger.debug("Generating embeddings...")
        embedder = get_embedding_pipeline()
        embeddings = embedder.encode(texts)
        logger.debug(f"Generated {len(embeddings)} embeddings")

        logger.debug(f"Discovering themes (n_themes={min(n_themes, max(1, len(texts)))})")
        discovery = ThemeDiscoveryPipeline(n_themes=min(n_themes, max(1, len(texts))))
        topics, probabilities = discovery.fit_transform(texts, embeddings)
        themes = discovery.get_themes()
        logger.info(f"Discovered {len(themes)} themes")

        logger.debug("Updating database with themes and sentiment analysis")
        db.query(ThemeModel).delete()
        names: dict[int, str] = {}
        counts = Counter(topics)
        for topic_id, info in themes.items():
            name = info["name"]
            names[topic_id] = name
            indexes = [i for i, topic in enumerate(topics) if topic == topic_id]
            db.add(ThemeModel(
                topic_id=topic_id,
                theme_name=name,
                description=f"Reviews about {', '.join(info['keywords'][:5])}",
                count=counts[topic_id],
                keywords=info["keywords"],
                top_reviews=[reviews[i].id for i in indexes[:5]],
            ))

        for i, review in enumerate(reviews):
            review.embedding = np.asarray(embeddings[i], dtype=float).tolist()
            review.theme = names.get(topics[i], "Other")
            review.theme_confidence = float(probabilities[i])
            review.sentiment = _sentiment(review.rating, review.text)
        
        db.commit()
        logger.info(f"Analysis complete: {len(reviews)} reviews processed, {len(themes)} themes discovered")
        return {"reviews_processed": len(reviews), "themes_discovered": len(themes)}
    except Exception as exc:
        logger.error(f"Analysis failed: {exc}", exc_info=True)
        db.rollback()
        raise


def semantic_search(db: Session, query: str, limit: int = 20) -> list[tuple[ReviewModel, float]]:
    try:
        logger.debug(f"Semantic search: query='{query}', limit={limit}")
        rows = db.query(ReviewModel).filter(ReviewModel.embedding.isnot(None)).all()
        
        if not rows:
            logger.debug("No embeddings found in database")
            return []
        
        logger.debug(f"Searching {len(rows)} embedded reviews")
        query_vector = get_embedding_pipeline().encode_single(query)
        matrix = np.asarray([row.embedding for row in rows])
        scores = get_embedding_pipeline().similarity(query_vector.reshape(1, -1), matrix)[0]
        ranked = np.argsort(scores)[::-1][:limit]
        results = [(rows[i], float(scores[i])) for i in ranked]
        logger.debug(f"Found {len(results)} matching reviews")
        return results
    except Exception as exc:
        logger.error(f"Semantic search error: {exc}", exc_info=True)
        raise
