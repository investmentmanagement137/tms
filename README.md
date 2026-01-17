# TMS Automation Apify Actor

This Apify Actor automates interactions with the NEPSE TMS (Trade Management System). It supports login (with Gemini-powered Captcha solving), extracting trade books, and placing Buy/Sell orders.

## Features

- 🔐 **Automated Login**: Handles login flow including dynamic Captcha solving using Google Gemini API.
- 📊 **Extract Tradebook**: Scrapes trade book history for the last 365 days.
- 🛒 **Buy/Sell Orders**: Automates order placement (Limit orders).
- 🧩 **Apify Integration**: Fully integrated with Apify platform (Inputs, Dataset, Docker).

## Input Configuration

The Actor accepts the following input settings (defined in `input_schema.json`):

| Field | Type | Description |
|-------|------|-------------|
| `tmsWebsiteNo` | String | The TMS instance number (e.g., "58", "49"). Default: "58". |
| `tmsLoginId` | String | Your TMS User ID / Client Code. |
| `tmsPassword` | String | Your TMS Password. |
| `geminiApiKey` | String | Google Gemini API Key for captcha solving. |
| `action` | Enum | Action to perform: `EXTRACT_TRADEBOOK`, `BUY`, `SELL`, `EXTRACT_INFO`. |
| `orderDetails` | Object | JSON object for order details (e.g., `{"symbol": "NICA", "quantity": 10, "price": 500}`). |

## Local Development

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Run Locally**:
   You can run the actor locally by setting environment variables or modifying `src/main.py` inputs directly for testing.
   ```bash
   python src/main.py
   ```

## Files Structure

- `src/`
  - `main.py`: Entry point for the Actor.
  - `tms_client.py`: Class handling TMS interactions (Page Object Model style).
  - `utils.py`: Utilities for login and captcha solving.
- `input_schema.json`: Defines the input UI for Apify.
- `Dockerfile`: Configuration for building the Actor image.
- `old_scripts/`: Archived original scripts.

## Deployment to Apify

1. Push this code to a Git repository.
2. Create a new Actor on Apify.
3. Connect the Actor to your Git repository.
4. Build and Run.

## Safety Note

This tool performs sensitive financial actions (Trading). Ensure you test thoroughly with small quantities or in a safe environment if available. The authors are not responsible for any financial losses.
