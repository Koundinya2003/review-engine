# ⚡ Quick Start Guide (5 Minutes)

## 1️⃣ Install Docker
- Download from [docker.com](https://docker.com)
- Install and open it

## 2️⃣ Get Project
```bash
git clone https://github.com/Koundinya2003/review-engine.git
cd review-engine
```

## 3️⃣ Start Application
```bash
docker-compose up -d
```

## 4️⃣ Open Dashboard
**Wait 30 seconds, then open in browser:**
```
http://localhost:8501
```

## 5️⃣ Register Account
- Click **Register** tab
- Create username, email, password
- Click **Register**

## 6️⃣ Upload Reviews
- Click **Upload Data**
- Upload CSV file with reviews
- Wait 1-2 minutes
- See charts on Dashboard! 📊

---

## That's It! 🎉

**For full guide:** See [USER_GUIDE.md](USER_GUIDE.md)

**Troubleshooting:**
- Not working? Run: `docker-compose ps`
- Should see 3 containers running
- If not, run: `docker-compose down` then `docker-compose up -d`
