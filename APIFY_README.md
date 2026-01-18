# TMS Order Executor 🚀

Automated trading actor for NEPSE TMS (Trade Management System). Built with **Playwright** for speed and stability.

---

## ✨ Features

- **⚡ Fast Execution**: Uses **Session Persistence** to skip Login & Captcha on repeat runs!
- **🤖 Smart Login**: Solves CAPTCHAs automatically using **Google Gemini AI**.
- **📦 Batch Trading**: Place multiple BUY/SELL orders in one go (JSON input).
- **🛡️ Stealth Mode**: Bypasses basic bot detection (403 Forbidden).
- **✅ Verification**: Optionally scrapes "Today's Order Book" to confirm orders.

---

## 📥 Input Guide

### 1. Credentials (Recommended: Use Saved Tasks)
To avoid sending sensitive data in every API call, create a **Saved Task** on Apify and safely store:
*   `tmsUrl`: Your broker URL (e.g., `https://tms58.nepsetms.com.np`)
*   `tmsUsername`: Client Code
*   `tmsPassword`: Password
*   `geminiApiKey`: Google Gemini API Key

### 2. Action Modes

| Action | Description | Required Inputs |
|:---:|---|---|
| **BATCH** | Execute a list of orders. | `orders` (Array) |
| **BUY** | Place a single buy order. | `symbol`, `quantity`, `price` |
| **SELL** | Place a single sell order. | `symbol`, `quantity`, `price` |

### 3. Batch Orders Example (`orders` array)
```json
[
  { "symbol": "NICA", "qty": 10, "price": 450, "side": "BUY" },
  { "symbol": "HIDCL", "qty": 50, "price": 200, "side": "SELL" }
]
```

---

## ⚡ Session Persistence
This actor automatically saves your login session (Cookies/Local Storage) to a private store (`tms-sessions`).
*   **Run 1**: Logs in (takes ~20s). Saves Session.
*   **Run 2+**: **Skips Login** (takes ~3s). Trades immediately.

*Note: Sessions usually expire after a few hours. The actor handles re-login automatically.*

---

## 📤 Output
Returns a JSON object with status and order details:

```json
{
    "version": "1.1.0",
    "status": "SUCCESS",
    "batch_results": [
        { "status": "SUBMITTED", "symbol": "NICA", "action": "BUY", ... }
    ],
    "todaysOrderPage": [ ... ]
}
```

