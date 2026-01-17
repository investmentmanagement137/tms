import time
import io
import re
from google import genai
from PIL import Image
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def get_tms_number(url):
    """Extracts the TMS number from the URL."""
    match = re.search(r"tms(\d+)", url)
    if match:
        return match.group(1)
    return "40" # Default

def solve_captcha(driver, api_key):
    """Solves captcha using Gemini API."""
    import traceback
    
    try:
        print("\n" + "="*50)
        print("CAPTCHA SOLVING STARTED")
        print("="*50)
        
        # Step 1: Locate CAPTCHA image
        print("[Step 1/4] Locating CAPTCHA image element...")
        try:
            start_time = time.time()
            captcha_element = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'img.captcha-image-dimension'))
            )
            print(f"✓ CAPTCHA image found in {time.time() - start_time:.2f}s")
        except Exception as e:
            print(f"✗ FAILED: Could not find CAPTCHA image element")
            print(f"   Error: {str(e)}")
            return None
        
        # Step 2: Capture screenshot
        print("[Step 2/4] Capturing CAPTCHA screenshot...")
        try:
            start_time = time.time()
            screenshot = captcha_element.screenshot_as_png
            image = Image.open(io.BytesIO(screenshot))
            img_size = len(screenshot)
            print(f"✓ Screenshot captured ({img_size} bytes) in {time.time() - start_time:.2f}s")
            print(f"   Image dimensions: {image.size[0]}x{image.size[1]} pixels")
            # Optionally save for debugging
            # image.save("captcha_debug.png")
        except Exception as e:
            print(f"✗ FAILED: Could not capture screenshot")
            print(f"   Error: {str(e)}")
            return None
        
        # Step 3: Initialize Gemini client
        print("[Step 3/4] Initializing Gemini API client...")
        try:
            if not api_key or len(api_key) < 10:
                print(f"✗ FAILED: Invalid API key (length: {len(api_key) if api_key else 0})")
                return None
            
            start_time = time.time()
            client = genai.Client(api_key=api_key)
            print(f"✓ Client initialized in {time.time() - start_time:.2f}s")
            print(f"   API Key: {api_key[:10]}...{api_key[-4:]} (masked)")
        except Exception as e:
            print(f"✗ FAILED: Could not initialize Gemini client")
            print(f"   Error: {str(e)}")
            print(f"   Traceback: {traceback.format_exc()}")
            return None
        
        # Step 4: Send to Gemini API
        print("[Step 4/4] Sending request to Gemini API...")
        print(f"   Model: gemini-2.0-flash-exp")
        try:
            start_time = time.time()
            response = client.models.generate_content(
                model="gemini-2.0-flash-exp",
                contents=[
                    "What is the text in this captcha image? Return ONLY the alphanumeric text, no other words.", 
                    image
                ]
            )
            api_time = time.time() - start_time
            print(f"✓ API response received in {api_time:.2f}s")
            
            # Log response metadata if available
            if hasattr(response, 'usage_metadata'):
                print(f"   Usage: {response.usage_metadata}")
            
        except Exception as e:
            print(f"✗ FAILED: Gemini API request failed")
            print(f"   Error: {str(e)}")
            print(f"   Error type: {type(e).__name__}")
            print(f"   Traceback: {traceback.format_exc()}")
            return None
        
        # Step 5: Extract and validate result
        print("[Final Step] Extracting CAPTCHA text from response...")
        try:
            captcha_text = response.text.strip()
            
            # Validate result
            if not captcha_text:
                print(f"✗ FAILED: Empty response from Gemini")
                print(f"   Raw response: {response}")
                return None
            
            # Clean any extra characters
            cleaned_text = re.sub(r'[^a-zA-Z0-9]', '', captcha_text)
            
            print(f"✓ CAPTCHA solved successfully!")
            print(f"   Raw response: '{captcha_text}'")
            print(f"   Cleaned text: '{cleaned_text}'")
            print(f"   Length: {len(cleaned_text)} characters")
            
            if len(cleaned_text) < 4 or len(cleaned_text) > 8:
                print(f"⚠ WARNING: Unusual CAPTCHA length (expected 4-6 chars)")
            
            print("="*50 + "\n")
            return cleaned_text
            
        except Exception as e:
            print(f"✗ FAILED: Could not extract text from response")
            print(f"   Error: {str(e)}")
            print(f"   Response object: {response}")
            return None
        
    except Exception as e:
        print(f"\n✗ CRITICAL ERROR in solve_captcha:")
        print(f"   {str(e)}")
        print(f"   Traceback: {traceback.format_exc()}")
        print("="*50 + "\n")
        return None

def perform_login(driver, username, password, api_key, login_url):
    """
    Performs the full login flow with retries.
    Returns True if login is successful, False otherwise.
    """
    try:
        # Navigate to Login Page
        # We handle dynamic TMS number if the provided URL is generic, 
        # but usually the driver is already navigating or we navigate here.
        if driver.current_url == "data:," or "neptse" not in driver.current_url:
             print(f"Navigating to {login_url}...")
             driver.get(login_url)
        
        # Wait for page to fully load
        print("Waiting for page to load...")
        time.sleep(3)  # Initial wait for JavaScript to execute
        
        wait = WebDriverWait(driver, 20)  # Increased from 10 to 20 seconds
        
        # LOGIN RETRY LOOP
        max_retries = 3
        
        for attempt in range(1, max_retries + 1):
            print(f"\n--- Login Attempt {attempt}/{max_retries} ---")
            print(f"Current URL: {driver.current_url}")
            
            try:
                # Check where we are
                if "dashboard" in driver.current_url:
                    print("Already logged in.")
                    return True
                
                # Fill Credentials
                try:
                    print("Looking for username field...")
                    username_field = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input[placeholder="Client Code/ User Name"]')))
                    print("✓ Username field found")
                    username_field.clear()
                    username_field.send_keys(username)
                    
                    print("Looking for password field...")
                    password_field = driver.find_element(By.CSS_SELECTOR, '#password-field')
                    print("✓ Password field found")
                    password_field.clear()
                    password_field.send_keys(password)
                    
                except Exception as e:
                    print(f"✗ Could not find login fields")
                    print(f"   Error: {str(e)}")
                    print(f"   Page title: {driver.title}")
                    
                    # Debug: Print what's on the page
                    try:
                        body_text = driver.find_element(By.TAG_NAME, "body").text[:500]
                        print(f"   Page content preview: {body_text}")
                    except:
                        pass
                    
                    # Try alternate selectors
                    print("   Trying alternate selectors...")
                    try:
                        all_inputs = driver.find_elements(By.TAG_NAME, "input")
                        print(f"   Found {len(all_inputs)} input elements total")
                        for i, inp in enumerate(all_inputs[:5]):
                            print(f"   Input {i}: type={inp.get_attribute('type')}, placeholder={inp.get_attribute('placeholder')}")
                    except:
                        pass
                    
                    print("Refreshing page...")
                    driver.refresh()
                    time.sleep(5)  # Longer wait after refresh
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
                        time.sleep(3)
                        if "dashboard" in driver.current_url:
                            print("Login successful!")
                            return True
                        else:
                            print("Login failed (URL did not change). Captcha might be wrong.")
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
