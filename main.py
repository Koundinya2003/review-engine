"""
Command-line orchestrator for the review discovery pipeline.

Supports database initialization, review collection from multiple sources,
and AI-powered analysis.
"""
from __future__ import annotations

import argparse
import logging

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
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    """Main entry point for CLI commands."""
    parser = argparse.ArgumentParser(
        description="AI-powered review discovery and analysis"
    )
    
    parser.add_argument(
        "command",
        choices=[
            "init-db",
            "analyze",
            "collect-appstore",
            "collect-playstore",
            "collect-reddit",
            "collect-all",
        ],
        help="Command to execute",
    )
    
    parser.add_argument("--themes", type=int, default=8, help="Number of themes to discover")
    parser.add_argument("--limit", type=int, default=50, help="Reviews to collect per source")
    parser.add_argument("--app-name", default="App", help="Application name")
    parser.add_argument("--app-store-id", help="Apple App Store ID")
    parser.add_argument("--play-store-package", help="Google Play Store package")
    parser.add_argument("--reddit-subreddit", help="Reddit subreddit name")
    parser.add_argument("--no-analyze", action="store_true", help="Skip analysis after collection")
    
    args = parser.parse_args()
    
    # Initialize database for all commands
    init_db()
    
    if args.command == "init-db":
        logger.info("✓ Database initialized")
    
    elif args.command == "analyze":
        db = get_session()
        try:
            logger.info(f"Running analysis with {args.themes} themes...")
            result = analyze_reviews(db, n_themes=args.themes)
            logger.info(f"✓ Analysis complete: {result}")
        finally:
            db.close()
    
    elif args.command == "collect-appstore":
        if not args.app_store_id:
            logger.error("--app-store-id required")
            return
        
        logger.info(f"Collecting App Store reviews ({args.limit} max)...")
        reviews = collect_app_store_reviews(args.app_store_id, args.app_name, args.limit)
        
        if reviews:
            db = get_session()
            try:
                inserted, skipped = ReviewRepository.bulk_upsert(db, reviews)
                logger.info(f"✓ Stored {inserted} reviews ({skipped} duplicates skipped)")
                
                if not args.no_analyze:
                    logger.info(f"Running analysis with {args.themes} themes...")
                    result = analyze_reviews(db, n_themes=args.themes)
                    logger.info(f"✓ Analysis complete: {result}")
            finally:
                db.close()
        else:
            logger.warning("No reviews collected")
    
    elif args.command == "collect-playstore":
        if not args.play_store_package:
            logger.error("--play-store-package required")
            return
        
        logger.info(f"Collecting Play Store reviews ({args.limit} max)...")
        reviews = collect_play_store_reviews(args.play_store_package, args.app_name, args.limit)
        
        if reviews:
            db = get_session()
            try:
                inserted, skipped = ReviewRepository.bulk_upsert(db, reviews)
                logger.info(f"✓ Stored {inserted} reviews ({skipped} duplicates skipped)")
                
                if not args.no_analyze:
                    logger.info(f"Running analysis with {args.themes} themes...")
                    result = analyze_reviews(db, n_themes=args.themes)
                    logger.info(f"✓ Analysis complete: {result}")
            finally:
                db.close()
        else:
            logger.warning("No reviews collected")
    
    elif args.command == "collect-reddit":
        if not args.reddit_subreddit:
            logger.error("--reddit-subreddit required")
            return
        
        logger.info(f"Collecting Reddit discussions ({args.limit} max)...")
        reviews = collect_reddit_reviews(args.reddit_subreddit, args.app_name, args.limit)
        
        if reviews:
            db = get_session()
            try:
                inserted, skipped = ReviewRepository.bulk_upsert(db, reviews)
                logger.info(f"✓ Stored {inserted} reviews ({skipped} duplicates skipped)")
                
                if not args.no_analyze:
                    logger.info(f"Running analysis with {args.themes} themes...")
                    result = analyze_reviews(db, n_themes=args.themes)
                    logger.info(f"✓ Analysis complete: {result}")
            finally:
                db.close()
        else:
            logger.warning("No reviews collected")
    
    elif args.command == "collect-all":
        logger.info(f"Collecting from all sources ({args.limit} max per source)...")
        reviews = collect_all_sources(
            app_store_id=args.app_store_id,
            play_store_package=args.play_store_package,
            reddit_subreddit=args.reddit_subreddit,
            app_name=args.app_name,
            limit_per_source=args.limit,
        )
        
        if reviews:
            db = get_session()
            try:
                inserted, skipped = ReviewRepository.bulk_upsert(db, reviews)
                logger.info(f"✓ Stored {inserted} reviews ({skipped} duplicates skipped)")
                
                if not args.no_analyze:
                    logger.info(f"Running analysis with {args.themes} themes...")
                    result = analyze_reviews(db, n_themes=args.themes)
                    logger.info(f"✓ Analysis complete: {result}")
            finally:
                db.close()
        else:
            logger.warning("No reviews collected")


if __name__ == "__main__":
    main()
