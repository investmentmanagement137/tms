from selenium.webdriver.common.by import By
import time
from bs4 import BeautifulSoup

def extract(driver, tms_url):
    """
    Extracts today's order book.
    Returns a list of order dictionaries.
    """
    base_url = tms_url.rstrip('/')
    order_book_url = f"{base_url}/tms/n/order/order-book"
    
    print(f"[DEBUG] Navigating to Daily Order Book: {order_book_url}")
    driver.get(order_book_url)
    time.sleep(5)
    
    orders = []
    try:
        # Check for headers
        headers = []
        header_row = driver.find_elements(By.CSS_SELECTOR, "table thead tr th")
        if not header_row:
             header_row = driver.find_elements(By.CSS_SELECTOR, ".k-grid-header th")
        headers = [h.text.strip() for h in header_row]
        print(f"[DEBUG] Order Book Headers: {headers}")

        # Get rows via BS4
        table_html = driver.execute_script("return document.querySelector('table').outerHTML;")
        soup = BeautifulSoup(table_html, 'html.parser')
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
