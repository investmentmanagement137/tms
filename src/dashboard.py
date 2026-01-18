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
            summary_items: []
        };

        // Helper to clean text
        const clean = (text) => text ? text.replace(/[\\n\\t]/g, '').trim() : '';

        // 1. Extract .figure items (Collateral, etc.)
        // Structure: div.figure > span.figure-label, span.figure-value
        const figures = document.querySelectorAll('.figure');
        figures.forEach(fig => {
            const labelEl = fig.querySelector('.figure-label');
            const valEl = fig.querySelector('.figure-value');
            if (labelEl && valEl) {
                const label = clean(labelEl.textContent);
                const value = clean(valEl.textContent);
                
                if (label.includes('Collateral Amount')) result.collateral.amount = value;
                if (label.includes('Collateral Utilized')) result.collateral.utilized = value;
                if (label.includes('Collateral Available')) result.collateral.available = value;
            }
        });

        // 2. Extract Trading Limits from Tooltips or Chart Items
        // The structure dump showed 'Available Trading Limit: ...' inside .tooltiptext
        // usually found inside .line-chart .chart-item
        const tooltips = document.querySelectorAll('.tooltiptext');
        tooltips.forEach(tt => {
            const text = clean(tt.textContent);
            if (text.includes('Utilized Trading Limit')) {
                result.limits.utilized = text.split(':').pop().trim();
            }
            if (text.includes('Available Trading Limit')) {
                result.limits.available = text.split(':').pop().trim();
            }
        });

        // 3. Extract Summary Items (Top bar or other boxes)
        // Try .data__summary--item if they exist (dump said 0, but logic stays just in case)
        document.querySelectorAll('.data__summary--item').forEach(item => {
            const num = item.querySelector('.data__summary--num');
            if (num) {
                const value = clean(num.textContent);
                // Label is usually the other span
                const spans = item.querySelectorAll('span');
                let label = '';
                spans.forEach(s => {
                    if (s !== num) label = clean(s.textContent);
                });
                result.summary_items.push({ label, value });
            }
        });
        
        return result;
    }""")
    
    print(f"Extracted Dashboard Data: {data}")
    return data
