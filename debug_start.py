print("DEBUG: Script started.")
import sys
print("DEBUG: Sys imported.")
import time
print("DEBUG: Time imported.")
try:
    import boto3
    print("DEBUG: Boto3 imported.")
except ImportError:
    print("DEBUG: Boto3 NOT found.")

try:
    from selenium import webdriver
    print("DEBUG: Selenium imported.")
    from webdriver_manager.chrome import ChromeDriverManager
    from selenium.webdriver.chrome.service import Service
    print("DEBUG: Webdriver Manager imported.")
except Exception as e:
    print(f"DEBUG: Error importing Selenium/Webdriver: {e}")

print("DEBUG: Attempting to launch Chrome...")
try:
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service)
    print("DEBUG: Chrome launched successfully.")
    driver.quit()
except Exception as e:
    print(f"DEBUG: Failed to launch Chrome: {e}")
print("DEBUG: Test complete.")
