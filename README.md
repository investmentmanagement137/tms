# TMS Trade Book History Scraper

Automated scraper for NEPSE TMS (Trade Management System) Trade Book History with Supabase S3 upload.

## Features

- 🔐 Automated login with CAPTCHA solving (using Gemini AI)
- 📊 Scrapes Trade Book History for the last 365 days
- 📄 Exports data to CSV
- ☁️ Uploads to Supabase S3 storage
- ⏰ GitHub Actions scheduled runs (before/after market hours)
- 🔧 Configurable via environment variables

## Local Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure credentials** in `trade_book.py` or set environment variables:
   ```bash
   export TMS_USERNAME="your_username"
   export TMS_PASSWORD="your_password"
   export GEMINI_API_KEY="your_gemini_api_key"
   ```

3. **Run the scraper:**
   ```bash
   python trade_book.py
   ```

## GitHub Actions Setup

1. **Push this repo to GitHub**

2. **Add Repository Secrets** (Settings → Secrets and variables → Actions):
   | Secret Name | Description |
   |-------------|-------------|
   | `TMS_USERNAME` | Your TMS login username |
   | `TMS_PASSWORD` | Your TMS login password |
   | `GEMINI_API_KEY` | Google Gemini API key for CAPTCHA |
   | `SUPABASE_ENDPOINT` | Supabase S3 endpoint URL |
   | `SUPABASE_REGION` | Supabase S3 region |
   | `SUPABASE_ACCESS_KEY` | Supabase S3 access key |
   | `SUPABASE_SECRET_KEY` | Supabase S3 secret key |
   | `SUPABASE_BUCKET_NAME` | Target bucket name |

3. **The workflow runs automatically:**
   - Mon-Fri at 4:00 AM UTC (9:45 AM Nepal) - Before market
   - Mon-Fri at 9:30 AM UTC (3:15 PM Nepal) - After market

4. **Manual trigger:** Go to Actions tab → "TMS Trade Book Scraper" → "Run workflow"

## Files

| File | Description |
|------|-------------|
| `trade_book.py` | Main scraper script (login, scrape, upload) |
| `tms_login.py` | Simple login-only script |
| `tms_utils.py` | Reusable login & CAPTCHA utilities |
| `.github/workflows/scrape.yml` | GitHub Actions workflow |

## Market Hours Note

Trade Book History is only accessible **outside market hours**:
- Before 10:00 AM Nepal Time
- After 3:05 PM Nepal Time

The GitHub Actions schedule is configured to run during these windows.

## License

Private use only.
