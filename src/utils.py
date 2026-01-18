import re
import io
import time
import asyncio
from PIL import Image
import asyncio
from PIL import Image
from google import genai
from google.genai import types

async def solve_captcha(page, api_key):
    """Solves captcha using Gemini API (new google-genai SDK)."""
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
        screenshot_bytes = await captcha_loc.screenshot()
        image = Image.open(io.BytesIO(screenshot_bytes))
        
        print("Sending to Gemini API...")
        # Client initialization
        client = genai.Client(api_key=api_key)
        
        # We run this in a thread executor because the new SDK might still be sync-heavy or we just want to be safe
        loop = asyncio.get_event_loop()
        
        def generate():
            response = client.models.generate_content(
                model='gemini-2.0-flash',
                contents=[
                    "What is the text in this captcha image? Return ONLY the alphanumeric text, no other words.",
                    image
                ]
            )
            return response.text

        captcha_text = await loop.run_in_executor(None, generate)
        
        if captcha_text:
            captcha_text = captcha_text.strip()
            print(f"Gemini solved captcha: '{captcha_text}'")
            return captcha_text
        else:
             print("Gemini returned empty text.")
             return None
        
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
             # Use domcontentloaded instead of networkidle for faster, more reliable loads
             await page.goto(login_url, wait_until='domcontentloaded', timeout=30000)
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


