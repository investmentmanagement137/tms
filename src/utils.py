import re
import io
import time
import asyncio
from PIL import Image
import google.generativeai as genai

async def solve_captcha(page, api_key):
    """Solves captcha using Gemini API (Async Playwright)."""
    try:
        print("Attempting to solve captcha using Gemini API...")
        
        print("Locating captcha image...")
        try:
            # Wait for captcha image
            captcha_loc = page.locator('img.captcha-image-dimension')
            await captcha_loc.wait_for(state='visible', timeout=5000)
        except:
            print("Could not find captcha image element.")
            return None
        
        print("Capturing captcha screenshot...")
        # Screenshot directly to memory bytes?
        # Playwright screenshot returns bytes
        screenshot_bytes = await captcha_loc.screenshot()
        image = Image.open(io.BytesIO(screenshot_bytes))
        
        print("Sending to Gemini API...")
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        # We need to run sync Gemini call in executor if we want strict async, 
        # but for this script blocking briefly is fine or we can use to_thread.
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, lambda: model.generate_content([
            "What is the text in this captcha image? Return ONLY the alphanumeric text, no other words.", 
            image
        ]))
        
        captcha_text = response.text.strip()
        print(f"Gemini solved captcha: '{captcha_text}'")
        return captcha_text
        
    except Exception as e:
        print(f"Error solving captcha: {e}")
        return None

async def perform_login(page, username, password, api_key, tms_url):
    """
    Performs login to TMS (Async Playwright).
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
             await page.goto(login_url, wait_until='networkidle')
             title = await page.title()
             print(f"[DEBUG] Navigation successful. Page title: {title}")
             
             # Check if already logged in (redirected to dashboard)
             if "dashboard" in page.url or "tms/me" in page.url:
                 print("[DEBUG] Already logged in (dashboard found).")
                 return True

             # Locate fields
             print("[DEBUG] Locating username field...")
             try:
                 # Check for username input
                 username_loc = page.locator('input[placeholder="Client Code/ User Name"], input[name="username"]').first
                 await username_loc.wait_for(state='visible', timeout=10000)
                 await username_loc.fill(username)
                 
                 password_loc = page.locator('#password-field, input[name="password"]').first
                 await password_loc.fill(password)
                 
             except Exception as e:
                 print(f"[DEBUG] Could not find fields: {e}. Refreshing...")
                 await page.reload()
                 continue

             # Solve Captcha
             captcha_text = await solve_captcha(page, api_key)
             if captcha_text:
                 print(f"[DEBUG] Filling Captcha with: '{captcha_text}'")
                 await page.fill("#captchaEnter", captcha_text)
                 
                 # Click Login
                 print("[DEBUG] Clicking Login Button...")
                 login_btn = page.locator('.login__button').first
                 await login_btn.click()
                 
                 # Wait for transition (dashboard or error check)
                 print("[DEBUG] Waiting for login transition...")
                 try:
                     # Wait for URL change OR error toast
                     # We wait up to 10s
                     await page.wait_for_timeout(5000) 
                     
                     if "dashboard" in page.url or "tms/me" in page.url:
                         print("[DEBUG] Login SUCCESS!")
                         return True
                     else:
                         print("[DEBUG] Checking for login errors...")
                         # Check for toast
                         toast = page.locator(".toast-message").first
                         if await toast.is_visible():
                             err = await toast.text_content()
                             print(f"[DEBUG] Website Error: {err}")
                 except Exception as ex:
                     print(f"Post-login check error: {ex}")

             else:
                 print("[DEBUG] Captcha failed. Retrying...")

        except Exception as e:
            print(f"[DEBUG] Error during login attempt: {e}")
            
        print("Refreshing page for retry...")
        print("Refreshing page for retry...")
        try:
            await page.reload()
            await page.wait_for_timeout(2000)
        except Exception as reload_err:
             print(f"[CRITICAL] Page crashed during reload: {reload_err}. Returning False to force restart.")
             return False
        
    return False


