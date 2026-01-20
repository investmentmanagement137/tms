import asyncio
import json
import os
import sys

# Ensure src can be imported
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from playwright.async_api import async_playwright
from src import login
from src.utils import set_toggle_position, get_toggle_state

async def verify_toggle():
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
            
            # Navigate to Order Entry
            symbol = "NICA" # Random symbol to ensure page loads fully
            order_url = f"{tms_url}/tms/me/memberclientorderentry?symbol={symbol}"
            print(f"Navigating to Order Entry: {order_url}")
            await page.goto(order_url, wait_until="networkidle")
            await page.wait_for_timeout(3000)

            # Test BUY
            print("\n--- Testing BUY Toggle ---")
            await set_toggle_position(page, "buy")
            state = await get_toggle_state(page)
            print(f"Current State: {state}")
            if state == "buy":
                print("✅ BUY verification passed")
            else:
                print("❌ BUY verification failed")

            await page.wait_for_timeout(1000)

            # Test SELL
            print("\n--- Testing SELL Toggle ---")
            await set_toggle_position(page, "sell")
            state = await get_toggle_state(page)
            print(f"Current State: {state}")
            if state == "sell":
                print("✅ SELL verification passed")
            else:
                print("❌ SELL verification failed")

            # Test BUY again
            print("\n--- Testing BUY Toggle (Switch Back) ---")
            await set_toggle_position(page, "buy")
            state = await get_toggle_state(page)
            print(f"Current State: {state}")
            if state == "buy":
                 print("✅ BUY verification (switch back) passed")
            else:
                 print("❌ BUY verification (switch back) failed")

        else:
            print("\n❌ Login failed!")

        print("\nClosing browser...")
        await browser.close()

if __name__ == "__main__":
    try:
        asyncio.run(verify_toggle())
    except Exception as e:
        import traceback
        traceback.print_exc()
