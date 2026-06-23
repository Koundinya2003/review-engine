"""Seed a small, representative corpus and optionally analyze it."""

from datetime import datetime, timedelta

from database.models import SessionLocal, init_db
from database.repository import upsert_reviews
from pipelines.analysis_service import analyze_reviews

SAMPLES = [
    ("app_store", 1, "The app crashes whenever I upload a photo. I lost my draft twice."),
    ("play_store", 2, "Very slow startup after the latest update and the screen freezes."),
    ("reddit", None, "Does anyone else have repeated login failures with two factor authentication?"),
    ("app_store", 5, "Love the clean design. Finding saved items is fast and easy."),
    ("play_store", 4, "Search is useful but I need better filters for dates and categories."),
    ("reddit", None, "The subscription price is confusing and cancellation is hard to find."),
    ("app_store", 2, "Notifications arrive hours late, so reminders are not useful."),
    ("play_store", 5, "Customer support replied quickly and fixed my billing issue."),
    ("reddit", None, "Please add offline mode. I travel often and lose access to everything."),
    ("app_store", 3, "Good features, but battery usage is much higher than other apps."),
    ("play_store", 1, "Payment failed three times and still charged my card."),
    ("reddit", None, "The new navigation is easier, although exporting data still takes forever."),
]


if __name__ == "__main__":
    init_db()
    db = SessionLocal()
    now = datetime.utcnow()
    payload = [{
        "external_id": f"demo-{i}", "source": source, "app_name": "Demo App",
        "reviewer": f"demo_user_{i}", "rating": rating, "title": None,
        "text": text, "date": now - timedelta(days=i), "metadata": {"demo": True},
    } for i, (source, rating, text) in enumerate(SAMPLES)]
    inserted, skipped = upsert_reviews(db, payload)
    result = analyze_reviews(db, n_themes=4)
    db.close()
    print({"inserted": inserted, "duplicates_skipped": skipped, **result})
