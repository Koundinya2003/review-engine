"""Collect reviews from one source and persist them to the configured database."""
from __future__ import annotations

import argparse
import os

from agents.collector import ReviewCollector
from database.models import SessionLocal, init_db
from database.repository import upsert_reviews

parser = argparse.ArgumentParser()
parser.add_argument("source", choices=["app-store", "play-store", "reddit"])
parser.add_argument("--app-name", required=True)
parser.add_argument("--app-id")
parser.add_argument("--package-name")
parser.add_argument("--subreddit")
parser.add_argument("--country", default="us")
parser.add_argument("--language", default="en")
parser.add_argument("--limit", type=int, default=100)
args = parser.parse_args()

collector = ReviewCollector()
if args.source == "app-store":
    if not args.app_id: parser.error("--app-id is required for app-store")
    rows = collector.collect_app_store_reviews(args.app_name, args.app_id, args.country, args.limit)
elif args.source == "play-store":
    if not args.package_name: parser.error("--package-name is required for play-store")
    rows = collector.collect_play_store_reviews(args.app_name, args.package_name, args.limit, args.language)
else:
    if not args.subreddit: parser.error("--subreddit is required for reddit")
    rows = collector.collect_reddit_reviews(
        args.app_name, args.subreddit, os.environ["REDDIT_CLIENT_ID"],
        os.environ["REDDIT_CLIENT_SECRET"], os.getenv("REDDIT_USER_AGENT", "review-discovery/1.0"), args.limit,
    )

init_db()
db = SessionLocal()
inserted, skipped = upsert_reviews(db, [row.to_dict() for row in rows if row.text.strip()])
db.close()
print({"collected": len(rows), "inserted": inserted, "duplicates_skipped": skipped})
