"""Persistence helpers shared by collectors and analysis jobs."""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from datetime import datetime

from sqlalchemy.orm import Session

from database.models import ReviewModel


def review_external_id(review: dict) -> str:
    supplied = review.get("external_id")
    if supplied:
        return str(supplied)
    raw = "|".join(str(review.get(k, "")) for k in ("source", "app_name", "reviewer", "date", "text"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def upsert_reviews(db: Session, reviews: Iterable[dict]) -> tuple[int, int]:
    inserted = skipped = 0
    for item in reviews:
        external_id = review_external_id(item)
        exists = db.query(ReviewModel.id).filter_by(source=item["source"], external_id=external_id).first()
        if exists:
            skipped += 1
            continue
        review_date = item["date"]
        if isinstance(review_date, str):
            review_date = datetime.fromisoformat(review_date.replace("Z", "+00:00")).replace(tzinfo=None)
        db.add(ReviewModel(
            external_id=external_id,
            source=item["source"],
            app_name=item["app_name"],
            reviewer=item.get("reviewer") or "Unknown",
            rating=item.get("rating"),
            title=item.get("title"),
            text=item["text"].strip(),
            date=review_date,
            url=item.get("url"),
            source_metadata=item.get("metadata"),
        ))
        inserted += 1
    db.commit()
    return inserted, skipped
