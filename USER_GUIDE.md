# 📊 Review Discovery Engine - Complete User Guide
## Everything You Need to Know (From A-Z)

---

## 🎯 What Is This Project?

The **Review Discovery Engine** is an AI-powered tool that analyzes customer reviews and turns them into useful insights. Think of it as a smart assistant that:

- 📖 Reads all your customer reviews
- 🔍 Finds common themes and patterns
- ⭐ Groups reviews by sentiment (positive/negative/neutral)
- 📊 Creates charts and graphs to show what customers care about
- 💡 Helps you understand what to improve

---

## 🖥️ What You Need

### Minimum Requirements
- **Computer**: Mac, Windows, or Linux
- **Storage**: 5GB free space
- **Memory**: 4GB RAM (8GB recommended)
- **Internet**: Connection needed for first-time setup

### Software You Need to Install
1. **Docker** (the container system) - Free download at [docker.com](https://docker.com)
   - This runs the application in a controlled environment
   - Think of it like a virtual computer just for this app

---

## 🚀 Getting Started (First Time Only)

### Step 1: Install Docker
1. Go to [docker.com/download](https://docker.com/download)
2. Download Docker for your computer type (Mac/Windows/Linux)
3. Install it like any other program
4. Open Docker and let it run (you'll see a Docker icon in your system tray)

### Step 2: Get the Project
1. Open your Terminal/Command Prompt
2. Copy and paste this command:
```bash
git clone https://github.com/Koundinya2003/review-engine.git
cd review-engine
```
(If you don't have `git`, download it from [git-scm.com](https://git-scm.com))

### Step 3: Start the Application
1. Open Terminal/Command Prompt
2. Navigate to the project folder (use `cd review-engine`)
3. Run this command:
```bash
docker-compose up -d
```
4. Wait 30-60 seconds for everything to start
5. Your system is ready! ✅

---

## 📱 Accessing the Application

### Dashboard (The User Interface)
Once started, open your web browser and go to:
```
http://localhost:8501
```

This is where you'll see:
- 📊 Charts and graphs
- 📝 Your reviews
- 🎯 Themes and patterns
- 📈 Analytics

---

## 🔐 Logging In

### First Time Login
You need to create an account before using the dashboard.

#### **Option A: Via Dashboard (Easy)**
1. Open http://localhost:8501
2. Click the **Register** tab
3. Enter:
   - **Username**: Something you'll remember (e.g., `john_admin`)
   - **Email**: Your email address
   - **Password**: A strong password (8+ characters)
4. Click **Register**
5. You're logged in! ✅

#### **Option B: Via Command Line (For Tech Users)**
```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "myusername",
    "email": "my@email.com",
    "password": "MyPassword123"
  }'
```

### Quick Test Account
If you just want to try it out quickly:
- **Username**: `demo`
- **Password**: `Demo12345`

---

## 📊 Using the Dashboard

### Main Navigation
The left sidebar has these sections:

#### **1. Dashboard (Home Page)**
- Overview of all your data
- Key statistics:
  - Total number of reviews
  - Average rating from reviews
  - Number of themes found
  - Recent insights

#### **2. Reviews**
- See all individual reviews
- Filter by:
  - Source (App Store, Play Store, Reddit, etc.)
  - Rating (1-5 stars)
  - Sentiment (positive, negative, neutral)
- Search for specific reviews
- Download as CSV file

#### **3. Themes**
- See all themes identified by AI
- Themes are common topics customers mention
- Examples:
  - "Battery life" - appears in 42 reviews
  - "User interface" - appears in 28 reviews
  - "Performance" - appears in 35 reviews

#### **4. Analytics**
- Detailed charts and graphs
- Trends over time
- Rating distribution
- Sentiment breakdown

#### **5. Upload Data**
- Add new reviews to analyze
- Supported formats:
  - CSV files (Excel)
  - JSON files
  - Paste text directly

---

## 📥 How to Upload and Analyze Reviews

### Method 1: Upload a File (Easiest)
1. Click **Upload Data** in the sidebar
2. Click **Choose File**
3. Select a CSV or JSON file with reviews
4. Click **Upload**
5. Wait for processing (usually 1-2 minutes)
6. See results on Dashboard

### Method 2: Paste Directly
1. Click **Upload Data**
2. Click **Paste Reviews**
3. Paste your reviews (one per line)
4. Click **Analyze**

### File Format (CSV Example)
If using Excel/CSV, your file should have columns like:
```
source,app_name,rating,text,date
app_store,MyApp,5,Great app! Love it!,2026-06-01
app_store,MyApp,3,Good but needs work,2026-06-02
```

---

## 💡 Understanding the Results

### What Are Themes?
Themes are common topics AI found in your reviews:
- **Theme**: "Crashes"
- **Count**: 23 reviews mentioned this
- **Trend**: Increasing over time (red = bad, green = good)

### What Is Sentiment?
How customers feel:
- 😊 **Positive**: Happy with the product (ratings 4-5)
- 😐 **Neutral**: Mixed feelings (rating 3)
- 😞 **Negative**: Unhappy (ratings 1-2)

### Reading the Charts
- **Line chart**: How things change over time
- **Bar chart**: Comparison between categories
- **Pie chart**: Proportion of the whole

---

## 🔧 Common Tasks

### Task 1: Export Data
1. Go to **Reviews** page
2. Click **Download as CSV** button
3. File saves to your Downloads folder
4. Open with Excel or Google Sheets

### Task 2: Find Reviews About Specific Topic
1. Go to **Reviews** page
2. Use **Search** box at top
3. Type a keyword (e.g., "battery")
4. See all matching reviews

### Task 3: See What Customers Liked Most
1. Go to **Analytics** page
2. Look at **Positive Themes** chart
3. These are things mentioned in good reviews

### Task 4: Find What Needs Improvement
1. Go to **Analytics** page
2. Look at **Negative Themes** chart
3. These are pain points to fix

### Task 5: Check Daily Trends
1. Go to **Analytics** page
2. Look at **Trend** charts
3. See if reviews are getting better or worse

---

## ❌ Troubleshooting

### Problem: "Cannot connect to API"
**What it means**: The server is not running  
**Solution**:
1. Open Terminal/Command Prompt
2. Run: `docker-compose ps`
3. If no containers running, start them: `docker-compose up -d`
4. Wait 30 seconds
5. Refresh the browser

### Problem: "Invalid credentials"
**What it means**: Username or password is wrong  
**Solution**:
1. Check spelling (uppercase/lowercase matters)
2. Make sure Caps Lock is off
3. Try registering a new account
4. Make sure password is 8+ characters

### Problem: Dashboard loads but no data shows
**What it means**: Database is loading  
**Solution**:
1. Wait 1-2 minutes
2. Refresh browser (Ctrl+R or Cmd+R)
3. Upload some sample reviews first

### Problem: "Permission denied" in logs
**What it means**: File access issue (can be ignored)  
**Solution**: This is normal, doesn't affect functionality

### Problem: Application is very slow
**What it means**: Too much data to process  
**Solution**:
1. Close other programs
2. Make sure Docker has enough memory (Settings > Resources)
3. Upload fewer reviews at once

---

## 🎓 Tips for Best Results

✅ **Do This:**
- Upload at least 50 reviews for better analysis
- Keep passwords secure
- Check analytics weekly to spot trends
- Export data regularly as backup

❌ **Don't Do This:**
- Don't close Docker while analyzing (wait for completion)
- Don't upload the same reviews twice
- Don't use very old reviews (more than 1 year)
- Don't share your login with others

---

## 📞 Getting Help

### Check These First
1. **Is Docker running?** Look for Docker icon in system tray
2. **Is the server started?** Try: `docker-compose ps`
3. **Is port 8501 available?** If another app uses it, there's a conflict
4. **Did you wait long enough?** First start takes 30-60 seconds

### If Problems Persist
1. Stop the application: `docker-compose down`
2. Start fresh: `docker-compose up -d`
3. Wait 60 seconds
4. Try again

---

## 📋 System Commands (Don't Worry If You Don't Know These!)

**These are "behind the scenes" commands if something goes wrong:**

```bash
# Start the application
docker-compose up -d

# Stop the application
docker-compose down

# See if everything is running
docker-compose ps

# See error messages
docker logs review-engine-api-1

# Completely restart
docker-compose down
docker-compose up -d
```

---

## 🎯 Common Questions (FAQ)

**Q: Do I need to know programming?**  
A: No! Just follow the steps above.

**Q: Can I use this offline?**  
A: After setup, yes. But first installation needs internet.

**Q: Is my data private?**  
A: Yes, everything runs on your computer locally.

**Q: Can I share this with my team?**  
A: Yes! On the same network, use: `http://[your-computer-ip]:8501`

**Q: How many reviews can it handle?**  
A: Thousands! Performance depends on your computer.

**Q: Can I delete reviews?**  
A: Currently no, but you can upload a new dataset to replace.

**Q: How often should I upload new reviews?**  
A: As often as you want! Daily is ideal for tracking trends.

**Q: What happens if I close the browser?**  
A: Your data is saved. Just open it again at `localhost:8501`

**Q: Can I export the results?**  
A: Yes! Click "Download as CSV" on the Reviews page.

---

## 🚀 You're Ready!

You now know everything needed to use the Review Discovery Engine. Start with these steps:

1. ✅ Install Docker
2. ✅ Clone the project
3. ✅ Run `docker-compose up -d`
4. ✅ Open `http://localhost:8501`
5. ✅ Register an account
6. ✅ Upload your first reviews
7. ✅ Explore the analytics!

---

## 📞 Quick Reference Card

| What I Want To Do | Where To Go | How Long |
|---|---|---|
| See overview | Dashboard | Instant |
| View reviews | Reviews page | Instant |
| Find common themes | Themes page | Instant |
| Analyze trends | Analytics page | Instant |
| Add new reviews | Upload Data | 1-2 min |
| Download data | Reviews page | 10 sec |
| Search for topic | Reviews search | Instant |
| Create account | Dashboard Register | 10 sec |
| Reset password | Coming soon | — |

---

## 🎉 You've Got This!

Don't worry about breaking anything - it's a local application just on your computer. Explore, experiment, and have fun discovering insights in your reviews!

**Happy analyzing!** 📊

---

*Last Updated: June 24, 2026*  
*Questions? Check the troubleshooting section above!*
