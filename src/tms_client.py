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
                # Dispatch both input and change events with bubbling to ensure framework detects change
                js_set = """
                    arguments[0].value = arguments[1]; 
                    arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
                    arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
                    arguments[0].dispatchEvent(new Event('blur', { bubbles: true }));
                """
                self.driver.execute_script(js_set, start_input, start_str)
                self.driver.execute_script(js_set, end_input, end_str)
            else:
                 print("[DEBUG] WARNING: Could not find date inputs.")
            
            # Click Search
            try:
                print("[DEBUG] Clicking Search Button...")
                
                # Wait for button to become enabled (if disabled)
                time.sleep(2)
                
                # Check for Search button
                selectors = [
                    (By.XPATH, "//button[contains(., 'Search')]"),  # Dot matches text in children too
                    (By.CSS_SELECTOR, "button.export-btn"),          # Class found by inspection
                    (By.CSS_SELECTOR, "button.k-button-icontext"),
                    (By.XPATH, "//button[contains(@class, 'export-btn')]"),
                    (By.CSS_SELECTOR, "button[type='button']")
                ]
                
                search_btn = None
                for by, value in selectors:
                    try:
                        btn = self.driver.find_element(by, value)
                        if btn.is_displayed():
                            search_btn = btn
                            print(f"[DEBUG] Found Search button using {value}")
                            break
                    except:
                        continue
                
                if search_btn:
                    # Check if enabled
                    is_disabled = search_btn.get_attribute("disabled") or "k-state-disabled" in search_btn.get_attribute("class")
                    if is_disabled:
                        print("[DEBUG] Search button is DISABLED. Date inputs might not have triggered.")
                    
                    # Force click anyway using JS
                    self.driver.execute_script("arguments[0].click();", search_btn)
                    print("[DEBUG] Clicked Search button via JS")
                    search_clicked = True
                else:
                    search_clicked = False
                    print("[DEBUG] Could not find Search button with any selector")
                    
                    # Capture screenshot of the Trade Book page
                    try:
                        timestamp = int(time.time())
                        screenshot_name = f"search_btn_missing_{timestamp}.png"
                        self.driver.save_screenshot(screenshot_name)
                        print(f"[DEBUG] Saved debug screenshot: {screenshot_name}")
                    except:
                        pass
                        
            except Exception as e:
                print(f"[DEBUG] Error clicking search: {e}")
            
            time.sleep(5) # Wait for search results to load
            
            # Sets 100 items per page (AFTER Search)
            try:
                print("[DEBUG] Attempting to set 'Items Per Page' to 100...")
                page_size_select = self.driver.find_element(By.CSS_SELECTOR, "select[aria-label='items per page']")
                
                # Use JS to set value and trigger events
                js_select = """
                    arguments[0].value = '100';
                    arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
                """
                self.driver.execute_script(js_select, page_size_select)
                
                # Also try standard Select class as backup
                try:
                    select = Select(page_size_select)
                    select.select_by_value("100")
                except:
                    pass
                    
                print("[DEBUG] Success: Selected 100 items per page.")
                time.sleep(5) # Wait for grid to reload with 100 items
            except Exception as e:
                print(f"[DEBUG] Could not set 100 items per page: {e}")
            
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
                # Get Rows using BeautifulSoup (FASTER)
                try:
                    # Get table HTML directly
                    table_html = self.driver.execute_script("return document.querySelector('table').outerHTML;")
                    soup = BeautifulSoup(table_html, 'html.parser')
                    
                    rows = soup.select('tbody tr')
                    if not rows:
                         rows = soup.select('.k-grid-content table tr')
                    
                    print(f"[DEBUG] Found {len(rows)} rows on this page (via BS4).")
                    
                    current_page_data = []
                    for row in rows:
                        cols = row.find_all('td')
                        row_data = [c.get_text(strip=True) for c in cols]
                        
                        # Check for "No records available"
                        if len(row_data) == 1 and "No records" in row_data[0]:
                            print("[DEBUG] Found 'No records available'. Stopping scraping.")
                            return data
                            
                        if any(row_data):
                            current_page_data.append(row_data)
                    
                    if current_page_data:
                        data.extend(current_page_data)
                        print(f"[DEBUG] Extracted {len(current_page_data)} rows.")
                    else:
                        print("[DEBUG] No valid data found in rows.")
                        # If we found rows but they weren't valid data, maybe stop?
                        # But sometimes blank rows exist. Safer to rely on Next button or "No records" check.
                        
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

