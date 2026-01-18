# TMS Automation (Playwright + Apify) 🎭

A Python-based Apify Actor to automate buying/selling on NEPSE TMS.
Migrated from Selenium -> **Playwright** for better speed, stability, and evasion.

## 📂 Project Structure
- `src/`
  - `main.py`: Entry point (orchestrator).
  - `utils.py`: Login logic, Captcha solving (Gemini AI), Browser setup.
  - `buy_stock.py` / `sell_stock.py`: Trading logic.
  - `daily_history.py`: Order book scraper.
- `Dockerfile`: Apify actor definition (Python 3.12 + Playwright).
- `.actor/`: Apify metadata & input schema.

## 💻 Local Development

### Prerequisites
- Python 3.12+
- Playwright (`pip install playwright && playwright install`)
- `apify-cli` (optional, for pushing)

### Setup
```bash
# 1. Install Dependencies
pip install -r requirements.txt
playwright install

# 2. Run Locally (Set Environment Variables for inputs or edit main.py)
python main.py
```

## 🚀 Deployment (to Apify)

We use the Apify CLI to deploy.

```bash
# 1. Login to Apify
apify login

# 2. Deploy
apify push
```

## 🔒 Session Persistence
The actor uses `tms-sessions` (Named Key-Value Store) to save login state.
- **Local Dev**: Files are saved in `storage/key_value_stores/tms-sessions`.
- **Apify Cloud**: Persistent storage attached to your account.

## ⚠️ Disclaimer
This tool interacts with a live trading platform.
Use with caution. Start with small quantities.
The authors are not responsible for financial losses.

