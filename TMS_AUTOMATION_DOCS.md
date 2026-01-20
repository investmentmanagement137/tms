# TMS Automation System Documentation

## 1. System Overview
The **TMS Automation System** is a robust, Python-based robotic process automation (RPA) tool designed to automate trading operations on the NEPSE Trade Management System (TMS). It is built to run as an **Apify Actor**, allowing for cloud-based execution, scheduling, and API integration, but can also run locally.

**Key Capabilities:**
- **Automated Login** with AI-powered Captcha Solving (Google Gemini).
- **Session Persistence** to minimize login overhead.
- **Order Execution** (Buy/Sell) with high reliability strategies.
- **Data Scrapping** (Order Book, Dashboard, Collateral).
- **Real-time Feedback** via Toast/Popup capture.
- **Cloud Integration** via Apify (Inputs/Outputs/Storage).

---

## 2. Architecture & Technology Stack
- **Core Engine:** Python 3.12+
- **Browser Automation:** Playwright (Async) - chosen for speed and modern web support.
- **Captcha Solving:** Google Gemini Flash 2.0 API (Vision).
- **Containerization:** Docker (for Apify deployment).
- **State Management:** Apify Key-Value Stores (for sessions and cookies).

### Directory Structure
```
tms-automation/
├── main.py                 # Entry point (Apify Actor)
├── src/
│   ├── login.py            # Login orchestration
│   ├── utils.py            # Core logic (Captcha, Login low-level, Session)
│   ├── buy_stock.py        # Buy order logic
│   ├── sell_stock.py       # Sell order logic
│   ├── dashboard.py        # Dashboard data extraction
│   ├── daily_history.py    # Order book verification
│   └── toast_capture.py    # Notification capture utility
├── .actor/                 # Apify configuration
└── requirements.txt        # Python dependencies
```

---

## 3. Workflow & Processes

### A. Authentication & Login
The login process is the most critical and complex part of the system, designed to handle TMS's instability and security measures.

1.  **Session Restoration:** 
    - On startup, the system checks the Apify Key-Value Store (`tms-sessions`) for a saved browser state (cookies/local storage).
    - It attempts to navigate directly to the Dashboard. If successful, login is skipped (Fast Path).

2.  **Fresh Login (if session invalid):**
    - **Navigation:** Uses robust navigation strategies (networkidle, domcontentloaded, commit) and handles timeouts/crashes by reloading or creating a fresh browser context.
    - **Captcha Solving:**
        - Captures a screenshot of the captcha image.
        - Sends the image to **Google Gemini API** with a prompt to extract the alphanumeric text.
        - Fills the solved text into the input field.
    - **Credential Entry:** Robustly finds and fills Username/Password using multiple fallback selectors.
    - **Validation:** Verifies login by checking for dashboard elements (`app-client-dashboard`, `.user-profile`).

3.  **Error Handling:**
    - Detects "Invalid Captcha" toasts and auto-retries.
    - Captures screenshots (`login_fail_final.png`) and HTML dumps if login fails.

### B. Order Execution (Buy/Sell)
The order placement modules (`buy_stock.py`, `sell_stock.py`) use a "Hybrid Injection" strategy to bypass UI flakiness.

1.  **Navigation:** Navigates directly to the Order Entry page with the symbol in the URL (e.g., `?symbol=NICA`).
2.  **Form Filling (JavaScript Injection):**
    - Instead of relying solely on Playwright's `type/click` (which can be flaky with Angular forms), the system uses `page.evaluate()` to directly set values on the underlying DOM elements and dispatch Angular events (`input`, `change`, `blur`, `keyup`) to trigger validation.
    - Sets **Quantity**, **Price**, and **Instrument** (Equity/Debenture).
3.  **Submission:**
    - Identifies the correct "Submit" button (ignoring Cancel/Close buttons).
    - Handles "Confirmation" dialogs (SweetAlert) automatically.
4.  **Result Capture (Toast Capture):**
    - Uses `toast_capture.py` to intercept system notifications (Red Error / Green Success / Blue Info).
    - Logs the exact server response (e.g., "Order placed successfully" or "Order Rejected: Insufficient balance").

### C. Data Extraction
- **Dashboard:** Extracts real-time "Trade Summary", "Collateral", and "Fund Summary" from the Dashboard. It uses DOM scraping to read values even if they are momentarily hidden by overlays.
- **Daily History:** Verifies orders by scraping the "Daily Order Book" table to confirm the transaction appears in the system.

---

## 4. Error Handling & Robustness

The system implements a "Defensive Automation" philosophy:

- **Browser Recovery:** If a page crashes (`ERR_ABORTED`) or freezes, the system automatically closes the context and spawns a new one.
- **Selector Fallbacks:** Every critical interaction (clicking buttons, finding inputs) has a list of 3-5 fallback selectors to handle UI updates or A/B tests.
- **Toast Logging:** All system messages (toasts) are captured and logged to the console (e.g., `[LOGIN][TOAST] Invalid Password`).
- **Debug Artifacts:** On critical failures, the system saves:
    - `screenshot.png`: User's view at time of failure.
    - `dump.html`: Full DOM structure for offline debugging.
    - `error.log`: Python tracebacks.

---

## 5. Apify Integration

### Inputs (INPUT.json)
The Actor accepts a JSON configuration:
```json
{
    "tmsUrl": "https://tms43.nepsetms.com.np",
    "tmsUsername": "YOUR_USERNAME",
    "tmsPassword": "YOUR_PASSWORD",
    "geminiApiKey": "AIzaSy...",
    "action": "BATCH",
    "orders": [
        {"symbol": "NICA", "qty": 10, "price": 500, "side": "BUY"},
        {"symbol": "HIDCL", "qty": 20, "price": 200, "side": "SELL"}
    ]
}
```

### Outputs
- **Dataset:** Pushes a structured JSON record for each run containing:
    - Execution status
    - Batch results (for each order)
    - Dashboard summary
- **Key-Value Store:**
    - `OUTPUT`: The full final JSON result.
    - `SESSION`: The serialized browser state (cookies) for the next run.

### Running Locally
You can test the full flow locally using the wrapper script:
```bash
# Requires secrets.json or hardcoded credentials
python test_login_toast.py
```
Or run the main entry point if configured:
```bash
python main.py
```
