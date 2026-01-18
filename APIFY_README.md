# TMS Order Executor 🚀

Automated trading actor for NEPSE TMS (Trade Management System). Supports **Buying**, **Selling**, and **Order Verification** (Order Book extraction).

---

## ✨ Features

- **Buy & Sell**: Execute orders automatically.
- **Batch Trading**: Place multiple orders (Buy/Sell mix) in a single run.
- **Verification**: Automatically scrapes "Today's Order Book" after trading to verify order status (Optional).
- **CAPTCHA Solving**: Uses Google Gemini AI to solve TMS login CAPTCHAs.
- **S3 Upload**: Optionally uploads result JSON to Supabase Storage.
- **Versioning**: Logs version numbers for tracking.

---

## 📥 Input Schema

| Field | Type | Description | Required | Default |
|-------|------|-------------|:--------:|:-------:|
| `tmsUrl` | String | Full Broker URL (e.g., `https://tms58.nepsetms.com.np`) | ✅ | - |
| `tmsUsername` | String | TMS Login Username | ✅ | - |
| `tmsPassword` | String | TMS Login Password | ✅ | - |
| `geminiApiKey` | String | Google Gemini API Key (for CAPTCHA) | ✅ | - |
| `action` | String | `BUY`, `SELL`, or `CHECK_ORDERS`. (Ignored if `orders` array is present) | ✅ | `CHECK_ORDERS` |
| `orders` | Array | **Batch Mode**: List of orders to execute. See structure below. | ❌ | `[]` |
| `checkOrders` | Boolean | Scrape Order Book after trading? (Runs ONLY ONCE at end) | ❌ | `true` |
| `uploadToS3` | Boolean | Upload result to Supabase? | ❌ | `true` |

### Batch `orders` Structure
Use this for **Multiple Buys** or **Rebalancing**.

```json
[
  {
    "symbol": "NICA",
    "qty": 10,
    "price": 450,
    "side": "BUY"
  },
  {
    "symbol": "HIDCL",
    "qty": 50,
    "price": 200,
    "side": "SELL"
  }
]
```

### Single Mode Inputs (Legacy/Simple)
If `orders` is empty, the actor uses these top-level fields:
- `symbol`
- `buyPrice` / `buyQuantity` (for BUY action)
- `sellPrice` / `sellQuantity` (for SELL action)

---

## 📤 Output Schema

The actor produces a JSON result.

### Example Output
```json
{
    "version": "1.1.0",
    "status": "SUCCESS",
    "timestamp": "2026-01-18 12:00:00.000",
    "batch_results": [
        {
            "status": "SUBMITTED",
            "message": "Order submitted successfully",
            "buyEntryUrl": "...",
            "orderDetails": {
                "symbol": "NICA",
                "quantity": 10,
                "price": 450,
                "action": "BUY"
            }
        }
    ],
    "todaysOrderPage": [
        {
            "Order No": "12345",
            "Symbol": "NICA",
            "Type": "BUY",
            "Qty": "10",
            "Price": "450",
            "Status": "OPEN"
        }
    ]
}
```

---

## 🛠️ Setup & Security

1. **Credentials**: It is highly recommended to save `tmsUsername`, `tmsPassword`, `geminiApiKey`, and `tmsUrl` in the **Apify Actor Inputs** configuration to avoid passing them in every API call.
2. **Proxies**: Uses Apify Proxy (auto-configured) if available, or direct connection.
3. **Timeouts**: Default timeout is set to handle slow NEPSE servers.

---

## 🆘 Troubleshooting

- **Login Failed?**: Check `geminiApiKey` quota or invalid credentials. Use `HEADLESS=false` locally to debug.
- **404 Errors?**: Ensure `tmsUrl` is correct (e.g. `https://tms58.nepsetms.com.np`) and does NOT end with `/login` (the actor handles path construction).
- **Schema Errors?**: Ensure `orders` array items have all fields (`symbol`, `qty`, `price`, `side`).

---
v1.1.0
