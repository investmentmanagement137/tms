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
