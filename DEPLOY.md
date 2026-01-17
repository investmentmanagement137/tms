# 🚀 Quick Deploy - Apify Actor

## Prerequisites
```bash
# Install Apify CLI
npm install -g apify-cli
```

## Deploy to Apify

```bash
# 1. Login
apify login

# 2. Navigate to project
cd "c:\Users\purib\Downloads\antigravity\APIFy\tms captch new"

# 3. Push to Apify
apify push
```

## Configure in Console

1. Go to https://console.apify.com/
2. Find your Actor: **tms-trade-book-scraper**
3. Click "Settings" → "Input"
4. Fill in **required secrets**:
   - ✅ TMS Username
   - ✅ TMS Password  
   - ✅ Gemini API Key
5. (Optional) Fill in Supabase S3 credentials if you want S3 upload
6. Click **"Save & Start"**

## Set Up Schedule

**Recommended schedules** (Nepal Time - Market is Sun-Thu):

```bash
# After market close (3:15 PM NPT = 9:30 AM UTC)
Cron: 30 9 * * 0-4

# Before market open (9:45 AM NPT = 4:00 AM UTC)  
Cron: 0 4 * * 0-4
```

## Local Testing (Optional)

```bash
# 1. Create input file
cp .actor/INPUT.example.json .actor/INPUT.json

# 2. Edit INPUT.json with your credentials
notepad .actor/INPUT.json

# 3. Run locally
apify run
```

---

## 📝 Important Reminders

⚠️ **Remove hardcoded credentials** from `trade_book.py` before pushing to Git!

Currently lines 22-34 have your real credentials. Either:
- Remove them (set to empty strings)
- Use environment variables
- Use Apify inputs (recommended)

⚠️ **Market Hours**: The scraper works best **outside** market hours (10 AM - 3:05 PM NPT)

✅ **GitHub Actions**: You can now **disable or delete** the `.github/workflows/scrape.yml` file

---

## 🔗 Quick Links

- 📚 Full Documentation: [APIFY_README.md](file:///c:/Users/purib/Downloads/antigravity/APIFy/tms%20captch%20new/APIFY_README.md)
- 🎯 Apify Console: https://console.apify.com/
- 📖 Apify Docs: https://docs.apify.com/
