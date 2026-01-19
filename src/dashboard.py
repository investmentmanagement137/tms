from playwright.async_api import Page
from .toast_capture import log_toasts, capture_all_popups

async def extract_dashboard_data(page: Page, tms_url: str) -> dict:
    """
    Extracts summary data from the TMS Dashboard.
    Navigate to the desktop dashboard first to ensure correct structure.
    Returns a dictionary with keys: fundSummary, tradeSummary, collateralSummary, marketStatus
    """
    # Navigate to the Desktop dashboard (client/) as we have optimized selectors for it
    # main.py now guarantees a valid session before calling this
    dashboard_url = f"{tms_url.rstrip('/')}/tms/client/dashboard"
    
    # Optimization: If we are already on the dashboard, skip navigation
    if "dashboard" in page.url and "/tms/" in page.url:
         print(f"[DEBUG] Already on Dashboard ({page.url}), skipping navigation.")
    else:
         print(f"[DEBUG] Navigating to Dashboard: {dashboard_url}")
         try:
             await page.goto(dashboard_url, wait_until='networkidle', timeout=30000)
         except Exception as e:
             print(f"[DEBUG] Navigation failed: {e}")
             return {}

    try:
        # Wait for "Loading..." overlay to go away if it exists
        try:
            await page.wait_for_selector("text=Loading", state="hidden", timeout=10000)
            await page.wait_for_selector(".loading-overlay", state="hidden", timeout=5000)
        except:
             pass # ambiguous, just proceed

        # Changed to state='attached' because logs showed elements were 'hidden' but present
        # We can extract text from hidden DOM elements via JS
        await page.wait_for_selector(".card-header, .figure, .total-count", state='attached', timeout=30000)
        await page.wait_for_timeout(2000) # Extra buffer 
    except Exception as e:
        print(f"[DEBUG] Error loading dashboard elements (Attached check): {e}")
        # Proceed to extraction anyway, maybe JS can still find them
        
    print("Extracting dashboard data...")

    try:
        # We use page.evaluate to run extraction logic in the browser context
        data = await page.evaluate("""() => {
        const result = {
            fundSummary: {},
            tradeSummary: {},
            collateralSummary: {},
            marketStatus: "Unknown"
        };
        
        // Helper to clean text and remove potential tooltips
        const clean = (el) => {
            if (!el) return '';
            const clone = el.cloneNode(true);
            // Remove tooltips or unwanted nested elements if necessary
            clone.querySelectorAll('.tooltiptext, .tooltip__utilize, .tooltip__available').forEach(e => e.remove());
            return clone.textContent.replace(/[\\n\\t]/g, '').trim();
        };

        // Helper to find specific card by header text
        const findCard = (headerText) => {
            // Find all potential headers
            const headers = Array.from(document.querySelectorAll('.card-title, h5, .card-header'));
            const header = headers.find(el => el.textContent.includes(headerText));
            return header ? header.closest('.card') : null;
        };

        // --- 1. My Trade Summary ---
        const tradeCard = findCard("My Trade Summary");
        if (tradeCard) {
            // "Total Turnover" is in .total-count .h4
            const totalEl = tradeCard.querySelector('.total-count .h4');
            if (totalEl) result.tradeSummary['Total Turnover'] = clean(totalEl);
            
            // Other items are in .figure blocks
            tradeCard.querySelectorAll('.figure').forEach(fig => {
                const labelEl = fig.querySelector('.figure-label');
                const valueEl = fig.querySelector('.figure-value');
                if (labelEl && valueEl) {
                    const label = clean(labelEl);
                    const value = clean(valueEl);
                    result.tradeSummary[label] = value;
                }
            });
        }

        // --- 2. My Collateral Summary ---
        const colCard = findCard("My Collateral Summary");
        if (colCard) {
             // "Total Collateral" is in .total-count .h4
             const totalEl = colCard.querySelector('.total-count .h4');
             if (totalEl) result.collateralSummary['Total Collateral'] = clean(totalEl);
             
             // Extract items from figures
             colCard.querySelectorAll('.figure').forEach(fig => {
                const labelEl = fig.querySelector('.figure-label');
                const valueEl = fig.querySelector('.figure-value');
                if (labelEl && valueEl) {
                    const label = clean(labelEl);
                    const value = clean(valueEl);
                    result.collateralSummary[label] = value;
                }
            });
        }

        // --- 3. Fund Summary ---
        const fundCard = findCard("Fund Summary");
        if (fundCard) {
            fundCard.querySelectorAll('.figure').forEach(fig => {
                const labelEl = fig.querySelector('.figure-label');
                const valueEl = fig.querySelector('.figure-value');
                if (labelEl && valueEl) {
                    const label = clean(labelEl);
                    const value = clean(valueEl);
                    result.fundSummary[label] = value;
                }
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
    
    except Exception as e:
        print(f"[DEBUG] JS execution failed or timed out: {e}")
        # Return empty structure or verify failure in caller
        data = {}

    # Post-process results for logging
    if data:
        print(f"[DEBUG] Dashboard: Status={data.get('marketStatus')}")
        print(f"[DEBUG] Trade Summary: {data.get('tradeSummary')}")
        print(f"[DEBUG] Collateral: {data.get('collateralSummary')}")
    
    # Log any toast messages that appeared during extraction
    print("[DEBUG] Checking for any toast messages on dashboard...")
    await log_toasts(page, prefix="[DASHBOARD][TOAST]")
    
    return data
