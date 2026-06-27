# Quick Verification Guide

After code review and fixes, verify the project is production-ready with these steps:

## Step 1: Start Services (2 min)
```bash
cd /Users/adityakkoundinya/Documents/AI-Powered\ Review\ Discovery/review-engine
export AUTH_SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
docker-compose up -d
sleep 15
docker-compose ps
```

Expected: All services show "Up" or "healthy" status

## Step 2: Verify API Health (1 min)
```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "ok",
  "database": "ok",
  "services": {"embedding": "ok", "theme_discovery": "ok"}
}
```

## Step 3: Register & Login via Dashboard (2 min)
1. Open: http://localhost:8501
2. Click "Register" tab
3. Create account: testuser / test@example.com / TestPass123!
4. Should auto-login and show dashboard

## Step 4: Seed Demo Data (2 min)
```bash
docker exec review-engine-api-1 python scripts/seed_demo.py
```

Expected output:
```json
{"inserted": 12, "duplicates_skipped": 0, "reviews_processed": 12, "themes_discovered": 4}
```

## Step 5: Verify Dashboard Updates (1 min)
- Refresh dashboard at http://localhost:8501
- Should show:
  - ✓ Total Reviews: 12
  - ✓ Average Rating: 3.8
  - ✓ Themes: 4
  - ✓ Sentiment breakdown chart
  - ✓ Rating distribution chart

## Step 6: Test Search Functionality (1 min)
1. Go to "🔍 Search Reviews"
2. Enter query: "app"
3. Should return semantic search results

## Step 7: Test API Directly (1 min)
```bash
# Get token from login (store in $TOKEN)
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"TestPass123!"}' \
  | jq -r '.access_token')

# Test endpoint
curl -X GET http://localhost:8000/api/v1/analytics/overview \
  -H "Authorization: Bearer $TOKEN" | jq .
```

Expected: JSON response with analytics data

## Step 8: Test Data Persistence (1 min)
```bash
docker-compose down
docker-compose up -d
sleep 15

# Verify data still exists
docker exec review-engine-api-1 python -c \
  "from database.connection import get_session; \
   from database.models import ReviewModel; \
   db = get_session(); \
   print(f'Reviews: {db.query(ReviewModel).count()}')"
```

Expected: Reviews: 12 (persisted from before)

## Step 9: Cleanup
```bash
docker-compose down
```

---

## Total Time: ~12 minutes

**Sign-off:** If all steps pass, project is verified production-ready! ✅

For detailed testing scenarios, see: **END_TO_END_TESTING.md**
