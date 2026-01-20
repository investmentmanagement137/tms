import asyncio
import json
import os
from playwright.async_api import async_playwright
from src import login
from src.toast_capture import log_toasts, capture_all_popups

async def test_login_and_toasts():
    # Load secrets
    if not os.path.exists("secrets.json"):
        print("secrets.json not found!")
        return

    with open("secrets.json", "r") as f:
        secrets = json.load(f)

    username = secrets["id"]
    password = secrets["password"]
    api_key = secrets["gemini_api_key"]
    tms_url = "https://tms43.nepsetms.com.np"

    async with async_playwright() as p:
        # Launch browser visibly
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        print(f"Logging in as {username}...")
        
        # Use the robust login function from src.login
        # It already uses log_toasts internally!
        success = await login.login(page, username, password, api_key, tms_url)

        if success:
            print("\n✅ Login successful!")
            
            # Navigate to a page to trigger toast
            print("Navigating to Order Book History to test toast capture...")
            await page.goto(f"{tms_url}/tms/client/dashboard", wait_until="domcontentloaded") # Dashboard first
            
            # Let's try to trigger a toast by doing something invalid or just checking existing ones
            # Example: Go to Order Book History and search without date
            await page.goto(f"{tms_url}/tms/me/order-book-history")
            await page.wait_for_timeout(2000)
            
            print("Attempting to trigger toast (Search without params)...")
            try:
                # Try to click search button expecting a "Please select date" error
                btn = page.locator("button:has-text('Search')").first
                if await btn.count() > 0:
                    await btn.click()
                else:
                    print("Search button not found, looking for Submit...")
                    await page.click("button[type='submit']")
            except Exception as e:
                print(f"Click failed: {e}")

            # Wait and capture
            print("Waiting for toasts...")
            await page.wait_for_timeout(2000)
            toasts = await capture_all_popups(page)
            
            if toasts:
                print(f"\n🎉 CAPTURED TOASTS: {toasts}")
            else:
                print("\n⚠️ No toasts captured yet. Trying another trigger...")

        else:
            print("\n❌ Login failed!")
            # Capture any error toasts present
            toasts = await capture_all_popups(page)
            print(f"Toasts visible at failure: {toasts}")

        print("\nKeeping browser open for 10 seconds...")
        await page.wait_for_timeout(10000)
        await browser.close()

if __name__ == "__main__":
    try:
        asyncio.run(test_login_and_toasts())
    except Exception as e:
        import traceback
        with open("error.log", "w", encoding="utf-8") as f:
            f.write(traceback.format_exc())
        print("Error details written to error.log")

