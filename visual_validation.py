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
            
            # Corrected selectors based on actual DOM structure from user screenshots:
            # - Uses .toggler-btn-wrapper labels (first for Buy, second for Sell)
            # - Active state indicated by .is-active class on label
            # - Parent container changes class: .box-buy or .box-sell
            
            for i in range(3):
                print(f"Loop {i+1}/3")
                
                # Click BUY (first toggler)
                print(">> Switch to BUY (Green)")
                try:
                    await page.click(".toggler-btn-wrapper:first-of-type", timeout=3000, force=True)
                except:
                    # Fallback to JS
                    await page.evaluate("""() => {
                        const togglers = document.querySelectorAll('.toggler-btn-wrapper');
                        if (togglers.length > 0) togglers[0].click();
                    }""")
                await page.wait_for_timeout(2000)
                
                # Verify BUY is active
                is_buy_active = await page.evaluate("""() => {
                    const container = document.querySelector('.box-order-entry');
                    const togglers = document.querySelectorAll('.toggler-btn-wrapper');
                    return (container && container.classList.contains('box-buy')) || 
                           (togglers.length > 0 && togglers[0].classList.contains('is-active'));
                }""")
                print(f"Verified BUY active: {is_buy_active}")

                # Click SELL (second toggler)
                print(">> Switch to SELL (Red)")
                try:
                    await page.click(".toggler-btn-wrapper:last-of-type", timeout=3000, force=True)
                except:
                    # Fallback to JS
                    await page.evaluate("""() => {
                        const togglers = document.querySelectorAll('.toggler-btn-wrapper');
                        if (togglers.length > 1) togglers[1].click();
                    }""")
                await page.wait_for_timeout(2000)
                
                # Verify SELL is active
                is_sell_active = await page.evaluate("""() => {
                    const container = document.querySelector('.box-order-entry');
                    const togglers = document.querySelectorAll('.toggler-btn-wrapper');
                    return (container && container.classList.contains('box-sell')) || 
                           (togglers.length > 1 && togglers[1].classList.contains('is-active'));
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
