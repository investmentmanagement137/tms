---
name: NEPSE TMS Automation
description: Guide and standard operating procedures for automating the NEPSE Trade Management System (TMS) using Playwright.
---
# NEPSE TMS Automation Skill 🎭

This skill documents the structure, logic, and automation strategies for the NEPSE TMS (Trade Management System) website. It is based on the working `tms-order-executor` actor.

## 🔗 Base Configuration

*   **URL Pattern**: `https://tms{NEPSE_ID}.nepsetms.com.np`
    *   *Example*: `https://tms58.nepsetms.com.np` (Stock Broker No. 58)
    *   *Note*: The ID varies by broker. Automation must be dynamic.
*   **Timezone**: Asia/Kathmandu (UTC+5:45)
*   **Operating Hours**: Sunday - Thursday (11:00 AM - 3:00 PM NPT). *Pre-open: 10:30 AM.*

## 🔐 Authentication & Session Logic

TMS uses CAPTCHA protected login and standard session cookies.

### 1. Login Logic
*   **URL**: `{BASE_URL}/login`
*   **Selectors**:
    *   **Username**: `input[placeholder="Client Code/ User Name"]` OR `input[name="username"]`
    *   **Password**: `#password-field` OR `input[name="password"]`
    *   **Captcha Image**: `img.captcha-image-dimension`
    *   **Captcha Input**: `#captchaEnter`
    *   **Login Button**: `.login__button`
*   **Flow**:
    1.  Navigate to `/login`.
    2.  Check if redirected to `/tms/m/dashboard` (Already logged in?).
    3.  Solve Captcha (Download image -> Gemini API).
    4.  Fill Credentials & Captcha -> Click Login.
    5.  Wait for URL to contain `dashboard` or `tms/me`.

### 2. Session Persistence (Cookie Strategy)
*   **Valid Session Indicator**: Accessing `/tms/m/dashboard` returns status 200 and does NOT redirect to `/login`.
*   **Storage**: Save `context.storage_state()` (cookies + localStorage).
*   **Re-use**: Load storage state on initialization. If accessing specific page fails (403/Redirect), clear cookies and perform full login.

## 🛡️ Anti-Bot Evasion (Stealth)

TMS uses basic fingerprinting and WAF rules.
*   **Detection Triggers**: `navigator.webdriver` property.
*   **Bypass Strategy**:
    *   **Chrome Args**: `--disable-blink-features=AutomationControlled`, `--disable-infobars`.
    *   **Init Script**:
        ```javascript
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined})
        ```
    *   **User Agent**: Use a standard, modern Desktop User Agent.

## 🛒 Order Entry Logic

*   **URL**: `{BASE_URL}/tms/me/memberclientorderentry`
*   **Selectors**:
    *   **Buy Tab**: `//a[contains(text(), 'Buy')]` or `.btn-buy`
    *   **Sell Tab**: `//a[contains(text(), 'Sell')]` or `.btn-sell`
    *   **Instrument**: `select[name='instrument']` or NG-Select via `text='INST'`.
    *   **Symbol Input**: `input[name="symbol"]` (Requires `Tab` press to trigger autocomplete fetch).
    *   **Quantity**: `input[name="quantity"]`
    *   **Price**: `input[name="price"]`
    *   **Submit Button**: `button[type='submit']`, `.btn-primary`

    > **On-Page Verification**: After submission, we extract the "Order Book" table (rows `.table tbody tr`) on the same page to confirm the order status immediately, avoiding extra navigation.

## 📚 Terminology & Data Structures

It is critical to distinguish between the two types of "Order" tables:

1.  **Order Book (User's Orders)**:
    *   **Definition**: The list of orders *placed by the logged-in user*. Contains your Open, Executed, and Cancelled orders.
    *   **Targeted by this Skill**: YES. We extract this to verify if our automated orders were submitted successfully.
    *   **Selectors**: `.k-grid-content tbody tr` (Data rows), `.k-grid-header` (Headers).

2.  **Market Depth (Top 5 Buy/Sell)**:
    *   **Definition**: The live list of the best 5 Buy and Sell orders *from the entire market* for a specific security.
    *   **Targeted by this Skill**: NO. We do explicitly ignore this data to avoid confusion.
    *   **Note**: Often displayed in a separate panel or popup. Do not confuse this with your personal Order Book.

## 📊 Data Extraction (Order Book)

*   **URL**: `{BASE_URL}/tms/n/order/order-book`
*   **Structure**: Kendo UI Grid or Standard Table.
*   **Selectors**:
    *   **Table**: `table`
    *   **Headers**: `thead tr th` or `.k-grid-header th`
    *   **Rows**: `tbody tr`
*   **Note**: Table loads dynamically. Use `wait_until='networkidle'` or specific `wait_for_selector('table')`.

## ⚠️ Common Errors & Fixes

| Error | Cause | Fix |
| :--- | :--- | :--- |
| `403 Forbidden` | WAF detection / Bad User Agent | Enable Stealth args & Init Script. |
| `Page crashed` | Browser OOM or bad state | catch `page.reload()` errors and restart context. |
| `Net::ERR_ABORTED` | Session invalid mid-request | Clear cookies and re-login. |
| `Fake Dashboard URL` | App shows `/dashboard` URL but renders Login page (Guard Redirect) | **Do not trust URL.** Check for elements like `.user-profile` or `app-dashboard`. |

## 📝 Dashboard Data Extraction
 
*   **URL**: `{BASE_URL}/tms/client/dashboard`
*   **Method**: `page.evaluate()` to scrape dynamic Angular text content.
*   **Key Selectors**:
    *   **Collateral Amount**: `span.figure-label` containing "Collateral Amount" -> sibling `span.figure-value`.
    *   **Utilized Collateral**: `span.figure-label` containing "Collateral Utilized" -> sibling `span.figure-value`.
    *   **Available Collateral**: `span.figure-label` containing "Collateral Available" -> sibling `span.figure-value`.
    *   **Trading Limits**: Extracted from `span.tooltiptext` elements containing "Utilized Trading Limit" or "Available Trading Limit".

