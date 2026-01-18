import asyncio
from bs4 import BeautifulSoup

async def extract(page, tms_url):
    """
    Extracts today's order book (Async Playwright).
    Returns a list of order dictionaries.
    """
    base_url = tms_url.rstrip('/')
    order_book_url = f"{base_url}/tms/n/order/order-book"
    
    print(f"[DEBUG] Navigating to Daily Order Book: {order_book_url}")
    await page.goto(order_book_url, wait_until='networkidle')
    await page.wait_for_timeout(3000) # Wait for table load
    
    orders = []
    try:
        # Get Header Text
        headers = []
        # We can extract text directly or via soup. Soup is robust.
        # Let's use Soup on the whole table area
        
        # Verify table exists
        try:
            await page.wait_for_selector("table", timeout=5000)
        except:
            print("[DEBUG] No table found on Order Book page.")
            return []

        # Get HTML
        try:
            table_html = await page.evaluate("document.querySelector('table').outerHTML")
        except:
             # Fallback if multiple tables or structure differs
             print("[DEBUG] Failed to select 'table', trying content()")
             table_html = await page.content()
             
        soup = BeautifulSoup(table_html, 'html.parser')
        
        # Headers
        header_row = soup.select("table thead tr th")
        if not header_row:
             header_row = soup.select(".k-grid-header th")
        headers = [h.get_text(strip=True) for h in header_row]
        print(f"[DEBUG] Order Book Headers: {headers}")

        # Rows
        rows = soup.select('tbody tr')
        
        print(f"[DEBUG] Found {len(rows)} orders in Order Book.")
        
        for row in rows:
            cols = row.find_all('td')
            row_data = [c.get_text(strip=True) for c in cols]
            
            if len(row_data) > 1 and "No records" not in row_data[0]:
                if len(headers) == len(row_data):
                    order_dict = dict(zip(headers, row_data))
                    orders.append(order_dict)
                else:
                    orders.append(row_data)
                    
    except Exception as e:
        print(f"[DEBUG] Error extracting order book: {e}")
        
    return orders
