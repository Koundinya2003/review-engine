"""Minimal command-line orchestrator for the review discovery pipeline."""
from __future__ import annotations

import argparse

from database.connection import get_session, init_db
from pipelines.analysis_service import analyze_reviews

parser = argparse.ArgumentParser(description="AI-powered review discovery")
parser.add_argument("command", choices=["init-db", "analyze"])
parser.add_argument("--themes", type=int, default=8)
args = parser.parse_args()

init_db()
if args.command == "init-db":
    print("Database initialized")
else:
    db = get_session()
    try:
        print(analyze_reviews(db, n_themes=args.themes))
    finally:
        db.close()
