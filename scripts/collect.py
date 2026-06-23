"""Collect reviews from one source and persist them to the configured database."""
from __future__ import annotations

import argparse
import os
import sys

from database.connection import get_session, init_db
from database.repository import ReviewRepository

parser = argparse.ArgumentParser(
    description="Collect reviews from external sources (REQUIRES IMPLEMENTATION)",
    epilog="Note: Review collectors require additional dependencies. See README.md for setup.",
)
parser.add_argument("source", choices=["app-store", "play-store", "reddit"])
parser.add_argument("--app-name", required=True)
parser.add_argument("--app-id")
parser.add_argument("--package-name")
parser.add_argument("--subreddit")
parser.add_argument("--country", default="us")
parser.add_argument("--language", default="en")
parser.add_argument("--limit", type=int, default=100)
args = parser.parse_args()

# NOTE: Review collectors are commented out in requirements.txt due to version conflicts.
# To enable collection from external sources:
# 1. Uncomment the collector libraries in requirements.txt:
#    - app-store-scraper==0.3.5
#    - google-play-scraper==1.2.7
#    - praw==7.8.1
# 2. Create agents/collector.py with ReviewCollector class
# 3. Implement collection methods
#
# For now, this script accepts data via stdin or from pre-collected CSV files.

print("ERROR: Review collectors are not implemented in this release.", file=sys.stderr)
print(
    "To collect reviews, either:\n"
    "  A) Implement agents/collector.py with ReviewCollector class\n"
    "  B) Use the seed_demo.py script to load test data\n"
    "  C) Use the dashboard to upload review CSV files",
    file=sys.stderr
)
sys.exit(1)
