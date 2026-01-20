import asyncio
import json
import os
import sys

# Add src to path just in case
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from playwright.async_api import async_playwright
from src import login

async def visual_validation():
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
        print("Launching browser...")
        browser = await p.chromium.launch(headless=False, args=["--start-maximized"])
        context = await browser.new_context(viewport={"width": 1920, "height": 1080})
        page = await context.new_page()

        print(f"Logging in as {username}...")
        
        # Use valid login module
        success = await login.login(page, username, password, api_key, tms_url)

        if success:
            print("\n✅ Login successful!")
            
            # Navigate to Order Entry
            print("Navigating to Order Entry...")
            order_url = f"{tms_url}/tms/me/memberclientorderentry"
            await page.goto(order_url, wait_until="networkidle")
            
            print("Visual Validation: Toggling Buy/Sell buttons...")
            
            # Selectors based on buy_stock.py and sell_stock.py
            # The toggle is usually custom labels or radio buttons
            
            # Let's inspect potential selectors from buy/sell scripts
            # Buy: .order__options--buy
            # Sell: .order__options--sell
            
            for i in range(3):
                print(f"Loop {i+1}/3")
                
                # Click BUY
                print(">> Switch to BUY (Green)")
                await page.click(".order__options--buy")
                await page.wait_for_timeout(2000)
                
                # Visual check via console (optional)
                is_buy_active = await page.evaluate("""() => {
                    const el = document.querySelector('.order__options--buy');
                    return el && (el.classList.contains('active') || window.getComputedStyle(el).backgroundColor.includes('green'));
                }""")
                print(f"Verified BUY active: {is_buy_active}")

                # Click SELL
                print(">> Switch to SELL (Red)")
                await page.click(".order__options--sell")
                await page.wait_for_timeout(2000)
                
                is_sell_active = await page.evaluate("""() => {
                    const el = document.querySelector('.order__options--sell');
                    return el && (el.classList.contains('active') || window.getComputedStyle(el).backgroundColor.includes('red'));
                }""")
                print(f"Verified SELL active: {is_sell_active}")

            print("\nValidation Loop Complete.")
            
        else:
            print("\n❌ Login failed! Cannot proceed with validation.")

        print("\nKeeping browser open for 10 seconds...")
        await page.wait_for_timeout(10000)
        await browser.close()

if __name__ == "__main__":
    try:
        asyncio.run(visual_validation())
    except Exception as e:
        import traceback
        traceback.print_exc()
        # Pause to let user read error if run from direct shell
        import time
        time.sleep(5)
