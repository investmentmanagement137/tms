"""
TMS Login Test - Playwright Version

This script uses Playwright to test the TMS login flow locally.
Run with: python test_playwright.py
"""

import asyncio
from playwright.async_api import async_playwright
import os

# Configuration - USE ENVIRONMENT VARIABLES for security
TMS_URL = "https://tms43.nepsetms.com.np/login"
USERNAME = os.environ.get("TMS_USERNAME", "Bp480035")
PASSWORD = os.environ.get("TMS_PASSWORD")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")

if not PASSWORD or not GEMINI_KEY:
    print("ERROR: Please set TMS_PASSWORD and GEMINI_API_KEY environment variables")
    print("Example (PowerShell):")
    print('  $env:TMS_PASSWORD="your_password"')
    print('  $env:GEMINI_API_KEY="your_api_key"')
    exit(1)

async def solve_captcha_with_gemini(page, api_key):
    """Extract and solve captcha using Gemini API ONLY"""
    print("[DEBUG] Solving captcha with Gemini API...")
    
    try:
        # Wait for captcha image to load
        await page.wait_for_selector('.captcha-image-dimension', timeout=5000)
        
        # Take screenshot of captcha element
        captcha_element = await page.query_selector('.captcha-image-dimension')
        captcha_screenshot = await captcha_element.screenshot()
        
        # Use Gemini to solve
        print("[DEBUG] Sending captcha image to Gemini...")
        import google.generativeai as genai
        from PIL import Image
        import io
        
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        # Convert screenshot to PIL Image
        image = Image.open(io.BytesIO(captcha_screenshot))
        
        response = model.generate_content([
            "What is the text in this captcha image? Return ONLY the alphanumeric text, no other words.",
            image
        ])
        
        captcha_text = response.text.strip()
        print(f"[DEBUG] Gemini solved captcha: '{captcha_text}'")
        return captcha_text
        
    except Exception as e:
        print(f"[DEBUG] Error solving captcha: {e}")
        return None

async def perform_login_playwright(page):
    """Perform TMS login using Playwright"""
    print(f"[DEBUG] Navigating to {TMS_URL}...")
    await page.goto(TMS_URL, wait_until='networkidle', timeout=30000)
    
    # Check page title
    title = await page.title()
    print(f"[DEBUG] Page title: {title}")
    
    if "403" in title or "Forbidden" in title:
        print("❌ 403 Forbidden detected!")
        return False
    
    max_retries = 3
    for attempt in range(1, max_retries + 1):
        print(f"\n[DEBUG] --- Login Attempt {attempt}/{max_retries} ---")
        
        try:
            # Fill username
            print("[DEBUG] Filling username...")
            username_selector = 'input[placeholder*="Client Code"]'
            await page.fill(username_selector, USERNAME)
            
            # Fill password
            print("[DEBUG] Filling password...")
            await page.fill('#password-field', PASSWORD)
            
            # Solve captcha
            captcha_text = await solve_captcha_with_gemini(page, GEMINI_KEY)
            
            if captcha_text:
                print(f"[DEBUG] Using captcha: {captcha_text}")
                await page.fill('#captchaEnter', captcha_text)
                
                # Click login
                print("[DEBUG] Clicking login button...")
                await page.click('.login__button')
                
                # Wait for navigation
                print("[DEBUG] Waiting for login response...")
                await asyncio.sleep(5)
                
                current_url = page.url
                print(f"[DEBUG] Current URL: {current_url}")
                
                if "dashboard" in current_url or "tms/me" in current_url:
                    print("✅ LOGIN SUCCESSFUL!")
                    return True
                else:
                    print(f"[DEBUG] Login failed. URL didn't change.")
                    await page.reload()
                    await asyncio.sleep(2)
            else:
                print("[DEBUG] No captcha text obtained")
                await page.reload()
                await asyncio.sleep(2)
                
        except Exception as e:
            print(f"[DEBUG] Error during attempt {attempt}: {e}")
            await page.reload()
            await asyncio.sleep(2)
    
    print("❌ Max login attempts reached")
    return False

async def main():
    print("\n" + "="*60)
    print("TMS LOGIN TEST - PLAYWRIGHT")
    print("="*60)
    
    async with async_playwright() as p:
        # Launch browser (visible for debugging)
        browser = await p.chromium.launch(
            headless=False,  # Set to True for headless mode
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-dev-shm-usage'
            ]
        )
        
        # Create context with anti-detection
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        
        # Disable automation indicators
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)
        
        page = await context.new_page()
        
        try:
            success = await perform_login_playwright(page)
            
            if success:
                print("\n" + "="*60)
                print("✅ TEST SUCCESSFUL!")
                print("="*60)
                print(f"You are logged in. Current URL: {page.url}")
                print("\nBrowser will stay open for 30 seconds...")
                await asyncio.sleep(30)
            else:
                print("\n" + "="*60)
                print("❌ TEST FAILED")
                print("="*60)
                # Save page source
                content = await page.content()
                with open("playwright_debug.html", "w", encoding="utf-8") as f:
                    f.write(content)
                print("Page source saved to: playwright_debug.html")
                
                print("\nBrowser will stay open for 30 seconds for inspection...")
                await asyncio.sleep(30)
                
        finally:
            await browser.close()
            print("Browser closed.")

if __name__ == "__main__":
    asyncio.run(main())
