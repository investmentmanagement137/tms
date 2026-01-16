print("DEBUG: Importing standard libraries...")
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import tms_utils 

# --- CONFIGURATION ---
USERNAME = "Bp480035" 
PASSWORD = "E3!xdpZ11@@" 
GEMINI_API_KEY = "AIzaSyC184Uw7BV4-QjCCbSddnIt1i9wn-K2Dbw" 
HEADLESS = False  # Set to True for headless mode, False for visible browser
LOGIN_URL = "https://tms43.nepsetms.com.np/login"

def main():
    print("DEBUG: Entered main function (Login Only).")
    # Setup Chrome Options
    chrome_options = Options()
    if HEADLESS:
        chrome_options.add_argument("--headless") 
    chrome_options.add_argument("--start-maximized")
    
    # Initialize WebDriver
    print("Launching Chrome...")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    try:
        # --- LOGIN USING UTILS ---
        print("Attempting login via tms_utils...")
        success = tms_utils.perform_login(driver, USERNAME, PASSWORD, GEMINI_API_KEY, LOGIN_URL)
        
        if success:
            print("\n" + "="*50)
            print("LOGIN SUCCESSFUL.")
            print("Browser will remain open for you to use manually.")
            print("="*50 + "\n")
        else:
            print("Login failed after max attempts.")

        # Keep waiting indefinitely for manual use
        while True:
            time.sleep(1)
            try:
                driver.title
            except:
                break
            
    except KeyboardInterrupt:
        print("\nScript stopped by user.")
    except Exception as e:
        print(f"\nAn error occurred: {e}")
    finally:
        try:
            if driver.service.is_connectable():
                input("\nPress Enter to close browser and exit script...")
                driver.quit()
        except:
            pass

if __name__ == "__main__":
    main()
