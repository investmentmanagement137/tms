import asyncio
import json
import os
import sys

# Ensure src can be imported
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from playwright.async_api import async_playwright
from src import login
from src.utils import set_symbol

async def verify_symbol_entry():
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
        print("Launching browser...")
        browser = await p.chromium.launch(headless=False, args=["--start-maximized"])
        context = await browser.new_context(viewport={"width": 1920, "height": 1080})
        page = await context.new_page()

        print(f"Logging in as {username}...")
        success = await login.login(page, username, password, api_key, tms_url)

        if success:
            print("\n✅ Login successful!")
            
            # Navigate to Order Entry WITHOUT symbol
            order_url = f"{tms_url}/tms/me/memberclientorderentry"
            print(f"Navigating to Order Entry: {order_url}")
            await page.goto(order_url, wait_until="networkidle")
            await page.wait_for_timeout(3000)

            # Test Symbol Entry
            test_symbol = "NICA"
            print(f"\n--- Testing Symbol Entry: {test_symbol} ---")
            
            result = await set_symbol(page, test_symbol)
            
            if result:
                print("✅ Symbol set function returned True")
            else:
                print("❌ Symbol set function returned False")
                
            # Double check input value
            val = await page.input_value("input[formcontrolname='companyName'], .k-autocomplete input")
            print(f"Input value after set: {val}")
            
            if test_symbol in val:
                 print("✅ Verification Passed")
            else:
                 print("❌ Verification Failed - Input mismatch")

        else:
            print("\n❌ Login failed!")

        print("\nClosing browser...")
        await browser.close()

if __name__ == "__main__":
    try:
        asyncio.run(verify_symbol_entry())
    except Exception as e:
        import traceback
        traceback.print_exc()
