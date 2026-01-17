import re
import io
import time
from PIL import Image
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from google import genai

def get_tms_number(url):
    """Extracts the TMS number from the URL."""
    match = re.search(r"tms(\d+)", url)
    if match:
        return match.group(1)
    return "58" # Default to 58 as per current common

def solve_captcha(driver, api_key):
    """Solves captcha: Priority 1 (DOM Value), Priority 2 (Gemini API)."""
    try:
        print("Attempting to solve captcha...")
        
        # Strategy 1: Check if value is already in the DOM
        try:
            captcha_input = driver.find_element(By.ID, "captchaEnter")
            hidden_value = captcha_input.get_attribute("value")
            if hidden_value and len(hidden_value) > 2:
                print(f"Strategy 1 Success: Found captcha value in DOM: '{hidden_value}'")
                return hidden_value
        except:
            pass

        # Strategy 2: Gemini API
        print("Strategy 1 failed (No value found). Proceeding to Strategy 2 (Gemini API)...")
        
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
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=[
                "What is the text in this captcha image? Return ONLY the alphanumeric text, no other words.", 
                image
            ]
        )
        
        captcha_text = response.text.strip()
        print(f"Gemini solved captcha: '{captcha_text}'")
        return captcha_text
        
    except Exception as e:
        print(f"Error solving captcha: {e}")
        return None

def perform_login(driver, username, password, api_key, login_url):
    """
    Performs the full login flow with retries.
    Returns True if login is successful, False otherwise.
    """
    try:
        if driver.current_url == "data:," or "nepsetms" not in driver.current_url:
             print(f"Navigating to {login_url}...")
             try:
                 driver.get(login_url)
             except Exception as nav_error:
                 if "ERR_NAME_NOT_RESOLVED" in str(nav_error) or "ERR_CONNECTION_REFUSED" in str(nav_error):
                     print(f"\nCRITICAL ERROR: Could not connect to {login_url}")
                     print("Please check your 'TMS Website No' configuration.")
                     print("Examples: 49, 58, 34, etc.")
                 raise nav_error
        
        wait = WebDriverWait(driver, 10)
        
        max_retries = 3
        
        for attempt in range(1, max_retries + 1):
            print(f"\n--- Login Attempt {attempt}/{max_retries} ---")
            
            try:
                # Check where we are
                if "dashboard" in driver.current_url:
                    print("Already logged in.")
                    return True
                
                # Fill Credentials
                try:
                    username_field = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input[placeholder="Client Code/ User Name"]')))
                    username_field.clear()
                    username_field.send_keys(username)
                    
                    password_field = driver.find_element(By.CSS_SELECTOR, '#password-field')
                    password_field.clear()
                    password_field.send_keys(password)
                except:
                    print("Could not find login fields (maybe reloading?). Refreshing...")
                    driver.refresh()
                    time.sleep(2)
                    continue

                # Solve Captcha
                captcha_text = solve_captcha(driver, api_key)
                
                if captcha_text:
                    try:
                        print(f"Filling Captcha: {captcha_text}")
                        captcha_input = driver.find_element(By.ID, "captchaEnter")
                        captcha_input.clear()
                        captcha_input.send_keys(captcha_text)
                        
                        # Click Login
                        print("Clicking Login...")
                        login_btn = driver.find_element(By.CSS_SELECTOR, '.login__button')
                        login_btn.click()
                        
                        # Wait for transition
                        time.sleep(5)
                        if "dashboard" in driver.current_url or "tms/me" in driver.current_url:
                            print("Login successful!")
                            return True
                        else:
                            print("Login failed (URL did not change). Captcha might be wrong.")
                            try:
                                # Check for error message
                                error_msg = driver.find_element(By.CSS_SELECTOR, ".toast-message").text
                                print(f"Error Message: {error_msg}")
                            except:
                                pass
                            driver.refresh()
                            time.sleep(2)
                    except Exception as e:
                         print(f"Error interacting with login form: {e}")
                         driver.refresh()
                         time.sleep(2)
                else:
                    print("Captcha solve failed.")
                    driver.refresh()
                    time.sleep(2)
                    
            except Exception as e:
                print(f"Error during login attempt {attempt}: {e}")
                driver.refresh()
                time.sleep(2)
                
        print("Max login attempts reached.")
        return False

    except Exception as e:
        print(f"Critical error in perform_login: {e}")
        return False
