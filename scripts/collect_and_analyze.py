"""
Collect reviews from multiple sources and store in database with analysis.

This is the main entry point for collecting reviews from App Store, Play Store,
and Reddit, storing them in the database, and running analysis.
"""

from __future__ import annotations

import argparse
import logging
from typing import Optional

from database.connection import get_session, init_db
from database.repository import ReviewRepository
from pipelines.analysis_service import analyze_reviews
from scripts.collector import (
    collect_all_sources,
    collect_app_store_reviews,
    collect_play_store_reviews,
    collect_reddit_reviews,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def collect_and_store(
    source: str,
    app_name: str,
    app_store_id: Optional[str] = None,
    play_store_package: Optional[str] = None,
    reddit_subreddit: Optional[str] = None,
    limit: int = 50,
    analyze: bool = True,
    n_themes: int = 8,
) -> dict:
    """
    Collect reviews from specified source and store in database.
    
    Args:
        source: Collection source ('app-store', 'play-store', 'reddit', or 'all')
        app_name: Human-readable app name
        app_store_id: App Store ID (if collecting from App Store)
        play_store_package: Play Store package (if collecting from Play Store)
        reddit_subreddit: Reddit subreddit (if collecting from Reddit)
        limit: Reviews per source
        analyze: Whether to run analysis after collection
        n_themes: Number of themes to discover
    
    Returns:
        Dictionary with collection and analysis results
    """
    logger.info(f"Starting collection from {source}...")
    
    # Collect reviews based on source
    if source == "app-store":
        if not app_store_id:
            raise ValueError("app_store_id required for app-store collection")
        reviews = collect_app_store_reviews(app_store_id, app_name, limit)
    
    elif source == "play-store":
        if not play_store_package:
            raise ValueError("play_store_package required for play-store collection")
        reviews = collect_play_store_reviews(play_store_package, app_name, limit)
    
    elif source == "reddit":
        if not reddit_subreddit:
            raise ValueError("reddit_subreddit required for reddit collection")
        reviews = collect_reddit_reviews(reddit_subreddit, app_name, limit)
    
    elif source == "all":
        reviews = collect_all_sources(
            app_store_id=app_store_id,
            play_store_package=play_store_package,
            reddit_subreddit=reddit_subreddit,
            app_name=app_name,
            limit_per_source=limit,
        )
    
    else:
        raise ValueError(f"Unknown source: {source}")
    
    if not reviews:
        logger.warning("No reviews collected")
        return {"collected": 0, "stored": 0, "skipped": 0}
    
    # Store in database
    logger.info(f"Storing {len(reviews)} reviews in database...")
    init_db()
    db = get_session()
    
    try:
        inserted, skipped = ReviewRepository.bulk_upsert(db, reviews)
        logger.info(f"Stored {inserted} new reviews ({skipped} duplicates skipped)")
        
        result = {"collected": len(reviews), "stored": inserted, "skipped": skipped}
        
        # Run analysis if requested
        if analyze:
            logger.info(f"Running analysis with n_themes={n_themes}...")
            analysis_result = analyze_reviews(db, n_themes=n_themes)
            result.update(analysis_result)
        
        return result
    
    finally:
        db.close()


def main():
    """Command-line interface for review collection and analysis."""
    parser = argparse.ArgumentParser(
        description="Collect reviews from App Store, Play Store, and Reddit"
    )
    
    parser.add_argument(
        "command",
        choices=["collect", "analyze", "init-db"],
        help="Command to execute",
    )
    
    parser.add_argument(
        "--source",
        choices=["app-store", "play-store", "reddit", "all"],
        default="all",
        help="Review source (default: all)",
    )
    
    parser.add_argument(
        "--app-name",
        default="App",
        help="Application name (default: App)",
    )
    
    parser.add_argument(
        "--app-store-id",
        help="Apple App Store ID (e.g., id1232780281)",
    )
    
    parser.add_argument(
        "--play-store-package",
        help="Google Play Store package (e.g., com.notion)",
    )
    
    parser.add_argument(
        "--reddit-subreddit",
        help="Reddit subreddit name (e.g., Notion)",
    )
    
    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Reviews per source (default: 50)",
    )
    
    parser.add_argument(
        "--themes",
        type=int,
        default=8,
        help="Number of themes to discover (default: 8)",
    )
    
    parser.add_argument(
        "--no-analyze",
        action="store_true",
        help="Skip analysis after collection",
    )
    
    args = parser.parse_args()
    
    if args.command == "init-db":
        logger.info("Initializing database...")
        init_db()
        logger.info("Database initialized ✓")
        return
    
    elif args.command == "analyze":
        logger.info("Running analysis on existing reviews...")
        init_db()
        db = get_session()
        try:
            result = analyze_reviews(db, n_themes=args.themes)
            logger.info(f"Analysis complete: {result}")
        finally:
            db.close()
        return
    
    elif args.command == "collect":
        result = collect_and_store(
            source=args.source,
            app_name=args.app_name,
            app_store_id=args.app_store_id,
            play_store_package=args.play_store_package,
            reddit_subreddit=args.reddit_subreddit,
            limit=args.limit,
            analyze=not args.no_analyze,
            n_themes=args.themes,
        )
        logger.info(f"Collection complete: {result}")


if __name__ == "__main__":
    main()
