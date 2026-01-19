# Implementation Plan - Debugging Dashboard Extraction

The dashboard data extraction is failing silently or returning empty data in the production environment, despite working with local static dumps. This plan aims to add robustness and detailed debugging information to identify the root cause.

## User Review Required
None. These are debugging and robustness improvements.

## Proposed Changes

### `src/dashboard.py`
- [MODIFY] Increase `wait_for_selector` timeout from 10s to 30s to handle slow loading.
- [MODIFY] Add `try-except` block *inside* the `extract_dashboard_data` function specifically around the `page.evaluate` call to catch JS execution errors.
- [MODIFY] Add a check to verify if the page URL actually matches the expected dashboard URL before attempting extraction.

### `main.py` (Root)
- [MODIFY] In the `Extract Dashboard Data` block:
  - Add explicit error logging (stack trace).
  - **Crucial**: If extraction fails (returns empty or raises exception), save the current page HTML (`dashboard_fail_dump.html`) and valid screenshot (`dashboard_fail.png`). This will allow us to see exactly what the bot sees when it fails.

## Verification Plan

### Automated Verification
1. **Local Dump Test**: Re-run `verify_dashboard_extraction_local.py` to ensure changes didn't break the logic for the known good dump.
   - Command: `python verify_dashboard_extraction_local.py`

### Production Verification (User)
1. The user will run the actor on Apify.
2. If it fails again, we will now have `dashboard_fail_dump.html` and `dashboard_fail.png` in the Key-Value store (or logs) to inspect.
