# Dashboard Extraction Fix Walkthrough

## Issue
The dashboard extraction was returning empty or incomplete data specifically for:
- "Total Turnover" in Trade Summary.
- "Total Collateral" in Collateral Summary.
- Some values contained tooltip text (e.g., dates) mixed with the numbers.

## Root Cause
The HTML structure places "Total" values in a separate `.total-count .h4` container, not in the standard `.figure-value` class used for other items. The previous script only looked for `.figure-value`.

## Fix
Updated `src/dashboard.py` to:
1. Specifically target `.total-count .h4` for the main "Total" values in Trade and Collateral cards.
2. Implement a robust `clean()` function that clones the element and removes tooltip nodes (`.tooltiptext`, `.tooltip__utilize`, etc.) before extracting text.

## Dashboard Extraction Fix (Production)

## Dashboard Extraction Fix (Production)

### Issue
The bot was failing to extract dashboard data. Logs claimed "Session is VALID", but debug artifacts (`dashboard_fail_dump.html`) showed the **Login Page**.

### Root Cause
The session verification logic in `main.py` relied only on the URL (`.../tms/m/dashboard`). However, the TMS application (an SPA) maintains the dashboard URL in the browser bar even when internally redirecting to the login component due to an expired session. This caused a **false positive** validation. The bot assumed it was logged in, skipped re-login, and then failed when trying to extract data from what was actually the login page.

### Resolution
1.  **Enhanced Session Verification (`main.py`)**: 
    - Moved away from simple URL checking.
    - Now explicitly waits for dashboard-specific DOM elements (`.nf-dashboard`, `.box`, `app-dashboard`, `.user-profile`) to confirm the session is truly active.
    - If these elements are missing (or login elements appear), the session is marked invalid, forcing a fresh login.
2.  **Dashboard URL (`src/dashboard.py`)**: 
    - Reverted to using the **Client Dashboard** (`/tms/client/dashboard`).
    - Since the session verification is now robust, we can safely use the Desktop dashboard (for which our selectors are optimized) without fear of redirect loops (as a fresh login will be performed if needed).

### Verification
- **Production:** Run the Actor on Apify.
- **Success Criteria:** 
    - Logs should show either "Session is VALID! Found dashboard elements" OR "Executing Login Script...".
    - `dashboard_fail_dump.html` should NOT be generated.
    - Final output JSON should contain populated `dashboard` data (Fund Summary, etc.).

### Logic Flow Fix (v1.3.1)
After fixing the session verification, a secondary issue was found where the bot **exited immediately** after detecting an expired session.
- **Cause:** The main execution logic (Login + Extraction) was accidentally indented *inside* the `except` block of the session verification. This meant it only ran if the session check crashed, not if it gracefully reported "Session expired".
- **Fix:** Restructured `main.py` to ensure the Login/Extraction block runs sequentially after the session check, wrapped in its own `try/except` for safety.

## Verification
Created a script `verify_dashboard_extraction_local.py` that:
1. Loads the provided `dashboard_dump.html`.
2. Mocks the page navigation to stay on the dump file.
3. Runs the `extract_dashboard_data` logic.

### Results
The extraction now yields:
```json
{
  "fundSummary": {
    "Collateral Amount": "NPR. 2,000,000.00",
    "Payable Amount(NPR)": "0.00",
    "Receivable Amount(NPR)": "6,989,672.32",
    "Net Receivable Amount(NPR)": "6,989,672.32",
    "Net Payable Amount(NPR)": "0.00"
  },
  "tradeSummary": {
    "Total Turnover": "NPR. 0.00",
    "Traded Shares": "0",
    "Transactions": "0",
    "Scrips Traded": "0",
    "Buy Count": "0",
    "Buy Summary": "0",
    "Sell Count": "0",
    "Sell Summary": "0"
  },
  "collateralSummary": {
    "Total Collateral": "NPR. 2,000,000.00",
    "Collateral Utilized": "0.00",
    "Collateral Available": "2,000,000.00"
  },
  "marketStatus": "OPEN"
}
```

## How to Run Verification
```bash
python verify_dashboard_extraction_local.py
```
