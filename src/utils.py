import re
import io
import time
from PIL import Image
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import google.generativeai as genai

def solve_captcha(driver, api_key):
    """Solves captcha using Gemini API."""
    try:
        print("Attempting to solve captcha using Gemini API...")
        
        print("Locating captcha image...")
        try:
            captcha_element = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'img.captcha-image-dimension'))
            )
        except:
            print("Could not find captcha image element.")
            return None
        
        print("Capturing captcha screenshot...")
        screenshot = captcha_element.screenshot_as_png
        image = Image.open(io.BytesIO(screenshot))
        
        print("Sending to Gemini API...")
        print("[DEBUG] Sending to Gemini API...")
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        response = model.generate_content([
            "What is the text in this captcha image? Return ONLY the alphanumeric text, no other words.", 
            image
        ])
        
        captcha_text = response.text.strip()
        print(f"Gemini solved captcha: '{captcha_text}'")
        return captcha_text
        
    except Exception as e:
        print(f"Error solving captcha: {e}")
        return None

def perform_login(driver, username, password, api_key, tms_url):
    """
    Performs login to TMS using the provided full URL.
    Returns True if login is successful, False otherwise.
    """
    # Ensure URL ends with /login for the initial navigation
    if not tms_url.endswith("/login"):
        login_url = f"{tms_url.rstrip('/')}/login"
    else:
        login_url = tms_url
        
    print(f"Navigating to Login Page: {login_url}")
    
    max_retries = 3
    for attempt in range(1, max_retries + 1):
        print(f"\n--- Login Attempt {attempt}/{max_retries} ---")
        try:
             driver.get(login_url)
             print(f"[DEBUG] Navigation successful. Page title: {driver.title}")
             
             # Wait for page load
             time.sleep(3)
             
             # Check if already logged in
             if "dashboard" in driver.current_url:
                 print("[DEBUG] Already logged in (dashboard found).")
                 return True

             # Locate fields
             print("[DEBUG] Locating username field...")
             wait = WebDriverWait(driver, 10)
             try:
                 username_field = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input[placeholder="Client Code/ User Name"], input[name="username"]')))
                 username_field.clear()
                 username_field.send_keys(username)
                 
                 password_field = driver.find_element(By.CSS_SELECTOR, '#password-field, input[name="password"]')
                 password_field.clear()
                 password_field.send_keys(password)
             except Exception as e:
                 print(f"[DEBUG] Could not find fields: {e}. Refreshing...")
                 driver.refresh()
                 continue

             # Solve Captcha
             captcha_text = solve_captcha(driver, api_key)
             if captcha_text:
                 print(f"[DEBUG] Filling Captcha with: '{captcha_text}'")
                 captcha_input = driver.find_element(By.ID, "captchaEnter")
                 captcha_input.clear()
                 captcha_input.send_keys(captcha_text)
                 
                 # Click Login
                 print("[DEBUG] Clicking Login Button...")
                 login_btn = driver.find_element(By.CSS_SELECTOR, '.login__button')
                 driver.execute_script("arguments[0].click();", login_btn)
                 
                 # Wait for transition
                 print("[DEBUG] Waiting for login transition...")
                 time.sleep(10)
                 
                 if "dashboard" in driver.current_url or "tms/me" in driver.current_url:
                     print("[DEBUG] Login SUCCESS!")
                     return True
                 else:
                     print("[DEBUG] Login failed (URL did not change). Checking for errors...")
                     try:
                         error_msg = driver.find_element(By.CSS_SELECTOR, ".toast-message").text
                         print(f"[DEBUG] Website Error: {error_msg}")
                     except:
                         pass
             else:
                 print("[DEBUG] Captcha failed. Retrying...")

        except Exception as e:
            print(f"[DEBUG] Error during login attempt: {e}")
            
        driver.refresh()
        time.sleep(2)
        
    return False


