# Review Discovery Engine - Test Credentials

## API Authentication Setup

### ✅ Authentication Status: ENABLED

The authentication system is now fully configured and ready for testing.

### 📝 Test User Credentials

**Username**: `demo`  
**Email**: `demo@review-engine.local`  
**Password**: `Demo12345`

### 🔗 API Endpoints

- **Register**: `POST http://localhost:8000/api/v1/auth/register`
- **Login**: `POST http://localhost:8000/api/v1/auth/login`
- **Dashboard**: `http://localhost:8501`

### 📋 Create User Request

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "demo",
    "email": "demo@review-engine    "email": "demo@review-engine    "email": "demo@review-engine    "email": "demo@reX     "email": "demo@review-engine    "emailin \    "email": "demo@review-engine    "email": "demo@review-engine    "email": "demo@review-eem    "email": "demo@review-engine    "email": "demo@reviess)
    "email": "demo@review-engine hb    "email": "demo@review-engine hb    "emaen_    "email": "demo@review-s_i    "email": "demo@review-engine hb ent     "email": "demo@review-engine hb    "email": "demo@review-engine hables    "email": "demo@review-eng                         #    "email": "demo@review-engine hb   up    "email": "demo@reviepro    "email": "demo@_TOKEN_EXPIRE_MINUTES=60
```

### 🚀 Docker Configuration

Update `docker-compose.yml` or create `docker-compose.auth.yml` with:

```yaml
api:
  environment:
    AUTH_ENABLED: "true"
    AUTH_SECRET_KEY: "super-secret-key-change-in-production"
```

### 📊 Dashboard Login

1. Open: `http://localhost:8501`
2. Select **Login** tab
3. Ente3. Ente3. Ente3. Ente3. Ente3. Ente3. Ente3. Ente3. Ente3. Ente3. Ente3. Ente3. Ente3. Ente3. Ente3. Ente3. Ente3. Ente3. Ente3. Ente3. Ente3. Ente3. Ente3. Ente3. Ente3. Ente3. Ente3. Ente3. Ente3. Ente3. Ente3. Ente3. Ente3. Ente3. Ente3. Ente3. Ente3. Ente3. Ente3. Ente3. Ente3. Ente3. Ente3. Ente3. Ente3. Ente3ev3. Ente3. Ente3. Ente3. Ente3. Ente3. Ente3. Ente3. Ente3. Ente3. Ente3. Ente3. Ente3. Ente3. Ente3. Ente3. Ente3. Ente3. Ente3. Ente3. Ente3. Ente3. Ente3. Ente3. Ente3. Ente3. Ente3. Ente3. Ente3. Ente3. Ente3. Ente3. Ente3. Ente3. Ente3. Ente3. Ente3. Ente3. Ente3. Ente3. Ente3. Ente3. Ente3. Ente3. Ente3. Ente3. Ente3ev3. Ente3. Ente3. Ente3. Ente3. Ente3. Ente3. Ente3. Ente3. Entean3.password match exactly

**Error: "**Error: "**Error: "**Error: "**Error: "**Error: "**Error: "**Erring and port 8000 i**Error: "*
- C- C- C- C- C- C- tings
- Verify `API_BASE_URL` in dashboard is correct

---

**Last Updated**: 2026-06-24
