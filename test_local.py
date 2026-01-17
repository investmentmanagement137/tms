"""
LOCAL TEST SCRIPT - Run this to validate the TMS login logic locally

This script tests the core login functionality WITHOUT Apify dependencies.
Run with: python test_local.py
"""

import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from utils import perform_login

# Configuration
TMS_URL = "https://tms43.nepsetms.com.np/login"
USERNAME = "Bp480035a"  # Replace with your username
PASSWORD = input("Enter TMS Password: ")  # For security
GEMINI_KEY = input("Enter Gemini API Key: ")

print("\n" + "="*50)
print("LOCAL TMS LOGIN TEST")
print("="*50)

# Setup Chrome (NON-headless for visual debugging)
chrome_options = Options()

# Anti-detection (from working script)
chrome_options.add_argument("--disable-blink-features=AutomationControlled")
chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
chrome_options.add_experimental_option('useAutomationExtension', False)

# Visible mode for debugging
# chrome_options.add_argument("--headless")  # Uncomment to test headless

chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--window-size=1920,1080")

print("Launching Chrome...")
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=chrome_options)

try:
    print(f"\nAttempting login to: {TMS_URL}")
    success = perform_login(driver, USERNAME, PASSWORD, GEMINI_KEY, TMS_URL)
    
    if success:
        print("\n" + "="*50)
        print("✓ LOGIN SUCCESSFUL!")
        print("="*50)
        print(f"Current URL: {driver.current_url}")
        print(f"Page Title: {driver.title}")
        
        input("\nPress Enter to close browser...")
    else:
        print("\n" + "="*50)
        print("✗ LOGIN FAILED")
        print("="*50)
        print(f"Final URL: {driver.current_url}")
        print(f"Page Title: {driver.title}")
        
        # Save page source
        with open("local_test_page.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        print("Page source saved to: local_test_page.html")
        
        input("\nPress Enter to close browser...")
        
finally:
    driver.quit()
    print("Browser closed.")
