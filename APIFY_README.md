# TMS Trade Book Scraper - Apify Actor

Automated scraper for NEPSE TMS (Trade Management System) Trade Book History, packaged as an Apify Actor.

## 🚀 Quick Start - Apify Platform

### 1. Deploy to Apify

1. **Create a new Apify Actor:**
   - Go to [Apify Console](https://console.apify.com/)
   - Click "Actors" → "Create new"
   - Choose "From scratch" or "Import from Git"

2. **Push code to Apify:**
   ```bash
   # Install Apify CLI
   npm install -g apify-cli
   
   # Login to Apify
   apify login
   
   # Initialize (if not already done)
   apify init
   
   # Push to Apify
   apify push
   ```

### 2. Configure Actor Inputs

In the Apify Console, set the following inputs:

| Input | Description | Required |
|-------|-------------|----------|
| **TMS Username** | Your TMS login username | ✅ Yes |
| **TMS Password** | Your TMS login password | ✅ Yes |
| **Gemini API Key** | Google Gemini API key for CAPTCHA solving | ✅ Yes |
| **Supabase S3 Endpoint** | Supabase S3 endpoint URL | ⚠️ For S3 upload |
| **Supabase S3 Region** | Supabase S3 region (default: ap-southeast-1) | ⚠️ For S3 upload |
| **Supabase Access Key** | Supabase S3 access key ID | ⚠️ For S3 upload |
| **Supabase Secret Key** | Supabase S3 secret key | ⚠️ For S3 upload |
| **Supabase Bucket Name** | Bucket name (default: investment_management) | ⚠️ For S3 upload |
| **Days to Scrape** | Number of days of history (default: 365) | No |
| **Upload to S3** | Enable S3 upload (default: true) | No |

### 3. Schedule Runs

Configure scheduled runs in Apify Console:

1. Go to your Actor → "Schedules" tab
2. Click "Create new schedule"
3. **Recommended schedules** (Nepal Time):
   - **Morning**: `45 4 * * 0-4` (9:45 AM NPT - before market)
   - **Evening**: `15 9 * * 0-4` (3:15 PM NPT - after market)

> **Note**: Nepal market operates Sunday-Thursday. Trade Book History is only accessible outside market hours (before 10:00 AM or after 3:05 PM NPT).

### 4. Run the Actor

- **Manual Run**: Click "Start" in Apify Console
- **Scheduled**: Runs automatically per schedule
- **API**: Use Apify API to trigger runs programmatically

---

## 🖥️ Local Development

### Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Install Apify CLI (for local runs)
npm install -g apify-cli
```

### Local Testing

1. **Create input file** (`.actor/INPUT.json`):
   ```json
   {
     "tmsUsername": "your_username",
     "tmsPassword": "your_password",
     "geminiApiKey": "your_gemini_api_key",
     "supabaseEndpoint": "https://xxx.storage.supabase.co/storage/v1/s3",
     "supabaseRegion": "ap-southeast-1",
     "supabaseAccessKey": "your_access_key",
     "supabaseSecretKey": "your_secret_key",
     "supabaseBucketName": "investment_management",
     "daysToScrape": 365,
     "uploadToS3": true
   }
   ```

2. **Run locally:**
   ```bash
   apify run
   ```

### Direct Python Run (without Apify)

You can still run the original script directly:

```bash
# Set environment variables
export TMS_USERNAME="your_username"
export TMS_PASSWORD="your_password"
export GEMINI_API_KEY="your_api_key"
export HEADLESS="false"

# Run
python trade_book.py
```

---

## 📦 Output

The Actor provides output in multiple formats:

1. **Apify Dataset**: Structured data viewable in Apify Console
2. **Key-Value Store**: CSV file stored as `OUTPUT`
3. **Supabase S3**: Uploaded CSV (if enabled)

### Accessing Output

- **Dataset**: `https://console.apify.com/actors/[actor-id]/runs/[run-id]#dataset`
- **CSV Download**: `https://console.apify.com/storage/key-value-stores/[store-id]`
- **S3**: Check your Supabase bucket

---

## 🔧 Troubleshooting

### Login Fails
- Verify credentials are correct
- Check if Gemini API key is valid and has quota
- Ensure you're not running during market hours

### No Data Scraped
- Verify you're running **outside market hours** (before 10 AM or after 3:05 PM Nepal Time)
- Check the debug HTML file saved in the run output
- Review Actor logs in Apify Console

### S3 Upload Fails
- Verify all Supabase credentials are correct
- Check bucket name and permissions
- Ensure endpoint URL is correct

### Memory Issues
- Apify free tier has 2GB RAM limit
- Consider upgrading to paid plan if needed
- Reduce `daysToScrape` to lower memory usage

---

## 📁 File Structure

```
.
├── .actor/
│   ├── actor.json          # Actor manifest
│   └── input_schema.json   # Input configuration schema
├── Dockerfile              # Docker configuration
├── main.py                 # Apify entry point
├── trade_book.py           # Main scraping logic
├── tms_utils.py            # Login & CAPTCHA utilities
├── tms_login.py            # Simple login script
├── requirements.txt        # Python dependencies
└── APIFY_README.md         # This file
```

---

## 🔑 Features

- ✅ Automated CAPTCHA solving using Gemini AI
- ✅ Configurable date range (days to scrape)
- ✅ Supabase S3 upload support
- ✅ Apify dataset output for easy viewing
- ✅ Scheduled runs support
- ✅ Market hours detection
- ✅ Pagination handling
- ✅ Anti-bot detection measures

---

## 📝 Migration from GitHub Actions

If you were using GitHub Actions before:

1. **Secrets Migration**: Copy all GitHub Secrets to Apify Actor inputs
2. **Schedule**: Convert cron schedules to Apify schedules
3. **Monitoring**: Use Apify's built-in monitoring instead of GitHub Actions logs

### GitHub vs Apify Comparison

| Feature | GitHub Actions | Apify |
|---------|----------------|-------|
| **Scheduling** | Cron in workflow YAML | UI-based schedules |
| **Secrets** | Repository secrets | Actor inputs (isSecret) |
| **Logs** | Actions tab | Actor runs page |
| **Storage** | Artifacts (7 days) | Key-value store (indefinite) |
| **Monitoring** | Email notifications | Webhooks, email, Slack |
| **Cost** | Free (with limits) | Free tier: 100 Actor hours/month |

---

## 🆘 Support

For issues or questions:
1. Check Actor logs in Apify Console
2. Review the debug HTML file (if scraping fails)
3. Verify market hours and credentials
4. Contact Apify support for platform issues

---

## 📄 License

Private use only.
