import time
import csv
import datetime
import os
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support import expected_conditions as EC
from .utils import get_tms_number

class TMSClient:
    def __init__(self, driver):
        self.driver = driver
        self.base_url = "https://tms{}.nepsetms.com.np" 

    def get_market_status(self):
        # Optional: Check if market is open
        pass

    def extract_tradebook(self):
        print("\n" + "="*30)
        print("STARTING TRADE BOOK SCRAPING")
        print("="*30)
        
        tms_no = get_tms_number(self.driver.current_url)
        history_url = f"https://tms{tms_no}.nepsetms.com.np/tms/me/trade-book-history"
        
        print(f"Navigating to {history_url}...")
        self.driver.get(history_url)
        time.sleep(3)
        
        try:
            # Date Selection
            today = datetime.date.today()
            start_date = today - datetime.timedelta(days=365) # Default 1 year
            
            start_str = start_date.strftime("%Y-%m-%d")
            end_str = today.strftime("%Y-%m-%d")
            
            print(f"Target Date Range: {start_str} to {end_str}")
            
            # Locate Date Inputs
            start_input = None
            end_input = None
            
            try:
                start_input = self.driver.find_element(By.CSS_SELECTOR, "input[name='dpFromDate']")
                end_input = self.driver.find_element(By.CSS_SELECTOR, "input[name='dpToDate']")
            except:
                # Fallback
                inputs = self.driver.find_elements(By.XPATH, "//input[@placeholder='yyyy-mm-dd']")
                if len(inputs) >= 2:
                    start_input = inputs[0]
                    end_input = inputs[1]

            if start_input and end_input:
                js_set = "arguments[0].value = arguments[1]; arguments[0].dispatchEvent(new Event('change'));"
                self.driver.execute_script(js_set, start_input, start_str)
                self.driver.execute_script(js_set, end_input, end_str)
            
            # Sets 100 items per page
            try:
                page_size_select = self.driver.find_element(By.CSS_SELECTOR, "select[aria-label='items per page']")
                select = Select(page_size_select)
                select.select_by_value("100")
                print("Selected 100 items per page.")
                time.sleep(2)
            except Exception as e:
                print(f"Could not set 100 items per page: {e}")

            # Click Search
            try:
                search_btn = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Search')]")
                search_btn.click()
            except:
                try:
                    self.driver.find_element(By.CSS_SELECTOR, "button.btn-primary").click()
                except:
                    print("Could not find Search button")
            
            time.sleep(2)
            
            # Scrape Data
            data = []
            
            # Get Headers
            headers = []
            try:
                header_row = self.driver.find_elements(By.CSS_SELECTOR, "table thead tr th") # Generic
                if not header_row:
                     header_row = self.driver.find_elements(By.CSS_SELECTOR, ".k-grid-header th") # Kendo
                headers = [h.text.strip() for h in header_row]
            except:
                pass
            
            if headers:
                data.append(headers)

            # Pagination Loop
            while True:
                # Get Rows
                try:
                    rows = self.driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
                    if not rows:
                        rows = self.driver.find_elements(By.CSS_SELECTOR, ".k-grid-content table tr") # Kendo
                    
                    for row in rows:
                        cols = row.find_elements(By.TAG_NAME, "td")
                        row_data = [c.text.strip() for c in cols]
                        if any(row_data):
                            data.append(row_data)
                except Exception as e:
                    print(f"Error reading rows: {e}")

                # Next Page
                try:
                    next_btn = self.driver.find_element(By.CSS_SELECTOR, "a.k-pager-nav[title='Go to the next page']")
                    if "k-state-disabled" in next_btn.get_attribute("class"):
                        break
                    next_btn.click()
                    time.sleep(2)
                except:
                    break
            
            return data

        except Exception as e:
            print(f"Error extracting tradebook: {e}")
            return []

    def place_order(self, action, symbol, quantity, price, order_type="LMT", validity="DAY"):
        """
        Action: 'BUY' or 'SELL'
        """
        print(f"\nPlacing {action} Order: {symbol}, Qty: {quantity}, Price: {price}")
        
        tms_no = get_tms_number(self.driver.current_url)
        # Order Entry URL
        order_url = f"https://tms{tms_no}.nepsetms.com.np/tms/n/order/order-entry" # New TMS URL structure
        
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

