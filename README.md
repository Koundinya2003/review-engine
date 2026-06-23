# 📱 Review Discovery Engine

## What Is This?

This system automatically analyzes reviews from apps and social media to find patterns and insights. It:
- **Collects** reviews from App Store, Google Play, and Reddit
- **Analyzes** them using AI to find common themes
- **Organizes** feedback by sentiment, rating, and topic
- **Visualizes** everything in a simple dashboard

No code knowledge needed — just point it at your app and get insights!

---

## 🚀 Quick Start (2 minutes)

### Option 1: Easy Start (Recommended)

**Using Docker** (requires Docker Desktop installed):

```bash
docker compose up --build -d
docker compose exec api python -m scripts.seed_demo
```

Then open:
- 📊 Dashboard: <http://localhost:8501>
- 🔌 API: <http://localhost:8000/docs>

Done! You'll see sample reviews already analyzed.

### Option 2: Without Docker

**On your computer** (requires Python 3.11+):

```bash
# Create isolated environment
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Install everything
pip install -r requirements.txt
cp .env.example .env

# Load sample data
python -m scripts.seed_demo

# Start the API (keep running)
uvicorn api.main:app --reload
```

**In a new terminal** (same folder, activate venv again):

```bash
source .venv/bin/activate
streamlit run dashboard/app.py
```

Open <http://localhost:8501> in your browser.

---

## 📊 How It Works (Simple Version)

```
┌─────────────────────────────────────────┐
│  Your App Reviews (App Store, etc)      │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  AI Reads All Reviews                   │
│  Finds common words and themes          │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  Groups Reviews Into Topics             │
│  "Battery Issues", "Crashes", etc       │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  Dashboard Shows Everything             │
│  Visual charts, trends, insights        │
└─────────────────────────────────────────┘
```

---

## 🎯 Step-by-Step Workflow

### Step 1: Load Review Data
You have 3 ways to get reviews:

**A) Use Sample Data** (instant, no setup)
```bash
python -m scripts.seed_demo
```
Loads demo reviews so you can see it working immediately.

**B) Add Your Own Reviews** 
Via the dashboard:
- Go to "Upload" section
- Paste or upload CSV with reviews
- System processes them automatically

**C) Collect Live Reviews** (requires API keys)
```bash
# App Store reviews for Notion
python -m scripts.collect app-store \
  --app-name "Notion" \
  --app-id 1232780281 \
  --limit 100

# Google Play reviews
python -m scripts.collect play-store \
  --app-name "Notion" \
  --package-name "notion.id" \
  --limit 100

# Reddit posts about your app
python -m scripts.collect reddit \
  --app-name "Notion" \
  --subreddit "Notion" \
  --limit 50
```

### Step 2: AI Analysis
The system automatically:
1. **Reads** every review (no humans needed)
2. **Understands** what it's saying (using AI)
3. **Groups** similar reviews together
4. **Rates** sentiment (positive/negative/neutral)
5. **Organizes** by theme (bugs, features, pricing, etc)

Takes 5-60 seconds depending on review count.

### Step 3: View Results in Dashboard
The dashboard shows:

📈 **Metrics**
- Total reviews processed
- Average rating
- Sentiment breakdown (happy/sad/neutral)

🏷️ **Themes**
- Common topics people mention
- How many reviews per theme
- Example quotes

📊 **Trends**
- Rating changes over time
- Sentiment patterns
- Most discussed topics

🔍 **Search**
- Find specific reviews
- Search by topic or keyword
- Similar review discovery

---

## 🎮 Using the Dashboard

### Main Features

**1. Home Screen**
- Overview of all reviews
- Key statistics
- Visual charts

**2. Reviews Section**
- Browse all reviews
- Filter by rating (5⭐ only? 1⭐ only?)
- Filter by sentiment (happy, sad, neutral)
- Search for specific words
- See themes automatically tagged

**3. Themes Section**
- See all discovered topics
- "Crashes" — 45 mentions
- "Slow performance" — 32 mentions
- "Love the UI" — 28 mentions
- Click to see examples

**4. Analytics**
- Trends over time
- Rating trends
- Sentiment trends
- Most important topics

**5. Upload Data**
- Add new reviews as CSV or text
- Bulk import from files

---

## 🔑 Keyboard Commands (Advanced Users)

Just in case you need to use the API directly:

| What You Want | How to Do It |
|---------------|------------|
| Add reviews | `POST /api/reviews` |
| See all reviews | `GET /api/reviews` |
| Search reviews | `GET /api/reviews/search?q=battery` |
| Run analysis | `POST /api/analysis/run` |
| Get themes | `GET /api/themes` |
| Get stats | `GET /api/metrics` |

Full API docs at: <http://localhost:8000/docs>

---

## 🛠️ What You Need

### To Run With Docker
- Docker Desktop installed
- 2 GB free disk space
- Internet connection (first run downloads AI models)

### To Run Without Docker
- Python 3.11 or newer
- macOS, Windows, or Linux
- 2 GB free disk space
- Internet connection

### To Collect Live Reviews
- For Reddit: Reddit developer account (free)
  - Get: Client ID, Client Secret, User Agent
  - Set in `.env` file

---

## ⚙️ Configuration

### Environment Variables (.env)

```env
# Leave blank for SQLite (local testing)
DATABASE_URL=

# For Reddit collection (optional)
REDDIT_CLIENT_ID=your_id_here
REDDIT_CLIENT_SECRET=your_secret_here
REDDIT_USER_AGENT=your_agent_here

# For advanced features (optional)
OPENAI_API_KEY=sk-...
```

Copy `.env.example` to `.env` and edit with your keys.

---

## 📁 What Gets Saved

- **Reviews Database** — stores all reviews with analysis
- **Models** — AI models for understanding text
- **Cache** — speeds up repeated searches
- **Logs** — for troubleshooting

Everything saved in the `outputs/` folder.

---

## 🆘 Troubleshooting

### "Connection refused" error
- Make sure Docker is running: `docker compose ps`
- Or make sure `uvicorn` is still running locally

### "Model download failed"
- Check internet connection
- Disk space available
- Try again (sometimes takes 5-10 minutes first time)

### "No reviews showing"
- Run: `docker compose exec api python -m scripts.seed_demo`
- Or upload reviews manually via dashboard

### "Analysis takes too long"
- Normal for first run (downloads AI model)
- Subsequent analyses much faster
- More reviews = longer analysis

---

## 🚀 What's Next?

Once you see it working:

1. **Upload your real reviews** - See actual patterns in your feedback
2. **Set up live collection** - Automatically pull reviews daily
3. **Share insights** - Export reports for your team
4. **Take action** - Use themes to prioritize fixes and features

---

## 📞 Need Help?

1. Check the **API docs**: <http://localhost:8000/docs>
2. Read **QUICKSTART.md** for more details
3. Review **logs** for error messages: `docker compose logs api`

---

## 📝 Example Workflow

**Day 1: Try it out**
```bash
docker compose up --build -d
docker compose exec api python -m scripts.seed_demo
# Open http://localhost:8501
# See sample analysis in dashboard
```

**Day 2: Use real data**
```bash
# Upload your reviews via dashboard
# OR collect from App Store/Reddit
# Run analysis
# Review themes in dashboard
```

**Day 3+: Get insights**
```bash
# Export reports
# Share findings with team
# Plan features based on themes
# Track sentiment over time
```

---

## 🎯 What You Get

✅ Analyze reviews without reading every one
✅ Find what customers really care about  
✅ Spot problems early
✅ Prioritize features customers want
✅ Track sentiment over time
✅ Export reports for your team

---

**Ready? Start with:** `docker compose up --build -d`
