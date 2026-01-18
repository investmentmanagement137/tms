import time
import time
import datetime
import os
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support import expected_conditions as EC
from .utils import get_tms_number
from bs4 import BeautifulSoup

class TMSClient:
    def __init__(self, driver):
        self.driver = driver
        self.base_url = "https://tms{}.nepsetms.com.np" 

    def extract_daily_order_book(self):
        """
        Extracts today's order book to verify the placed order.
        Returns a list of order dictionaries.
        """
        tms_no = get_tms_number(self.driver.current_url)
        # Verify URL for daily order book
        order_book_url = f"https://tms{tms_no}.nepsetms.com.np/tms/n/order/order-book"
        
        print(f"[DEBUG] Navigating to Daily Order Book: {order_book_url}")
        self.driver.get(order_book_url)
        time.sleep(5)
        
        orders = []
        try:
            # Check for headers
            headers = []
            header_row = self.driver.find_elements(By.CSS_SELECTOR, "table thead tr th")
            if not header_row:
                 header_row = self.driver.find_elements(By.CSS_SELECTOR, ".k-grid-header th")
            headers = [h.text.strip() for h in header_row]
            print(f"[DEBUG] Order Book Headers: {headers}")

            # Get rows via BS4 for speed
            table_html = self.driver.execute_script("return document.querySelector('table').outerHTML;")
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
                        orders.append(row_data) # Fallback list
        except Exception as e:
            print(f"[DEBUG] Error extracting order book: {e}")
            
        return orders

    def place_order(self, action, symbol, quantity, price, order_type="LMT", validity="DAY"):
        """
        Places a BUY/SELL order.
        Returns a dictionary with status, message, and URL.
        """
        print(f"\n[DEBUG] Placing {action} Order: {symbol}, Qty: {quantity}, Price: {price}")
        
        tms_no = get_tms_number(self.driver.current_url)
        # Order Entry URL
        order_url = f"https://tms{tms_no}.nepsetms.com.np/tms/n/order/order-entry"
        
        print(f"[DEBUG] Navigating to Order Entry: {order_url}")
        self.driver.get(order_url)
        time.sleep(3)
        
        result = {
            "status": "FAILED",
            "message": "",
            "buyEntryUrl": order_url,
            "orderDetails": {
                "symbol": symbol,
                "quantity": quantity,
                "price": price,
                "action": action
            }
        }
        
        try:
            # 1. Select Buy/Sell
            if action.upper() == "BUY":
                 try:
                     # Try multiple selectors for BUY tab
                     buy_tab = self.driver.find_element(By.XPATH, "//a[contains(text(), 'Buy')]")
                     buy_tab.click()
                 except:
                     self.driver.execute_script("document.querySelector('.btn-buy, .buy-tab').click()")
                 print("[DEBUG] Selected BUY tab")
            
            time.sleep(1)

            # 2. Enter Symbol
            print(f"[DEBUG] Entering Symbol: {symbol}")
            sym_input = self.driver.find_element(By.CSS_SELECTOR, "input[placeholder='Symbol'], input[name='symbol']")
            sym_input.clear()
            sym_input.send_keys(symbol)
            time.sleep(1)
            # Trigger autocomplete selection
            from selenium.webdriver.common.keys import Keys
            sym_input.send_keys(Keys.TAB)
            time.sleep(1)

            # 3. Enter Quantity
            print(f"[DEBUG] Entering Quantity: {quantity}")
            qty_input = self.driver.find_element(By.CSS_SELECTOR, "input[placeholder='Qty'], input[name='quantity']")
            qty_input.clear()
            qty_input.send_keys(str(quantity))

            # 4. Enter Price
            print(f"[DEBUG] Entering Price: {price}")
            price_input = self.driver.find_element(By.CSS_SELECTOR, "input[placeholder='Price'], input[name='price']")
            price_input.clear()
            price_input.send_keys(str(price))
            
            time.sleep(1)
            
            # 5. Verify filled data (Optional but good)
            
            # 6. Click Submit/Buy Button
            print("[DEBUG] Clicking Buy Button...")
            submit_btn = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit'], button.btn-primary, button.btn-success")
            
            if "Place Order" in submit_btn.text or "Buy" in submit_btn.text:
                submit_btn.click()
                print("[DEBUG] Clicked Submit.")
            else:
                 print("[DEBUG] Warning: Submit button text mismatch? Clicking anyway.")
                 submit_btn.click()
            
            # 7. Check for Confirmation / Success / Error
            time.sleep(2)
            
            # Check for error toast/message
            error_msg = ""
            try:
                toasts = self.driver.find_elements(By.CSS_SELECTOR, ".toast-message, .alert-danger")
                for t in toasts:
                    if t.is_displayed():
                        error_msg += t.text + " "
            except:
                pass
                
            if error_msg:
                print(f"[DEBUG] Order Error: {error_msg}")
                result["message"] = f"Error: {error_msg}"
                result["status"] = "ERROR"
            else:
                # Assume success if no error and URL changed or confirm dialog appeared
                # For now, we assume click worked.
                print("[DEBUG] Order Submitted (No immediate error detected).")
                result["status"] = "SUBMITTED"
                result["message"] = "Order submitted successfully"
                
        except Exception as e:
            print(f"[DEBUG] Error placing order: {e}")
            result["message"] = str(e)
            result["status"] = "EXCEPTION"
            
        return result


