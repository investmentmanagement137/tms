from playwright.async_api import Page

async def extract_dashboard_data(page: Page, tms_url: str) -> dict:
    """
    Extracts summary data from the TMS Dashboard.
    Navigate to the desktop dashboard first to ensure correct structure.
    Returns a dictionary with keys: fundSummary, tradeSummary, collateralSummary, marketStatus
    """
    dashboard_url = f"{tms_url.rstrip('/')}/tms/client/dashboard"
    print(f"[DEBUG] Navigating to Dashboard: {dashboard_url}")
    
    try:
        await page.goto(dashboard_url, wait_until='networkidle')
        await page.wait_for_selector('.card-header, .figure', timeout=10000)
        await page.wait_for_timeout(2000) # Extra buffer for dynamic values
    except Exception as e:
        print(f"[DEBUG] Error loading dashboard: {e}")
        return {}

    print("Extracting dashboard data...")
    
    # We use page.evaluate to run extraction logic in the browser context
    data = await page.evaluate("""() => {
        const result = {
            fundSummary: {},
            tradeSummary: {},
            collateralSummary: {},
            marketStatus: "Unknown"
        };
        
        // Helper to clean text
        const clean = (text) => text ? text.replace(/[\\n\\t]/g, '').trim() : '';

        // Helper to find specific card by header text
        const findCard = (headerText) => {
            const headers = Array.from(document.querySelectorAll('.card-header, .card-title, h5'));
            const header = headers.find(el => el.textContent.includes(headerText));
            return header ? header.closest('.card') : null;
        };

        // --- 1. My Trade Summary ---
        const tradeCard = findCard("My Trade Summary");
        if (tradeCard) {
            // "Total Turnover" is often the main figure
            const mainVal = tradeCard.querySelector('.figure-value');
            if (mainVal) result.tradeSummary['Total Turnover'] = clean(mainVal.textContent);
            
            // Other items are in .figure blocks or rows
            tradeCard.querySelectorAll('.figure').forEach(fig => {
                const label = clean(fig.querySelector('.figure-label')?.textContent);
                const value = clean(fig.querySelector('.figure-value')?.textContent);
                if (label && value) result.tradeSummary[label] = value;
            });
        }

        // --- 2. My Collateral Summary ---
        const colCard = findCard("My Collateral Summary");
        if (colCard) {
             const mainVal = colCard.querySelector('.figure-value');
             if (mainVal) result.collateralSummary['Total Collateral'] = clean(mainVal.textContent);
             
             // Utilized / Available are often in separate smaller blocks or labeled spans
             // Inspect showed labels like "Collateral Utilized"
             colCard.querySelectorAll('div, span').forEach(el => {
                 const text = clean(el.textContent);
                 if (text === "Collateral Utilized") {
                     // Value is likely next sibling or in parent's next sibling
                     const val = el.parentElement.querySelector('.text-bold, .figure-value, span:nth-child(2)');
                     if(val) result.collateralSummary['Utilized'] = clean(val.textContent);
                 }
                 if (text === "Collateral Available") {
                     const val = el.parentElement.querySelector('.text-bold, .figure-value, span:nth-child(2)');
                     if(val) result.collateralSummary['Available'] = clean(val.textContent);
                 }
             });
             
             // Fallback: Check .figure loop if standard structure
             colCard.querySelectorAll('.figure').forEach(fig => {
                const label = clean(fig.querySelector('.figure-label')?.textContent);
                const value = clean(fig.querySelector('.figure-value')?.textContent);
                if (label && value) result.collateralSummary[label] = value;
            });
        }

        // --- 3. Fund Summary ---
        const fundCard = findCard("Fund Summary");
        if (fundCard) {
            fundCard.querySelectorAll('.row > div').forEach(col => {
                 // Often formatted as Label ... Value or Label [Value]
                 // We look for specific known labels:
                 const text = clean(col.textContent);
                 if (text.includes("Collateral Amount")) {
                     const val = col.querySelector('.figure-value, .hover-over');
                     if(val) result.fundSummary['Collateral Amount'] = clean(val.textContent);
                 }
                 if (text.includes("Net Receivable")) {
                     const val = col.querySelector('.figure-value, .hover-over');
                     if(val) result.fundSummary['Net Receivable'] = clean(val.textContent);
                 }
                 if (text.includes("Net Payable")) {
                     const val = col.querySelector('.figure-value, .hover-over');
                     if(val) result.fundSummary['Net Payable'] = clean(val.textContent);
                 }
            });
            // Try generic figure capture for Fund Card too
            fundCard.querySelectorAll('.figure').forEach(fig => {
                const label = clean(fig.querySelector('.figure-label')?.textContent);
                const value = clean(fig.querySelector('.figure-value')?.textContent);
                if (label && value) result.fundSummary[label] = value;
            });
        }

        // --- 4. Market Status ---
        const ledGreen = document.querySelector('.led-green');
        const ledRed = document.querySelector('.led-red');
        const blinker = document.querySelector('.blinker');
        
        if (ledGreen) result.marketStatus = "OPEN";
        else if (ledRed) result.marketStatus = "CLOSED";
        else if (blinker) result.marketStatus = "OPEN (Blinking)";
        
        if (result.marketStatus === "Unknown") {
             const statusIcon = document.querySelector('.market-status-icon');
             if (statusIcon) {
                 const color = window.getComputedStyle(statusIcon).backgroundColor;
                 if (color.includes('255, 0, 0') || color.includes('red')) result.marketStatus = "CLOSED";
                 else if (color.includes('0, 128, 0') || color.includes('green')) result.marketStatus = "OPEN";
             }
        }

        return result;
    }""")
    
    # Post-process results for logging
    if data:
        print(f"[DEBUG] Dashboard: Status={data.get('marketStatus')}")
        print(f"[DEBUG] Trade Summary: {data.get('tradeSummary')}")
        print(f"[DEBUG] Collateral: {data.get('collateralSummary')}")
    
    return data
