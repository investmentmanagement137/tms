from playwright.async_api import Page

async def extract_dashboard_data(page: Page) -> dict:
    """
    Extracts summary data from the TMS Dashboard.
    Returns a dictionary with keys:
      - collateral: { amount, utilized, available }
      - limits: { total, utilized, available }
      - summary_items: list of { label, value }
    """
    print("Extracting dashboard data...")
    
    # We use page.evaluate to run extraction logic in the browser context
    # This is faster and more robust for scraping multiple elements
    data = await page.evaluate("""() => {
        const result = {
            collateral: {},
            limits: {},
            summary_items: [],
            marketStatus: "Unknown"
        };

        // Helper to clean text
        const clean = (text) => text ? text.replace(/[\\n\\t]/g, '').trim() : '';

        // 1. Extract .figure items (Collateral, Trade Summary, etc.)
        // Validated structure: div.figure > span.figure-label, span.figure-value
        const figures = document.querySelectorAll('.figure');
        figures.forEach(fig => {
            const labelEl = fig.querySelector('.figure-label');
            const valEl = fig.querySelector('.figure-value');
            if (labelEl && valEl) {
                const label = clean(labelEl.textContent);
                const value = clean(valEl.textContent);
                
                // Collateral
                if (label.includes('Collateral Amount')) result.collateral.amount = value;
                if (label.includes('Collateral Utilized')) result.collateral.utilized = value;
                if (label.includes('Collateral Available')) result.collateral.available = value;
                
                // Generic Summary Items
                result.summary_items.push({ label, value });
            }
        });

        // 2. Extract Trading Limits (often in tooltips or specific cards)
        // If not found in figures, check specific IDs/Classes if known
        // For now, rely on figures as they cover most summary data
        
        // 3. Market Status Detection
        const ledGreen = document.querySelector('.led-green');
        const ledRed = document.querySelector('.led-red');
        const blinker = document.querySelector('.blinker'); // continuous session often has this
        
        if (ledGreen) {
            result.marketStatus = "OPEN";
        } else if (ledRed) {
            result.marketStatus = "CLOSED";
        } else if (blinker) {
             result.marketStatus = "OPEN (Blinking)";
        }
        
        // 4. Fallback: Check header status icon color
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
    
    # Post-process / Log
    if data:
        print(f"[DEBUG] Dashboard Extracted: Status={data.get('marketStatus')} | Collateral={data.get('collateral')}")
    
    return data
