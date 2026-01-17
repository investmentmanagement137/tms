import time
import csv
import datetime
import os
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support import expected_conditions as EC
from utils import get_tms_number

class TMSClient:
    def __init__(self, driver):
        self.driver = driver
        self.base_url = "https://tms{}.nepsetms.com.np" 

    def get_market_status(self):
        # Optional: Check if market is open
        pass

    def extract_tradebook(self, months=12):
        print("\n" + "="*30)
        print("[DEBUG] STARTING TRADE BOOK SCRAPING")
        print("="*30)
        
        tms_no = get_tms_number(self.driver.current_url)
        history_url = f"https://tms{tms_no}.nepsetms.com.np/tms/me/trade-book-history"
        
        print(f"[DEBUG] Navigating to Tradebook History: {history_url}")
        self.driver.get(history_url)
        time.sleep(3)
        
        try:
            # Date Selection
            today = datetime.date.today()
            # Approximation: 30 days per month
            days_to_subtract = months * 30
            start_date = today - datetime.timedelta(days=days_to_subtract) 
            
            start_str = start_date.strftime("%Y-%m-%d")
            end_str = today.strftime("%Y-%m-%d")
            
            print(f"[DEBUG] Target Date Range: {start_str} to {end_str} ({months} months)")
            
            # Locate Date Inputs
            start_input = None
            end_input = None
            
            try:
                print("[DEBUG] Locating Date Inputs...")
                start_input = self.driver.find_element(By.CSS_SELECTOR, "input[name='dpFromDate']")
                end_input = self.driver.find_element(By.CSS_SELECTOR, "input[name='dpToDate']")
            except:
                # Fallback
                print("[DEBUG] Standard selectors failed. Trying fallback XPath...")
                inputs = self.driver.find_elements(By.XPATH, "//input[@placeholder='yyyy-mm-dd']")
                if len(inputs) >= 2:
                    start_input = inputs[0]
                    end_input = inputs[1]

            if start_input and end_input:
                print("[DEBUG] Setting date values...")
                js_set = "arguments[0].value = arguments[1]; arguments[0].dispatchEvent(new Event('change'));"
                self.driver.execute_script(js_set, start_input, start_str)
                self.driver.execute_script(js_set, end_input, end_str)
            else:
                 print("[DEBUG] WARNING: Could not find date inputs.")
            
            # Sets 100 items per page
            try:
                print("[DEBUG] Attempting to set 'Items Per Page' to 100...")
                page_size_select = self.driver.find_element(By.CSS_SELECTOR, "select[aria-label='items per page']")
                select = Select(page_size_select)
                select.select_by_value("100")
                print("[DEBUG] Success: Selected 100 items per page.")
                time.sleep(2)
            except Exception as e:
                print(f"[DEBUG] Could not set 100 items per page: {e}")

            # Click Search
            try:
                print("[DEBUG] Clicking Search Button...")
                search_btn = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Search')]")
                search_btn.click()
            except:
                try:
                    self.driver.find_element(By.CSS_SELECTOR, "button.btn-primary").click()
                except:
                    print("[DEBUG] Could not find Search button")
            
            time.sleep(2)
            
            # Scrape Data
            data = []
            
            # Get Headers
            headers = []
            try:
                print("[DEBUG] Extracting Headers...")
                header_row = self.driver.find_elements(By.CSS_SELECTOR, "table thead tr th") # Generic
                if not header_row:
                     header_row = self.driver.find_elements(By.CSS_SELECTOR, ".k-grid-header th") # Kendo
                headers = [h.text.strip() for h in header_row]
            except:
                pass
            
            if headers:
                data.append(headers)
                print(f"[DEBUG] Found Headers: {headers}")

            # Pagination Loop
            page_count = 1
            while True:
                print(f"[DEBUG] Scraping Page {page_count}...")
                # Get Rows
                try:
                    rows = self.driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
                    if not rows:
                        rows = self.driver.find_elements(By.CSS_SELECTOR, ".k-grid-content table tr") # Kendo
                    
                    print(f"[DEBUG] Found {len(rows)} rows on this page.")
                    for row in rows:
                        cols = row.find_elements(By.TAG_NAME, "td")
                        row_data = [c.text.strip() for c in cols]
                        if any(row_data):
                            data.append(row_data)
                except Exception as e:
                    print(f"[DEBUG] Error reading rows: {e}")

                # Next Page
                try:
                    next_btn = self.driver.find_element(By.CSS_SELECTOR, "a.k-pager-nav[title='Go to the next page']")
                    if "k-state-disabled" in next_btn.get_attribute("class"):
                        print("[DEBUG] Next button disabled. End of pagination.")
                        break
                    print("[DEBUG] moving to next page...")
                    next_btn.click()
                    page_count += 1
                    time.sleep(2)
                except:
                    print("[DEBUG] Next button not found or other pagination error.")
                    break
            
            return data

        except Exception as e:
            print(f"[DEBUG] Error extracting tradebook: {e}")
            return []

    def place_order(self, action, symbol, quantity, price, order_type="LMT", validity="DAY"):
        """
        Action: 'BUY' or 'SELL'
        """
        print(f"\n[DEBUG] Placing {action} Order: {symbol}, Qty: {quantity}, Price: {price}")
        
        tms_no = get_tms_number(self.driver.current_url)
        # Order Entry URL
        order_url = f"https://tms{tms_no}.nepsetms.com.np/tms/n/order/order-entry" # New TMS URL structure
        
        print(f"[DEBUG] Navigating to Order Entry: {order_url}")
        self.driver.get(order_url)
        time.sleep(2)
        
        try:
            # 1. Select Buy/Sell
            # Usually Tabs or Radio buttons
            if action.upper() == "BUY":
                 # Try finding Buy tab/button
                 try:
                     self.driver.find_element(By.XPATH, "//label[contains(text(), 'Buy')]").click()
                 except:
                     # Maybe a button class
                     self.driver.find_element(By.CLASS_NAME, "btn-buy").click()
            else:
                 try:
                     self.driver.find_element(By.XPATH, "//label[contains(text(), 'Sell')]").click()
                 except:
                     self.driver.find_element(By.CLASS_NAME, "btn-sell").click()
            
            time.sleep(0.5)

            # 2. Enter Symbol
            # Usually an input with autocomplete
            sym_input = self.driver.find_element(By.XPATH, "//input[contains(@placeholder, 'Symbol') or contains(@placeholder, 'Company')]")
            sym_input.clear()
            sym_input.send_keys(symbol)
            time.sleep(1)
            # Select from dropdown if needed (Simulation: Enter key)
            from selenium.webdriver.common.keys import Keys
            sym_input.send_keys(Keys.ENTER)
            time.sleep(1)

            # 3. Enter Quantity
            qty_input = self.driver.find_element(By.XPATH, "//input[contains(@placeholder, 'Qty') or @name='quantity']")
            qty_input.clear()
            qty_input.send_keys(str(quantity))

            # 4. Enter Price
            price_input = self.driver.find_element(By.XPATH, "//input[contains(@placeholder, 'Price') or @name='price']")
            price_input.clear()
            price_input.send_keys(str(price))

            # 5. Submit
            submit_btn = self.driver.find_element(By.XPATH, f"//button[contains(text(), '{action.capitalize()}') or @type='submit']")
            submit_btn.click()
            
            # 6. Confirm (Popup)
            time.sleep(1)
            try:
                confirm_btn = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Confirm') or contains(text(), 'Yes')]")
                confirm_btn.click()
                print("Order Submitted/Confirmed.")
                return {"status": "submitted", "details": f"{action} {symbol} {quantity} @ {price}"}
            except:
                print("Confirmation popup not found or auto-submitted.")
                return {"status": "unknown_submitted", "details": "Confirmation skipped"}

        except Exception as e:
            print(f"Error placing order: {e}")
            return {"status": "failed", "error": str(e)}

