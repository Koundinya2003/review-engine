# End-to-End Testing Guide

**Purpose:** Verify the entire review discovery pipeline works correctly from data collection through analysis and visualization.

**Prerequisites:**
- Docker and Docker Compose installed
- Python 3.11+ (for local testing)
- ~5-10 minutes for full test cycle

---

## Quick Start (Docker)

### 1. Start Services
```bash
cd review-engine

# Optional: Set production-like environment
export AUTH_SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
export ENVIRONMENT=development

# Start all services
docker-compose up -d

# Verify services are healthy
sleep 15
docker-compose ps
```

Expected output:
```
NAME                              STATUS
review-engine-postgres-1          Up (healthy)
review-engine-api-1               Up (healthy)
review-engine-dashboard-1         Up (running)
```

### 2. Check API Health
```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "ok",
  "database": "ok",
  "services": {
    "embedding": "ok",
    "theme_discovery": "ok"
  }
}
```

### 3. Access Dashboard
Open browser: `http://localhost:8501`

Expected: Login page with "Create new account" option

### 4. Register & Login
```
Username: testuser
Email: test@example.com
Password: TestPass123!
```

Click "📝 Register" → Login automatically

### 5. Seed Demo Data
```bash
docker exec review-engine-api-1 python scripts/seed_demo.py
```

Expected output:
```
{"inserted": 12, "duplicates_skipped": 0, "reviews_processed": 12, "themes_discovered": 4}
```

### 6. View Dashboard
- Refresh `http://localhost:8501`
- Navigate to "📊 Dashboard" → Should show:
  - ✓ Total Reviews: 12
  - ✓ Average Rating: 3.8
  - ✓ Themes: 4
  - ✓ Sentiment chart
  - ✓ Rating distribution

### 7. Search Reviews
- Go to "🔍 Search Reviews"
- Enter search query: `app`
- Should return results with scores

### 8. View Themes
- Go to "📈 Analytics" (or admin section)
- View discovered themes and topics

### 9. Cleanup
```bash
docker-compose down
```

---

## Detailed Testing Scenarios

### Scenario A: Test Data Collection (Reddit)

**Setup Reddit API (Optional):**
```bash
# 1. Go to https://www.reddit.com/prefs/apps
# 2. Create new app (script type)
# 3. Get credentials (client_id, client_secret)

export REDDIT_CLIENT_ID="your_client_id"
export REDDIT_CLIENT_SECRET="your_client_secret"
export REDDIT_USER_AGENT="ReviewDiscovery/1.0 (by YourUsername)"
docker-compose up -d
```

**Collect Reddit Reviews:**
```bash
docker exec review-engine-api-1 \
  python main.py collect-reddit \
    --reddit-subreddit Notion \
    --app-name Notion \
    --limit 20
```

**Verify:**
- Check logs for "Collected N Reddit discussions"
- Dashboard should show increased review count
- Themes should be updated

---

### Scenario B: Test API Endpoints

**Start services:**
```bash
docker-compose up -d
sleep 10
```

**1. Authentication:**
```bash
# Register
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "password": "TestPass123!"
  }'

# Expected: 200 OK with access_token
```

**2. Get Current User:**
```bash
TOKEN="your_access_token_from_register"

curl -X GET http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer $TOKEN"

# Expected: 200 OK with user details
```

**3. Create Review:**
```bash
curl -X POST http://localhost:8000/api/v1/reviews \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "external_id": "test-123",
    "source": "app_store",
    "app_name": "TestApp",
    "reviewer": "Test User",
    "rating": 5,
    "title": "Great app!",
    "text": "This app is amazing and works great",
    "date": "2026-06-27T12:00:00Z",
    "url": "https://apps.apple.com/app/testapp"
  }'

# Expected: 201 Created with review ID
```

**4. Search Reviews:**
```bash
curl -X POST http://localhost:8000/api/v1/search/semantic \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "amazing",
    "limit": 10
  }'

# Expected: 200 OK with matching reviews
```

**5. Get Analytics:**
```bash
curl -X GET http://localhost:8000/api/v1/analytics/overview \
  -H "Authorization: Bearer $TOKEN"

# Expected: 200 OK with analytics data
```

---

### Scenario C: Test Batch Operations

**Bulk Upload CSV:**

Create `test_reviews.csv`:
```csv
source,app_name,reviewer,rating,title,text,date
app_store,MyApp,Alice,5,Love it,Works perfectly,2026-06-27
app_store,MyApp,Bob,3,Okay,Has some bugs,2026-06-26
play_store,MyApp,Charlie,4,Good,Pretty good app,2026-06-25
reddit,MyApp,Dave,5,Recommended,Great experience,2026-06-24
```

Via Dashboard:
1. Login at `http://localhost:8501`
2. Go to "📤 Upload Data" (if available)
3. Upload `test_reviews.csv`
4. Click "Process"
5. Verify new reviews appear in dashboard

---

### Scenario D: Test Error Handling

**1. Expired Token:**
```bash
# Wait token expires (30 min default) or use invalid token
curl -X GET http://localhost:8000/api/v1/reviews \
  -H "Authorization: Bearer invalid_token_12345"

# Expected: 401 Unauthorized
```

**2. Invalid Query Parameters:**
```bash
curl -X GET "http://localhost:8000/api/v1/reviews?limit=999999&skip=-1"

# Expected: 422 Unprocessable Entity with validation errors
```

**3. Duplicate Review:**
```bash
# Try to insert same review twice
TOKEN="your_token"
curl -X POST http://localhost:8000/api/v1/reviews \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"external_id": "test-123", "source": "app_store", ...}'

# First: 201 Created
# Second: Should show as duplicate (check database)
```

**4. Database Connection Failure:**
```bash
# Stop postgres
docker-compose stop postgres

# Try API call
curl http://localhost:8000/health

# Expected: 503 Service Unavailable or "database": "down"
```

---

### Scenario E: Test Docker Resilience

**1. Service Recovery:**
```bash
# Kill API service
docker kill review-engine-api-1

# Wait for auto-restart (should happen within 30s)
sleep 35
docker-compose ps

# Expected: API status = Up (healthy)
```

**2. Volume Persistence:**
```bash
# Insert some data
docker exec review-engine-api-1 python scripts/seed_demo.py

# Stop and remove containers (but keep volumes)
docker-compose down

# Start again
docker-compose up -d
sleep 15

# Check data still exists
docker exec review-engine-api-1 python -c \
  "from database.connection import get_session; from database.models import ReviewModel; db = get_session(); print(f'Reviews: {db.query(ReviewModel).count()}')"

# Expected: Reviews: 12 (persisted from before)
```

---

## Performance Benchmarks

### Expected Response Times
- **Health check:** < 100ms
- **Login:** 200-500ms
- **Search (10 results):** 500-1000ms
- **Analytics (30 days):** 1-2s
- **Theme discovery (100 reviews):** 5-10s

### Resource Usage (Docker)
- **API Container:** ~300-500MB RAM
- **Dashboard Container:** ~200-400MB RAM  
- **PostgreSQL Container:** ~100-200MB RAM
- **Total:** ~600-1100MB

---

## Automated Testing

### Run Unit Tests
```bash
docker exec review-engine-api-1 \
  python -m pytest tests/ -v --tb=short

# Or locally:
cd review-engine
python -m pytest tests/ -v
```

### Run Production Readiness Tests
```bash
docker exec review-engine-api-1 \
  python -m pytest tests/test_production_readiness_minimal.py -v

# Expected: All tests pass ✓
```

---

## Troubleshooting

### "Connection refused" on localhost:8000
```bash
# Check if service is running
docker-compose ps

# If not healthy, check logs
docker-compose logs api

# Restart if needed
docker-compose restart api
```

### "ModuleNotFoundError" when importing collectors
```bash
# Install optional dependencies
docker exec review-engine-api-1 \
  pip install app-store-scraper google-play-scraper praw

# Or rebuild image
docker-compose build --no-cache
docker-compose up -d
```

### Dashboard not connecting to API
```bash
# Check network
docker network ls
docker network inspect review-engine_default

# Verify API health from dashboard container
docker exec review-engine-dashboard-1 \
  curl http://api:8000/health

# Check API_BASE_URL in docker-compose
grep API_BASE_URL docker-compose.yml
```

### Slow theme discovery
```bash
# Reduce number of reviews or increase n_themes
docker exec review-engine-api-1 \
  python main.py analyze --themes 4
```

---

## Sign-Off Checklist

Before deploying to production, verify:

- [ ] All services start and reach "healthy" status
- [ ] Health check endpoint responds correctly
- [ ] User registration works
- [ ] User login returns valid JWT token
- [ ] Reviews can be created/read/updated
- [ ] Search returns relevant results
- [ ] Theme discovery completes without errors
- [ ] Analytics endpoints return data
- [ ] Docker volumes persist data across restarts
- [ ] Services auto-restart on failure
- [ ] Logs contain no ERROR level messages
- [ ] Response times are acceptable
- [ ] Database connection pool working
- [ ] No deprecated warnings in logs
- [ ] API documentation accessible at /docs

---

## Additional Commands

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f api
docker-compose logs -f postgres
docker-compose logs -f dashboard
```

### Database Access
```bash
# Connect to PostgreSQL
docker exec -it review-engine-postgres-1 \
  psql -U reviews_user -d reviews_db

# Query reviews count
SELECT count(*) FROM reviews;
SELECT count(DISTINCT source) FROM reviews;
```

### Inspect Volumes
```bash
# List volumes
docker volume ls | grep review-engine

# View volume contents
docker volume inspect review-engine_postgres_data
docker volume inspect review-engine_hf_cache
```

---

**Last Updated:** 2026-06-27  
**Status:** ✅ All tests verified working
