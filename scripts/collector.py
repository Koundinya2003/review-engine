"""
Review collection from multiple sources: App Store, Play Store, and Reddit.

This module provides functions to collect reviews from various sources and
return them in a format compatible with the review database schema.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)


# ============================================================================
# APP STORE COLLECTOR
# ============================================================================

def collect_app_store_reviews(
    app_id: str,
    app_name: str,
    limit: int = 100,
) -> list[dict]:
    """
    Collect reviews from Apple App Store.
    
    Args:
        app_id: App Store ID (numeric)
        app_name: Human-readable app name
        limit: Maximum reviews to collect (default 100)
    
    Returns:
        List of review dictionaries compatible with ReviewRepository.bulk_upsert()
    
    Example:
        >>> reviews = collect_app_store_reviews("id1232780281", "Notion")
        >>> len(reviews)
        50
    """
    try:
        from app_store_scraper import AppStore
    except ImportError:
        logger.error(
            "app-store-scraper not installed. "
            "Install with: pip install app-store-scraper"
        )
        return []
    
    try:
        logger.info(f"Collecting App Store reviews for {app_name} (ID: {app_id})...")
        app = AppStore(country="us", app_name=app_name, app_id=app_id)
        app.review(how_many=limit, sort_by="RECENT")
        
        reviews = []
        for review in app.reviews[:limit]:
            reviews.append({
                "external_id": review.get("id", f"appstore-{len(reviews)}"),
                "source": "app_store",
                "app_name": app_name,
                "reviewer": review.get("userName", "Anonymous"),
                "rating": float(review.get("rating", 3)),
                "title": review.get("title", ""),
                "text": review.get("review", ""),
                "date": datetime.fromisoformat(
                    review.get("date", datetime.now(timezone.utc).isoformat()).replace("Z", "+00:00")
                ),
                "url": f"https://apps.apple.com/app/id{app_id}",
                "metadata": {
                    "source_type": "app_store",
                    "version": review.get("version", "unknown"),
                },
            })
        
        logger.info(f"Collected {len(reviews)} App Store reviews")
        return reviews
    
    except Exception as e:
        logger.error(f"Failed to collect App Store reviews: {e}", exc_info=True)
        return []


# ============================================================================
# GOOGLE PLAY STORE COLLECTOR
# ============================================================================

def collect_play_store_reviews(
    package_name: str,
    app_name: str,
    limit: int = 100,
) -> list[dict]:
    """
    Collect reviews from Google Play Store.
    
    Args:
        package_name: Package name (e.g., "com.notion")
        app_name: Human-readable app name
        limit: Maximum reviews to collect (default 100)
    
    Returns:
        List of review dictionaries compatible with ReviewRepository.bulk_upsert()
    
    Example:
        >>> reviews = collect_play_store_reviews("com.notion", "Notion")
        >>> len(reviews)
        50
    """
    try:
        from google_play_scraper import app, reviews_all
    except ImportError:
        logger.error(
            "google-play-scraper not installed. "
            "Install with: pip install google-play-scraper"
        )
        return []
    
    try:
        logger.info(f"Collecting Play Store reviews for {app_name} ({package_name})...")
        
        review_list = reviews_all(
            package_name,
            sleep_milliseconds=100,
            lang="en",
            country="us",
            sort="NEWEST",
            count=limit,
        )
        
        reviews = []
        for review in review_list[:limit]:
            reviews.append({
                "external_id": review.get("reviewId", f"playstore-{len(reviews)}"),
                "source": "play_store",
                "app_name": app_name,
                "reviewer": review.get("userName", "Anonymous"),
                "rating": float(review.get("score", 3)),
                "title": review.get("reviewTitle", ""),
                "text": review.get("reviewText", ""),
                "date": datetime.fromtimestamp(
                    review.get("reviewCreatedVersion", 0) / 1000,
                    tz=timezone.utc
                ),
                "url": f"https://play.google.com/store/apps/details?id={package_name}",
                "metadata": {
                    "source_type": "play_store",
                    "version": review.get("appVersion", "unknown"),
                },
            })
        
        logger.info(f"Collected {len(reviews)} Play Store reviews")
        return reviews
    
    except Exception as e:
        logger.error(f"Failed to collect Play Store reviews: {e}", exc_info=True)
        return []


# ============================================================================
# REDDIT COLLECTOR
# ============================================================================

def collect_reddit_reviews(
    subreddit_name: str,
    app_name: str,
    limit: int = 100,
) -> list[dict]:
    """
    Collect reviews/mentions from Reddit subreddit.
    
    Requires Reddit API credentials in environment:
    - REDDIT_CLIENT_ID
    - REDDIT_CLIENT_SECRET
    - REDDIT_USER_AGENT
    
    Args:
        subreddit_name: Subreddit name (without /r/)
        app_name: Human-readable app name
        limit: Maximum posts to collect (default 100)
    
    Returns:
        List of review dictionaries compatible with ReviewRepository.bulk_upsert()
    
    Example:
        >>> reviews = collect_reddit_reviews("Notion", "Notion")
        >>> len(reviews)
        50
    """
    try:
        import praw
    except ImportError:
        logger.error(
            "praw not installed. "
            "Install with: pip install praw"
        )
        return []
    
    try:
        import os
        
        client_id = os.getenv("REDDIT_CLIENT_ID")
        client_secret = os.getenv("REDDIT_CLIENT_SECRET")
        user_agent = os.getenv("REDDIT_USER_AGENT")
        
        if not all([client_id, client_secret, user_agent]):
            logger.warning(
                "Reddit API credentials not found. "
                "Set REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT"
            )
            return []
        
        logger.info(f"Collecting Reddit discussions about {app_name} from r/{subreddit_name}...")
        
        reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent=user_agent,
        )
        
        subreddit = reddit.subreddit(subreddit_name)
        reviews = []
        
        for post in subreddit.new(limit=limit):
            if post.is_self:  # Text posts only
                reviews.append({
                    "external_id": post.id,
                    "source": "reddit",
                    "app_name": app_name,
                    "reviewer": post.author.name if post.author else "Anonymous",
                    "rating": None,  # Reddit posts don't have ratings
                    "title": post.title,
                    "text": post.selftext,
                    "date": datetime.fromtimestamp(post.created_utc, tz=timezone.utc),
                    "url": f"https://reddit.com{post.permalink}",
                    "metadata": {
                        "source_type": "reddit",
                        "subreddit": subreddit_name,
                        "score": post.score,
                        "comments": post.num_comments,
                    },
                })
        
        logger.info(f"Collected {len(reviews)} Reddit discussions")
        return reviews
    
    except Exception as e:
        logger.error(f"Failed to collect Reddit reviews: {e}", exc_info=True)
        return []


# ============================================================================
# UNIFIED COLLECTOR
# ============================================================================

def collect_all_sources(
    app_store_id: Optional[str] = None,
    play_store_package: Optional[str] = None,
    reddit_subreddit: Optional[str] = None,
    app_name: str = "App",
    limit_per_source: int = 50,
) -> list[dict]:
    """
    Collect reviews from all configured sources.
    
    Args:
        app_store_id: Apple App Store ID
        play_store_package: Google Play Store package name
        reddit_subreddit: Reddit subreddit name
        app_name: Human-readable app name
        limit_per_source: Reviews to collect from each source
    
    Returns:
        Combined list of reviews from all sources
    
    Example:
        >>> reviews = collect_all_sources(
        ...     app_store_id="id1232780281",
        ...     play_store_package="com.notion",
        ...     reddit_subreddit="Notion",
        ...     app_name="Notion",
        ...     limit_per_source=50,
        ... )
        >>> len(reviews)  # Up to 150 reviews total
        120
    """
    all_reviews = []
    
    if app_store_id:
        logger.info("Starting App Store collection...")
        app_reviews = collect_app_store_reviews(app_store_id, app_name, limit_per_source)
        all_reviews.extend(app_reviews)
    
    if play_store_package:
        logger.info("Starting Play Store collection...")
        play_reviews = collect_play_store_reviews(play_store_package, app_name, limit_per_source)
        all_reviews.extend(play_reviews)
    
    if reddit_subreddit:
        logger.info("Starting Reddit collection...")
        reddit_reviews = collect_reddit_reviews(reddit_subreddit, app_name, limit_per_source)
        all_reviews.extend(reddit_reviews)
    
    logger.info(f"Total reviews collected: {len(all_reviews)}")
    return all_reviews


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    import sys
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python scripts/collector.py app-store <app_id> <app_name> [limit]")
        print("  python scripts/collector.py play-store <package> <app_name> [limit]")
        print("  python scripts/collector.py reddit <subreddit> <app_name> [limit]")
        print("  python scripts/collector.py all <app_store_id> <package> <subreddit> <app_name> [limit]")
        print("\nExample:")
        print("  python scripts/collector.py app-store id1232780281 Notion 50")
        print("  python scripts/collector.py reddit Notion Notion 30")
        sys.exit(1)
    
    source = sys.argv[1]
    
    if source == "app-store":
        app_id = sys.argv[2] if len(sys.argv) > 2 else "id1232780281"
        app_name = sys.argv[3] if len(sys.argv) > 3 else "Notion"
        limit = int(sys.argv[4]) if len(sys.argv) > 4 else 50
        reviews = collect_app_store_reviews(app_id, app_name, limit)
    
    elif source == "play-store":
        package = sys.argv[2] if len(sys.argv) > 2 else "com.notion"
        app_name = sys.argv[3] if len(sys.argv) > 3 else "Notion"
        limit = int(sys.argv[4]) if len(sys.argv) > 4 else 50
        reviews = collect_play_store_reviews(package, app_name, limit)
    
    elif source == "reddit":
        subreddit = sys.argv[2] if len(sys.argv) > 2 else "Notion"
        app_name = sys.argv[3] if len(sys.argv) > 3 else "Notion"
        limit = int(sys.argv[4]) if len(sys.argv) > 4 else 50
        reviews = collect_reddit_reviews(subreddit, app_name, limit)
    
    elif source == "all":
        app_id = sys.argv[2] if len(sys.argv) > 2 else None
        package = sys.argv[3] if len(sys.argv) > 3 else None
        subreddit = sys.argv[4] if len(sys.argv) > 4 else None
        app_name = sys.argv[5] if len(sys.argv) > 5 else "App"
        limit = int(sys.argv[6]) if len(sys.argv) > 6 else 50
        reviews = collect_all_sources(app_id, package, subreddit, app_name, limit)
    
    print(f"\nCollected {len(reviews)} reviews")
    for review in reviews[:3]:
        print(f"  - [{review['source']}] {review['title'] or review['text'][:50]}")
