# Convert TMS Scraper to Apify Actor
# Apify Actor: TMS Order Execution & Daily Order Scraper

## Goal Description
Convert the existing scraper into a **Trading Actor**.
1.  **Execute Buy Order**: Input symbol, price, quantity -> Place Order.
2.  **Verify**: Extract data from "Today's Order Book" to confirm.
3.  **Output**: JSON containing order details and the current order book.

## User Review Required
> [!IMPORTANT]
> **Trading Risk**: This actor will perform REAL TRADES. Ensure inputs are correct.
> **Validation**: The actor will attempt to click "Buy", but success depends on market status, funds, and TMS validation.

## Proposed Changes

### Configuration
#### [MODIFY] [.actor/input_schema.json](file:///c:/Users/purib/Downloads/antigravity/APIFy/tms%20captch%20new/.actor/input_schema.json)
- Add `action` (enum: `BUY`, `CHECK_ORDERS`).
- fields `symbol`, `buyPrice`, `buyQuantity` are required only if `action` is `BUY`.

### Configuration
#### [MODIFY] [.actor/input_schema.json](file:///c:/Users/purib/Downloads/antigravity/APIFy/tms%20captch%20new/.actor/input_schema.json)
- Add `tmsUrl` (string, required, e.g., "https://tms58.nepsetms.com.np").

### Logic
#### [MODIFY] [src/utils.py](file:///c:/Users/purib/Downloads/antigravity/APIFy/tms%20captch%20new/src/utils.py)
- Remove `get_tms_number`.
- `perform_login` now takes `tms_url` directly.

#### [MODIFY] [src/buy_stock.py](file:///c:/Users/purib/Downloads/antigravity/APIFy/tms%20captch%20new/src/buy_stock.py)
- Accept `tms_url`.
- Construct order URL using `f"{tms_url}/tms/n/order/order-entry"`.

#### [MODIFY] [src/daily_history.py](file:///c:/Users/purib/Downloads/antigravity/APIFy/tms%20captch%20new/src/daily_history.py)
- Accept `tms_url`.
- Construct history URL using `f"{tms_url}/tms/n/order/order-book"`.

#### [MODIFY] [main.py](file:///c:/Users/purib/Downloads/antigravity/APIFy/tms%20captch%20new/main.py)
- Read `tmsUrl` from input.
- Pass to login and action scripts.

## Verification Plan
### Automated Tests
- dry-run: Using a mocked "Click" (or verifying selectors without clicking) if possible, but user requested full execution.
- verification: Check output JSON for `todaysOrderPage` list.ble
- Keep all scraping logic intact

---

### Documentation

#### [NEW] [APIFY_README.md](file:///c:/Users/purib/Downloads/antigravity/APIFy/tms%20captch%20new/APIFY_README.md)
- Instructions for deploying to Apify
- How to configure inputs and secrets
- How to schedule runs
- Debugging tips

## Verification Plan

### Manual Verification
- [x] Local Testing: Test the Actor locally using `apify run` command
- [x] Apify Platform Deployment: Deploy to Apify and verify it runs successfully
- [x] Scheduled Run Setup: Configure schedule in Apify Console
- [x] Output Validation: Verify CSV is generated and uploaded to Supabase S3
