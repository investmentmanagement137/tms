# ✅ Deployment Complete!

## GitHub Repository

**Repository**: https://github.com/investmentmanagement137/tms

Your TMS scraper has been successfully pushed to GitHub with all Apify Actor files!

---

## 🔒 Security Changes Made

### Hardcoded Credentials Removed

All sensitive credentials have been **removed** from `trade_book.py`:

```python
# ✅ BEFORE (Insecure - hardcoded)
USERNAME = os.environ.get("TMS_USERNAME", "Bp480035")
PASSWORD = os.environ.get("TMS_PASSWORD", "E3!xdpZ11@@")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "AIzaSy...")
SUPABASE_ACCESS_KEY = os.environ.get("SUPABASE_ACCESS_KEY", "20e24ef9...")
SUPABASE_SECRET_KEY = os.environ.get("SUPABASE_SECRET_KEY", "3e72f2bd...")

# ✅ AFTER (Secure - environment variables only)
USERNAME = os.environ.get("TMS_USERNAME", "")
PASSWORD = os.environ.get("TMS_PASSWORD", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
SUPABASE_ACCESS_KEY = os.environ.get("SUPABASE_ACCESS_KEY", "")
SUPABASE_SECRET_KEY = os.environ.get("SUPABASE_SECRET_KEY", "")
```

**Your actual credentials are now safe** - they'll need to be set in:
- Apify Actor inputs (recommended)
- Environment variables (for local testing)

---

## 📦 What's in the Repository

```
✅ .actor/
   ├── actor.json              # Actor manifest
   ├── input_schema.json       # Input configuration
   └── INPUT.example.json      # Template for local testing
✅ Dockerfile                  # Apify container build
✅ main.py                     # Apify entry point
✅ trade_book.py               # Main scraper (credentials removed)
✅ tms_utils.py                # Login utilities
✅ tms_login.py                # Login test script
✅ requirements.txt            # Python dependencies
✅ APIFY_README.md             # Full documentation
✅ DEPLOY.md                   # Quick deploy guide
✅ .gitignore                  # Protects sensitive files
```

---

## 🚀 Next Steps

### 1. Deploy to Apify Platform

```bash
# Install Apify CLI (if not already installed)
npm install -g apify-cli

# Login to Apify
apify login

# Push to Apify from your local directory
cd "c:\Users\purib\Downloads\antigravity\APIFy\tms captch new"
apify push
```

### 2. Configure Apify Actor Inputs

Go to [Apify Console](https://console.apify.com/) and set:

**Required:**
- ✅ TMS Username: `Bp480035`
- ✅ TMS Password: `E3!xdpZ11@@`
- ✅ Gemini API Key: `AIzaSyC184Uw7BV4-QjCCbSddnIt1i9wn-K2Dbw`

**Optional (S3 Upload):**
- Supabase Endpoint: `https://unbgkfatcaztstordiyt.storage.supabase.co/storage/v1/s3`
- Supabase Region: `ap-southeast-1`
- Supabase Access Key: `20e24ef90a5b78cbe4a72a476affbd49`
- Supabase Secret Key: `3e72f2bdb31a4abe284acca9ee6ef22e02e9a2c8ed3fb1fdb007127ee8438a21`
- Supabase Bucket: `investment_management`

### 3. Set Up Schedule

**Recommended cron schedules** (Nepal Time):

```
After market:  30 9 * * 0-4   (3:15 PM NPT / 9:30 AM UTC)
Before market: 0 4 * * 0-4    (9:45 AM NPT / 4:00 AM UTC)
```

Market operates Sunday-Thursday.

---

## 📊 Alternative: Deploy from GitHub to Apify

Instead of pushing from local, you can connect GitHub directly:

1. Go to [Apify Console](https://console.apify.com/)
2. Create New Actor → "From Git Repository"
3. Enter: `https://github.com/investmentmanagement137/tms`
4. Branch: `main`
5. Click "Create"

Apify will automatically pull from GitHub and build the Actor!

---

## 🔗 Quick Links

- 📚 **Full Documentation**: [APIFY_README.md](https://github.com/investmentmanagement137/tms/blob/main/APIFY_README.md)
- 🚀 **Quick Deploy Guide**: [DEPLOY.md](https://github.com/investmentmanagement137/tms/blob/main/DEPLOY.md)
- 🐙 **GitHub Repository**: https://github.com/investmentmanagement137/tms
- 🎯 **Apify Console**: https://console.apify.com/

---

## ⚠️ Important Reminders

1. **Credentials are removed from code** - Set them in Apify Console
2. **S3 upload is optional** - Works without Supabase if you don't set those inputs
3. **Market hours matter** - Run outside 10 AM - 3:05 PM NPT for best results
4. **GitHub Actions disabled** - You can delete `.github/workflows/scrape.yml` if you want

---

## 🎉 You're All Set!

Your TMS scraper is now:
- ✅ Secure (no hardcoded credentials)
- ✅ On GitHub (version controlled)
- ✅ Ready for Apify (just run `apify push`)
- ✅ Fully documented

**Next action**: Run `apify push` to deploy! 🚀
