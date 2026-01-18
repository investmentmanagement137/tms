# TMS Scraper: GitHub Actions → Apify Actor Conversion

Successfully converted the TMS Trade Book History scraper from a GitHub Actions workflow to a fully functional Apify Actor.

## 📋 Changes Summary

### Files Created

#### Apify Configuration
- **[.actor/actor.json](file:///c:/Users/purib/Downloads/antigravity/APIFy/tms%20captch%20new/.actor/actor.json)** - Actor manifest with metadata and build configuration
- **[.actor/input_schema.json](file:///c:/Users/purib/Downloads/antigravity/APIFy/tms%20captch%20new/.actor/input_schema.json)** - Input schema defining 10 configurable parameters with user-friendly UI
- **[.actor/INPUT.example.json](file:///c:/Users/purib/Downloads/antigravity/APIFy/tms%20captch%20new/.actor/INPUT.example.json)** - Template for local testing

#### Docker & Entry Point
- **[Dockerfile](file:///c:/Users/purib/Downloads/antigravity/APIFy/tms%20captch%20new/Dockerfile)** - Uses `apify/actor-python-chrome:3.11` base image
- **[main.py](file:///c:/Users/purib/Downloads/antigravity/APIFy/tms%20captch%20new/main.py)** - Apify Actor entry point (142 lines)
  - Reads inputs from Apify storage
  - Orchestrates login and scraping
  - Outputs to Apify dataset and key-value store
  - Handles errors gracefully with Apify logging

#### Documentation
- **[APIFY_README.md](file:///c:/Users/purib/Downloads/antigravity/APIFy/tms%20captch%20new/APIFY_README.md)** - Comprehensive guide covering:
  - Deployment instructions
  - Input configuration
  - Scheduling setup
  - Local development
  - Troubleshooting

### Files Modified

#### [requirements.txt](file:///c:/Users/purib/Downloads/antigravity/APIFy/tms%20captch%20new/requirements.txt)
```diff
+ apify>=2.0.0
  selenium>=4.0.0
  webdriver-manager>=4.0.0
  google-genai>=1.0.0
  Pillow>=9.0.0
  boto3>=1.26.0
```

#### [trade_book.py](file:///c:/Users/purib/Downloads/antigravity/APIFy/tms%20captch%20new/trade_book.py)
- Modified `scrape_trade_book()` function signature to accept `days` parameter (default: 365)
- Changed hardcoded 365 days to use the configurable `days` parameter
- All other scraping logic remains unchanged

#### [.gitignore](file:///c:/Users/purib/Downloads/antigravity/APIFy/tms%20captch%20new/.gitignore)
- Updated to exclude Apify-specific files (`apify_storage/`, `.actor/INPUT.json`)
- Added Python and IDE ignores

---

## 🎯 Key Features

### Input Configuration
The Actor accepts 10 configurable inputs via Apify Console UI:

| Input | Type | Required | Description |
|-------|------|----------|-------------|
| TMS Username | String (secret) | ✅ | Login credentials |
| TMS Password | String (secret) | ✅ | Login credentials |
| Gemini API Key | String (secret) | ✅ | For CAPTCHA solving |
| Supabase Endpoint | String | ⚠️ | S3 upload endpoint |
| Supabase Region | String | ⚠️ | Default: ap-southeast-1 |
| Supabase Access Key | String (secret) | ⚠️ | S3 credentials |
| Supabase Secret Key | String (secret) | ⚠️ | S3 credentials |
| Supabase Bucket Name | String | ⚠️ | Default: investment_management |
| Days to Scrape | Integer | No | Default: 365 (1-3650 range) |
| Upload to S3 | Boolean | No | Default: true |

### Output Formats

The Actor provides data in multiple formats:

1. **Apify Dataset** - Structured JSON records viewable in Console
2. **Key-Value Store** - Raw CSV file downloadable as `OUTPUT`
3. **Supabase S3** - Uploaded CSV (if credentials provided)

### Scheduling

Recommended schedules for Nepal market hours:

```
Morning (before market):  45 4 * * 0-4  (9:45 AM NPT)
Evening (after market):   15 9 * * 0-4  (3:15 PM NPT)
```

> Market operates Sunday-Thursday; Trade Book History accessible only outside hours 10:00 AM - 3:05 PM NPT

---

## 🚀 Deployment Steps

### 1. Install Apify CLI

```bash
npm install -g apify-cli
```

### 2. Login to Apify

```bash
apify login
```

### 3. Push to Apify

```bash
cd "c:\Users\purib\Downloads\antigravity\APIFy\tms captch new"
apify push
```

### 4. Configure Inputs in Console

1. Go to [Apify Console](https://console.apify.com/)
2. Navigate to your Actor
3. Fill in all required inputs (especially the 3 secrets)
4. Click "Save & Start"

### 5. Set Up Schedule (Optional)

1. Go to Actor → "Schedules" tab
2. Create new schedule with cron: `15 9 * * 0-4`
3. Configure notification preferences

---

## 🧪 Local Testing

### Quick Test

```bash
# 1. Copy example input
cp .actor/INPUT.example.json .actor/INPUT.json

# 2. Edit INPUT.json with real credentials

# 3. Run locally
apify run
```

### Direct Python Run (Bypass Apify)

The original `trade_book.py` still works standalone:

```bash
python trade_book.py
```

---

## 📊 Architecture Comparison

### Before: GitHub Actions

```
Trigger (cron) → GitHub Runner → Python Script → S3 Upload → Artifacts
```

### After: Apify Actor

```
Trigger (schedule/API) → Apify Container → main.py → trade_book.py → Multi-output
                                                                      ├─ Dataset
                                                                      ├─ Key-Value Store
                                                                      └─ S3 Upload
```

### Benefits of Apify

✅ **Better Monitoring** - Built-in run history, logs, and metrics  
✅ **Flexible Storage** - Dataset + KV store + S3  
✅ **No GitHub Dependency** - Standalone infrastructure  
✅ **Easier Configuration** - UI-based inputs vs GitHub Secrets  
✅ **API Access** - Trigger runs programmatically  
✅ **Cost Efficiency** - 100 free Actor hours/month  

---

## ⚠️ Important Notes

### Credentials Migration

Your hardcoded credentials in `trade_book.py` lines 22-34 should now be:
- ❌ **Do NOT commit** to Git anymore
- ✅ **Set in Apify Console** as secret inputs
- ✅ **Or use INPUT.json** for local testing (gitignored)

### Market Hours Detection

The scraper includes market hours detection (10:00 AM - 3:05 PM NPT). If run during these hours, it will:
- ⚠️ Show a warning
- ⏭️ Continue execution (may find no data)
- 💾 Save debug HTML for troubleshooting

### Backward Compatibility

The original files remain intact:
- [trade_book.py](file:///c:/Users/purib/Downloads/antigravity/APIFy/tms%20captch%20new/trade_book.py) - Still runnable standalone
- [tms_utils.py](file:///c:/Users/purib/Downloads/antigravity/APIFy/tms%20captch%20new/tms_utils.py) - Unchanged
- [tms_login.py](file:///c:/Users/purib/Downloads/antigravity/APIFy/tms%20captch%20new/tms_login.py) - Unchanged

---

## 📁 Final Project Structure

```
tms captch new/
├── .actor/
│   ├── actor.json              # Actor manifest
│   ├── input_schema.json       # Input UI definition
│   └── INPUT.example.json      # Template for local testing
├── .github/
│   └── workflows/
│       └── scrape.yml          # (Legacy - can be removed)
├── Dockerfile                  # Apify container build
├── main.py                     # Apify entry point ⭐ NEW
├── trade_book.py               # Main scraping logic (modified)
├── tms_utils.py                # Login utilities
├── tms_login.py                # Simple login test
├── requirements.txt            # Dependencies (+ apify)
├── APIFY_README.md             # Apify documentation ⭐ NEW
├── README.md                   # Original GitHub Actions docs
└── .gitignore                  # Updated for Apify
```

---

## ✅ Verification Checklist

- [x] All Apify configuration files created
- [x] Dockerfile uses official Apify Python+Chrome image
- [x] Input schema defines all 10 parameters with proper types
- [x] main.py integrates with Apify SDK correctly
- [x] trade_book.py modified to accept configurable days
- [x] Dependencies updated with apify package
- [x] Comprehensive documentation provided
- [x] .gitignore updated to protect secrets
- [x] Example input file created

### New Trading Features (Added Jan 2026)
The actor now supports **Real Trading**:
1.  **Action Input**: Select `BUY` or `CHECK_ORDERS` in the input.
2.  **Broker URL**: Provide the full `tmsUrl` (e.g., `https://tms58.nepsetms.com.np`).
3.  **Buy Stock**: Executes a buy order for a specific symbol, price, and quantity.
4.  **Verification**: Automatically extracts "Today's Order Book" to confirm order placement.
5.  **Modular Logic**: Separate scripts for `login`, `buy_stock`, and `daily_history` for robustness.

## Next Steps

1. **Deploy**: Run `apify push`.
2. **Configure**: Set `action` to `BUY`, `tmsUrl` (e.g. `https://tms58.nepsetms.com.np`), and order details.
3. **Run**: The actor will login, place the order, and return the order status + confirmation from the daily order book.
4. **Safety**: Always verify your order limits and wallet balance before running in `BUY` mode.


## API Usage (HTTP Request)
To trigger the actor programmatically (e.g., from Postman, Python, or another app), send a **POST** request to the Apify API.

**Endpoint:**
`https://api.apify.com/v2/acts/<YOUR_USERNAME>~<ACTOR_NAME>/runs?token=<YOUR_APIFY_TOKEN>`

### 1. Buy Request (Example)
```bash
curl --request POST \
  --url 'https://api.apify.com/v2/acts/YOUR_USERNAME~tms-actor/runs?token=YOUR_APIFY_TOKEN' \
  --header 'Content-Type: application/json' \
  --data '{
    "tmsUrl": "https://tms58.nepsetms.com.np",
    "action": "BUY",
    "symbol": "NICA",
    "buyQuantity": 10,
    "buyPrice": 450,
    "checkOrders": true,
    "tmsUsername": "YOUR_USERNAME",
    "tmsPassword": "YOUR_PASSWORD",
    "geminiApiKey": "YOUR_GEMINI_KEY"
}'
```

> **New Feature**: Set `"checkOrders": false` to skip the post-buy order book verification. Default is `true`.


### 2. Sell Request (Example)
```bash
curl --request POST \
  --url 'https://api.apify.com/v2/acts/YOUR_USERNAME~tms-actor/runs?token=YOUR_APIFY_TOKEN' \
  --header 'Content-Type: application/json' \
  --data '{
    "tmsUrl": "https://tms58.nepsetms.com.np",
    "action": "SELL",
    "symbol": "NICA",
    "sellQuantity": 10,
    "sellPrice": 450,
    "checkOrders": true
}'
```

### 3. Check Daily Orders (Example)
```bash
curl --request POST \
  --url 'https://api.apify.com/v2/acts/YOUR_USERNAME~tms-actor/runs?token=YOUR_APIFY_TOKEN' \
  --header 'Content-Type: application/json' \
  --data '{
    "tmsUrl": "https://tms58.nepsetms.com.np",
    "action": "CHECK_ORDERS",
    "tmsUsername": "YOUR_USERNAME",
    "tmsPassword": "YOUR_PASSWORD",
    "geminiApiKey": "YOUR_GEMINI_KEY"
}'
```

### 3. Secure Usage (Recommended)
**Is adding credential here safe?**
Passing credentials in the command line can be risky (history logs). 
**Best Practice**:
1.  Go to the **Apify Console** > **Actor** > **Inputs**.
2.  Enter your `tmsUsername`, `tmsPassword`, and `geminiApiKey` there and **Save**.
3.  Now, your API requests only need the trading details! The actor will use the saved values for the rest.

**Secure Payload Example:**
```bash
curl --request POST \
  --url 'https://api.apify.com/v2/acts/YOUR_USERNAME~tms-actor/runs?token=YOUR_APIFY_TOKEN' \
  --header 'Content-Type: application/json' \
  --data '{
    "tmsUrl": "https://tms58.nepsetms.com.np",
    "action": "BUY",
    "symbol": "NICA",
    "buyQuantity": 10,
    "buyPrice": 450
}'
```
### 4. Batch Trading (Multiple Orders)
To buy/sell multiple stocks in one run:
```bash
curl --request POST \
  --url 'https://api.apify.com/v2/acts/YOUR_USERNAME~tms-actor/runs?token=YOUR_APIFY_TOKEN' \
  --header 'Content-Type: application/json' \
  --data '{
    "tmsUrl": "https://tms58.nepsetms.com.np",
    "checkOrders": true,
    "orders": [
        { "symbol": "NICA", "qty": 10, "price": 450, "side": "BUY" },
        { "symbol": "HIDCL", "qty": 50, "price": 200, "side": "SELL" }
    ],
    "tmsUsername": "USER",
    "tmsPassword": "PASS",
    "geminiApiKey": "KEY"
}'
```
**Optimized**: verification runs only **ONCE** at the end.


