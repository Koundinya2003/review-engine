# Authentication & Login Debugging Guide

## 🔴 Issue: "Cannot connect to API" Error

The login page shows:
- ⚠️ "Connection failed, retrying... (1/2)"
- ❌ "API Error: Cannot connect to API"  
- ❌ "Invalid credentials"

This guide explains why this happens and how to fix it.

---

## Root Causes & Solutions

### ❌ Problem 1: Authentication is Disabled

**Symptom**: API responds with `"detail": "Authentication not enabled"`

**Root Cause**: The `AUTH_ENABLED` environment variable is not set to `true`

**Solution**:
```bash
# Update docker-compose.yml
export AUTH_ENABLED=true

# Or set in docker-compose.yml:
environment:
  AUTH_ENABLED: "true"
```

### ❌ Problem 2: API Server Not Running

**Symptom**: Connection refused on port 8000

**Root Cause**: Docker containers are not started

**Solution**:
```bash
# Start all services
docker-compose up -d

# Verify API is running
docker-compose ps

# Check API logs
docker logs review_api

# Test connectivity
curl http://localhost:8000/health
```

### ❌ Problem 3: No Test Users Exist

**Symptom**: Login fails with "Invalid credentials" even with correct password

**Root Cause**: No user accounts in database

**Solution**: Create test user via API:
```bash
# Register new user
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "demo",
    "email": "demo@example.com",
    "password": "Demo12345"
  }'

# Response includes access_token
# {
#   "access_token": "eyJhbGc...",
#   "token_type": "bearer",
#   "expires_in": 3600
# }
```

### ❌ Problem 4: Incorrect API_BASE_URL in Dashboard

**Symptom**: Dashboard can't reach API even though API is running

**Root Cause**: `API_BASE_URL` environment variable is wrong

**Solution**:
```yaml
# In docker-compose.yml dashboard service:
environment:
  API_BASE_URL: http://api:8000  # For Docker container-to-container
  # Or: http://localhost:8000    # For local testing
```

### ❌ Problem 5: CORS Configuration Issue

**Symptom**: Browser console shows CORS error

**Root Cause**: API CORS settings don't include dashboard origin

**Solution**:
```yaml
# In docker-compose.yml api service:
environment:
  API_CORS_ORIGINS: '["http://localhost:8501","http://localhost:8000","http://dashboard:8501"]'
```

### ❌ Problem 6: Database Connection Failed

**Symptom**: API health check shows database in error state

**Root Cause**: PostgreSQL not running or credentials wrong

**Solution**:
```bash
# Verify PostgreSQL is running
docker-compose ps postgres

# Check database logs
docker logs review_db

# Test database connection
docker exec review_db psql -U reviews_user -d reviews_db -c "SELECT 1"

# Verify credentials in docker-compose.yml
# POSTGRES_USER: reviews_user
# POSTGRES_PASSWORD: reviews_password
# POSTGRES_DB: reviews_db
```

---

## 🟢 Step-by-Step Setup Guide

### 1️⃣ Start Services with Authentication Enabled

```bash
cd review-engine

# Ensure docker-compose.yml has AUTH_ENABLED set
# See: docker-compose.yml api service environment section

# Start services
docker-compose up -d

# Wait for services to be healthy (30-60 seconds)
docker-compose ps
```

### 2️⃣ Verify API is Running

```bash
# Should return healthy response
curl http://localhost:8000/health | jq .

# Expected response:
# {
#   "status": "healthy" or "degraded",
#   "database": "ok",
#   "services": { "embeddings": "ok", ... }
# }
```

### 3️⃣ Create Test User

```bash
# Register user
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "demo",
    "email": "demo@example.com",
    "password": "Demo12345"
  }'

# Should return:
# {
#   "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
#   "token_type": "bearer",
#   "expires_in": 3600
# }
```

### 4️⃣ Test Login

```bash
# Test login endpoint
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "demo",
    "password": "Demo12345"
  }'

# Should return same access_token response
```

### 5️⃣ Test Dashboard Login

1. Open browser: `http://localhost:8501`
2. Click **Login** tab
3. Enter:
   - Username: `demo`
   - Password: `Demo12345`
4. Click **🔓 Login**
5. Should redirect to dashboard

---

## 🔧 Troubleshooting Checklist

- [ ] Docker services running: `docker-compose ps` shows 3 healthy services
- [ ] Auth enabled: `docker exec review_api env | grep AUTH_ENABLED`
- [ ] API responds: `curl http://localhost:8000/health` returns 200
- [ ] Database ready: `docker logs review_db` shows "accepting connections"
- [ ] Test user exists: Run register request above
- [ ] Login works: Run login request above
- [ ] Dashboard accessible: `http://localhost:8501` loads
- [ ] No browser console errors (check F12 > Console)

---

## 📊 Current Configuration

### Docker Compose Environment Variables

```yaml
# API Service (docker-compose.yml)
api:
  environment:
    DATABASE_URL: postgresql://reviews_user:reviews_password@postgres:5432/reviews_db
    AUTH_ENABLED: "true"                    # ✅ Authentication enabled
    AUTH_SECRET_KEY: dev-secret-key-change-in-production
    AUTH_ACCESS_TOKEN_EXPIRE_MINUTES: 60

# Dashboard Service  
dashboard:
  environment:
    API_BASE_URL: http://api:8000           # ✅ Correct API URL for containers
```

### Test Credentials

| Field | Value |
|-------|-------|
| Username | `demo` |
| Email | `demo@example.com` |
| Password | `Demo12345` |
| API Endpoint | `http://localhost:8000` |
| Dashboard | `http://localhost:8501` |

---

## 🔐 Authentication Flow

```
1. User enters credentials on Dashboard
   ↓
2. Dashboard sends POST to /api/v1/auth/login
   ↓
3. API validates credentials against database
   ↓
4. API returns access_token (JWT)
   ↓
5. Dashboard stores token in session_state
   ↓
6. Subsequent requests include: Authorization: Bearer {token}
   ↓
7. API verifies token with get_current_user dependency
   ↓
8. User authorized, data returned
```

---

## 🛡️ Security Notes

⚠️ **For Production**:
- Change `AUTH_SECRET_KEY` to a strong, random value
- Use environment variables from secure secret manager
- Enable HTTPS/TLS
- Set `API_CORS_ORIGINS` to specific allowed domains only
- Implement rate limiting (already configured: 100 req/min)
- Store secrets in `.env` file (not in docker-compose.yml)
- Rotate JWT tokens regularly
- Monitor authentication logs for suspicious activity

---

## 📝 Common Solutions Quick Reference

| Error | Solution |
|-------|----------|
| "Authentication not enabled" | Set `AUTH_ENABLED=true` |
| "Cannot connect to API" | Start containers: `docker-compose up -d` |
| "Invalid credentials" | Register user first, verify username/password |
| "Token expired" | Login again to get new token |
| "CORS error in browser" | Check `API_CORS_ORIGINS` in docker-compose.yml |
| "Database connection failed" | Check PostgreSQL is healthy: `docker logs review_db` |
| "API Health shows degraded" | Normal - embedding model not downloaded offline |

---

## 🚀 Quick Start (One Command)

```bash
# Navigate to project
cd review-engine

# Start services with auth enabled
docker-compose up -d

# Wait 30 seconds for services to start
sleep 30

# Register test user
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"demo","email":"demo@example.com","password":"Demo12345"}'

# Open dashboard
open http://localhost:8501

# Login with demo / Demo12345
```

---

**Last Updated**: 2026-06-24  
**Status**: ✅ Authentication system ready for testing
