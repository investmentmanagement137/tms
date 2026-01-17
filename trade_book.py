print("DEBUG: Importing standard libraries...")
import os
import time
import csv
import datetime
import boto3
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import tms_utils 

print("DEBUG: All imports done.")

# --- CONFIGURATION ---
# These values MUST be set via environment variables or Apify Actor inputs
# DO NOT hardcode credentials here!

USERNAME = os.environ.get("TMS_USERNAME", "")
PASSWORD = os.environ.get("TMS_PASSWORD", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
HEADLESS = os.environ.get("HEADLESS", "false").lower() == "true"

LOGIN_URL = "https://tms43.nepsetms.com.np/login"

# --- SUPABASE S3 CONFIGURATION ---
SUPABASE_ENDPOINT = os.environ.get("SUPABASE_ENDPOINT", "")
SUPABASE_REGION = os.environ.get("SUPABASE_REGION", "ap-southeast-1")
SUPABASE_ACCESS_KEY = os.environ.get("SUPABASE_ACCESS_KEY", "")
SUPABASE_SECRET_KEY = os.environ.get("SUPABASE_SECRET_KEY", "")
SUPABASE_BUCKET_NAME = os.environ.get("SUPABASE_BUCKET_NAME", "investment_management")

def upload_to_supabase(file_path):
    print("\n" + "="*30)
    print("STARTING S3 UPLOAD")
    print("="*30)
    
    try:
        session = boto3.session.Session()
        s3 = session.client(
            's3',
            region_name=SUPABASE_REGION,
            endpoint_url=SUPABASE_ENDPOINT,
            aws_access_key_id=SUPABASE_ACCESS_KEY,
            aws_secret_access_key=SUPABASE_SECRET_KEY
        )
        
        target_bucket = SUPABASE_BUCKET_NAME
        print(f"Uploading context to bucket: {target_bucket}")
        
        # Upload
        print(f"Uploading {file_path}...")
        with open(file_path, "rb") as f:
            s3.upload_fileobj(f, target_bucket, file_path)
            
        print(f"FAILED? No, Success! File '{file_path}' uploaded successfully.")
        
    except Exception as e:
        print(f"Error uploading to Supabase: {e}")

def scrape_trade_book(driver, days=365):
    print("\n" + "="*30)
    print("STARTING TRADE BOOK SCRAPING")
    print("="*30)
    
    tms_no = tms_utils.get_tms_number(driver.current_url)
    history_url = f"https://tms{tms_no}.nepsetms.com.np/tms/me/trade-book-history"
    
    # --- MARKET HOURS CHECK ---
    now = datetime.datetime.now()
    current_time = now.time()
    market_open = datetime.time(10, 0)
    market_close = datetime.time(15, 5)
    
    print(f"Current Time: {current_time.strftime('%H:%M')}")
    if market_open <= current_time <= market_close:
        print("\n" + "!"*50)
        print("WARNING: Market is likely OPEN.")
        print("Trade Book History is usually accessible ONLY:")
        print("  - Before 10:00 AM")
        print("  - After 3:05 PM")
        print("You are running this script during market hours.")
        print("The website might block access or show no data.")
        print("!"*50 + "\n")
    else:
        print("Time check passed: Outside market hours.")
    # --------------------------

    print(f"Navigating to {history_url}...")
    driver.get(history_url)
    time.sleep(3) # Wait for load
    
    try:
        # Date Selection
        today = datetime.date.today()
        start_date = today - datetime.timedelta(days=days)
        
        start_str = start_date.strftime("%Y-%m-%d")
        end_str = today.strftime("%Y-%m-%d")
        
        print(f"Target Date Range: {start_str} to {end_str}")
        
        # Strategy: Precise targeting based on User Feedback
        print("Looking for date inputs (Strategy: Placeholders & Labels)...")
        found_inputs = False
        start_input = None
        end_input = None
        
        try:
            # KENDO UI GRID - Date inputs have specific names
            print("Looking for Kendo UI date inputs (dpFromDate, dpToDate)...")
            
            start_input = None
            end_input = None
            
            # Try specific name selectors first (most reliable)
            try:
                start_input = driver.find_element(By.CSS_SELECTOR, "input[name='dpFromDate']")
                end_input = driver.find_element(By.CSS_SELECTOR, "input[name='dpToDate']")
                print("Found date inputs by name attribute!")
            except:
                pass
            
            # Fallback to placeholder
            if not start_input:
                print("Checking for inputs with placeholder 'yyyy-mm-dd'...")
                placehold_inputs = driver.find_elements(By.XPATH, "//input[@placeholder='yyyy-mm-dd']")
                placehold_inputs = [i for i in placehold_inputs if i.is_displayed()]
                
                if len(placehold_inputs) >= 2:
                    print(f"Found {len(placehold_inputs)} visible inputs with date placeholder.")
                    start_input = placehold_inputs[0]
                    end_input = placehold_inputs[1]

            if start_input and end_input:
                try:
                    p1 = start_input.get_attribute('placeholder')
                    p2 = end_input.get_attribute('placeholder')
                    print(f"Targeting inputs: P1='{p1}', P2='{p2}'")
                except:
                    pass
                
                js_set_value = """
                arguments[0].value = arguments[1];
                arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
                arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
                arguments[0].dispatchEvent(new Event('blur', { bubbles: true }));
                """
                
                print(f"Setting Start Date to {start_str}...")
                driver.execute_script(js_set_value, start_input, start_str)
                time.sleep(0.5)
                
                print(f"Setting End Date to {end_str}...")
                driver.execute_script(js_set_value, end_input, end_str)
                time.sleep(0.5)
                
                # VERIFY VALUES
                v1 = start_input.get_attribute('value')
                v2 = end_input.get_attribute('value')
                print(f"VERIFICATION: Start Input Value='{v1}', End Input Value='{v2}'")
                if v1 != start_str or v2 != end_str:
                     print("WARNING: Date setting might have failed! Values do not match target.")
                
                found_inputs = True
            else:
                 print("ERROR: Could not locate 2 suitable date inputs.")

        except Exception as e:
            print(f"Error locating/setting dates: {e}")

        # Search Button Logic - REFINED
        print("Looking for Search button...")
        try:
             search_btn = None
             # Try finding ANY button with "Search" text
             buttons = driver.find_elements(By.TAG_NAME, "button")
             for btn in buttons:
                 if "search" in btn.text.lower():
                     search_btn = btn
                     print("Found button with text 'Search'")
                     break
             
             if not search_btn:
                 try:
                     search_btn = driver.find_element(By.CSS_SELECTOR, "button.btn-primary")
                     print("Found button with class 'btn-primary'")
                 except:
                     pass

             if search_btn:
                 print("Clicking Search...")
                 search_btn.click()
                 time.sleep(2)
                 try:
                     WebDriverWait(driver, 10).until(
                         EC.presence_of_element_located((By.CSS_SELECTOR, "table tbody tr"))
                     )
                     print("Table data loaded (rows detected).")
                 except:
                     print("Warning: Timeout waiting for table rows.")
                     # Debug: print what IS there
                     try:
                         tbl = driver.find_element(By.TAG_NAME, "table")
                         print(f"DEBUG: Table found. Text content preview: {tbl.text[:200]}")
                     except:
                         print("DEBUG: No table found at all.")
             else:
                print("Could not find Search button.")
        except Exception as e:
            print(f"Error clicking search: {e}")

        # SELECT 100 ITEMS PER PAGE for faster scraping
        print("Attempting to set 100 items per page...")
        try:
            # The page size is a standard HTML select element with aria-label
            from selenium.webdriver.support.ui import Select
            
            page_size_select = driver.find_element(By.CSS_SELECTOR, "select[aria-label='items per page']")
            select = Select(page_size_select)
            select.select_by_value("100")
            print("Selected 100 items per page!")
            time.sleep(2)  # Wait for table to reload with more items
        except Exception as e:
            print(f"Could not set 100 items per page (keeping default): {e}")

        # Scrape Table
        filename = f"trade-book-history-{today}.csv"
        print(f"Scraping data to {filename}...")
        
        # Try to get pagination info
        total_pages = 1
        total_records = "unknown"
        try:
            # Look for pagination info text like "Showing 1 to 10 of 500 entries"
            page_info = driver.find_elements(By.XPATH, "//*[contains(text(), 'Showing') and contains(text(), 'of')]")
            if page_info:
                info_text = page_info[0].text
                print(f"PAGINATION INFO: {info_text}")
                # Try to extract total records
                import re
                match = re.search(r'of (\d+)', info_text)
                if match:
                    total_records = match.group(1)
            
            # Look for page buttons to count pages
            page_btns = driver.find_elements(By.CSS_SELECTOR, ".pagination li, .pagination button, [class*='page'] button")
            if page_btns:
                # Filter to find the last numbered page
                for btn in reversed(page_btns):
                    txt = btn.text.strip()
                    if txt.isdigit():
                        total_pages = int(txt)
                        break
            print(f"ESTIMATED TOTAL PAGES: {total_pages}, TOTAL RECORDS: {total_records}")
        except Exception as e:
            print(f"Could not determine pagination info: {e}")
        
        total_rows_extracted = 0
        
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            header_written = False
            
            page_num = 1
            while True:
                print(f"\n{'='*40}")
                print(f"PROCESSING PAGE {page_num} of ~{total_pages}")
                print(f"{'='*40}")
                
                # KENDO UI GRID - Headers and Data are in SEPARATE tables!
                try:
                    # Get headers from .k-grid-header table (only on first page)
                    if not header_written:
                        try:
                            header_table = driver.find_element(By.CSS_SELECTOR, ".k-grid-header table")
                            header_cells = header_table.find_elements(By.TAG_NAME, "th")
                            headers = [th.text.strip() for th in header_cells]
                            if headers and any(h for h in headers):
                                print(f"DEBUG: Headers from Kendo header table: {headers}")
                                writer.writerow(headers)
                                header_written = True
                            else:
                                print("WARNING: Header table found but no text in cells.")
                        except Exception as e:
                            print(f"Could not find Kendo header table: {e}")
                    
                    # Get data from .k-grid-content table
                    try:
                        data_table = driver.find_element(By.CSS_SELECTOR, ".k-grid-content table")
                        rows = data_table.find_elements(By.TAG_NAME, "tr")
                        print(f"DEBUG: Found {len(rows)} data rows in Kendo content table.")
                    except:
                        # Fallback to generic table
                        print("Kendo content table not found, trying generic table...")
                        tables = driver.find_elements(By.TAG_NAME, "table")
                        if tables:
                            data_table = tables[-1]  # Usually last table is data
                            rows = data_table.find_elements(By.TAG_NAME, "tr")
                            print(f"DEBUG: Found {len(rows)} rows in fallback table.")
                        else:
                            rows = []
                            print("ERROR: No tables found!")
                    
                    valid_rows = 0
                    for i, row in enumerate(rows):
                        # Debug first few rows of each page
                        if i < 2:
                            print(f"DEBUG Row {i}: '{row.text.strip()[:100]}'")

                        cols = row.find_elements(By.TAG_NAME, "td")
                        if not cols:
                            continue  # Skip non-data rows
                        
                        # Verify it's not a "No matching records found" row
                        row_text = row.text.lower()
                        if "no matching records" in row_text or "no data" in row_text or "no records" in row_text:
                            print("No data found in table (text match).")
                            break
                            
                        data = [col.text.strip() for col in cols]
                        # Only write if row has actual data
                        if any(d for d in data):
                            writer.writerow(data)
                            valid_rows += 1
                    
                    total_rows_extracted += valid_rows
                    print(f"PAGE {page_num} SUMMARY: Extracted {valid_rows} rows. Running total: {total_rows_extracted}")
                    
                    if valid_rows == 0 and page_num == 1:
                        print("WARNING: No valid data rows extracted on first page!")
                        try:
                            body_text = driver.find_element(By.TAG_NAME, "body").text[:500]
                            print(f"PAGE BODY PREVIEW:\n{body_text}")
                        except:
                            pass
                        
                except Exception as e:
                    print(f"Error reading table on page {page_num}: {e}")
                
                # KENDO UI PAGINATION
                try:
                    # Kendo uses .k-pager-nav for next button
                    next_element = None
                    
                    # Try Kendo-specific selector first
                    try:
                        kendo_next = driver.find_element(By.CSS_SELECTOR, "a.k-pager-nav[title='Go to the next page']")
                        # Check if not disabled
                        if "k-state-disabled" not in (kendo_next.get_attribute("class") or ""):
                            next_element = kendo_next
                            print("Found Kendo Next button")
                    except:
                        pass
                    
                    # Fallback to generic Next button
                    if not next_element:
                        next_btns = driver.find_elements(By.XPATH, "//a[contains(text(), 'Next') or contains(text(), '›')]")
                        if next_btns:
                            next_element = next_btns[0]
                            print("Found generic Next link")
                    
                    if next_element:
                        classes = next_element.get_attribute("class") or ""
                        is_disabled = "disabled" in classes or "k-state-disabled" in classes
                        if not is_disabled:
                            print("Clicking Next...")
                            next_element.click()
                            time.sleep(2)  # Wait for AJAX load
                            page_num += 1
                        else:
                            print("Next button is disabled. End of pages.")
                            break
                    else:
                        print("No Next button found. End of pages.")
                        break
                except Exception as e:
                    print(f"Pagination error: {e}")
                    break
        
        print(f"\n{'='*50}")
        print(f"SCRAPING COMPLETE!")
        print(f"Total pages processed: {page_num}")
        print(f"Total rows extracted: {total_rows_extracted}")
        print(f"Output file: {filename}")
        print(f"{'='*50}\n")
        
        # If no rows extracted, save page HTML for debugging
        if total_rows_extracted == 0:
            debug_html_file = f"debug-page-{today}.html"
            try:
                with open(debug_html_file, 'w', encoding='utf-8') as f:
                    f.write(driver.page_source)
                print(f"DEBUG: No data extracted. Page HTML saved to: {debug_html_file}")
                print("Please share this file for analysis.")
            except Exception as e:
                print(f"Could not save debug HTML: {e}")
        
        print(f"Scraping complete. Saved to {filename}.")
        return filename
        
    except Exception as e:
        print(f"Error during scraping: {e}")
        return None

def main():
    print("DEBUG: Entered main function.")
    # Setup Chrome Options
    chrome_options = Options()
    
    # Add realistic User-Agent
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36')
    
    if HEADLESS:
        chrome_options.add_argument("--headless=new")
        # CI/CD environment optimizations
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-software-rasterizer")
        chrome_options.add_argument("--window-size=1920,1080")
    else:
        chrome_options.add_argument("--start-maximized")
    
    # Anti-detection measures
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    
    # Initialize WebDriver using webdriver-manager
    print("Launching Chrome...")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    try:
        # --- LOGIN USING UTILS ---
        print("Attempting login via tms_utils...")
        success = tms_utils.perform_login(driver, USERNAME, PASSWORD, GEMINI_API_KEY, LOGIN_URL)
        
        if success:
             # PROCEED TO SCRAPING
            csv_file = scrape_trade_book(driver)
            
            # UPLOAD TO S3
            if csv_file:
                upload_to_supabase(csv_file)
        else:
            print("Login failed after max attempts. Exiting.")

        print("\n" + "="*50)
        print("Script finished successfully.")
        print("="*50 + "\n")
        
        # Only keep browser open in interactive mode (not headless)
        if not HEADLESS:
            print("Browser remains open. Press Ctrl+C to exit.")
            try:
                while True:
                    time.sleep(1)
                    driver.title  # Check if browser is still open
            except:
                print("Browser closed.")
            
    except KeyboardInterrupt:
        print("\nScript stopped by user.")
    except Exception as e:
        print(f"\nAn error occurred: {e}")
    finally:
        # Ask if user wants to close
        try:
            if driver.service.is_connectable():
                input("\nPress Enter to close browser and exit script...")
                driver.quit()
        except:
            pass

if __name__ == "__main__":
    main()
