import asyncio
import json
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from playwright.async_api import async_playwright
from src import login

async def debug_toggle():
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
            
            # Navigate to Order Entry WITH a symbol (like in user's screenshot)
            symbol = "NICFC"
            order_url = f"{tms_url}/tms/me/memberclientorderentry?symbol={symbol}"
            print(f"Navigating to Order Entry: {order_url}")
            await page.goto(order_url, wait_until="networkidle")
            
            # Wait a bit for Angular components to render
            await page.wait_for_timeout(3000)
            
            # Take screenshot BEFORE toggle attempt
            await page.screenshot(path="debug_order_entry.png")
            print("📸 Screenshot saved: debug_order_entry.png")
            
            # Check what elements are on the page
            print("\n--- DOM Analysis ---")
            
            # Check for toggler-btn-wrapper
            toggler_count = await page.locator(".toggler-btn-wrapper").count()
            print(f"Found {toggler_count} .toggler-btn-wrapper elements")
            
            # Check for box-order-entry
            box_order_entry = await page.locator(".box-order-entry").count()
            print(f"Found {box_order_entry} .box-order-entry elements")
            
            # Check for order__options (old selector)
            order_options = await page.locator(".order__options--buy").count()
            print(f"Found {order_options} .order__options--buy elements")
            
            # Check for app-three-state-toggle
            three_state = await page.locator("app-three-state-toggle").count()
            print(f"Found {three_state} app-three-state-toggle elements")
            
            # Get all classes on the main container
            classes = await page.evaluate("""() => {
                const el = document.querySelector('.box-order-entry');
                return el ? el.className : 'NOT FOUND';
            }""")
            print(f"box-order-entry classes: {classes}")
            
            # Get toggler text if any
            toggler_texts = await page.evaluate("""() => {
                const els = document.querySelectorAll('.toggler-btn-wrapper');
                return Array.from(els).map(e => e.textContent.trim());
            }""")
            print(f"Toggler texts: {toggler_texts}")
            
            print("\n--- Attempting Toggle ---")
            
            if toggler_count > 0:
                # Try clicking first toggler (Buy)
                print("Clicking first .toggler-btn-wrapper (Buy)...")
                await page.click(".toggler-btn-wrapper:first-of-type", timeout=5000, force=True)
                await page.wait_for_timeout(1000)
                await page.screenshot(path="debug_after_buy_click.png")
                print("📸 Screenshot saved: debug_after_buy_click.png")
                
                # Check state
                has_box_buy = await page.evaluate("""() => {
                    const el = document.querySelector('.box-order-entry');
                    return el ? el.classList.contains('box-buy') : false;
                }""")
                print(f"Has box-buy class after click: {has_box_buy}")
                
                # Try clicking second toggler (Sell)
                print("\nClicking second .toggler-btn-wrapper (Sell)...")
                await page.click(".toggler-btn-wrapper:last-of-type", timeout=5000, force=True)
                await page.wait_for_timeout(1000)
                await page.screenshot(path="debug_after_sell_click.png")
                print("📸 Screenshot saved: debug_after_sell_click.png")
                
                has_box_sell = await page.evaluate("""() => {
                    const el = document.querySelector('.box-order-entry');
                    return el ? el.classList.contains('box-sell') : false;
                }""")
                print(f"Has box-sell class after click: {has_box_sell}")
            else:
                print("⚠️ No toggler elements found! Check screenshot for page state.")
            
            print("\n--- Debug Complete ---")
            
        else:
            print("\n❌ Login failed!")
            await page.screenshot(path="debug_login_failed.png")

        print("\nKeeping browser open for 15 seconds for inspection...")
        await page.wait_for_timeout(15000)
        await browser.close()

if __name__ == "__main__":
    try:
        asyncio.run(debug_toggle())
    except Exception as e:
        import traceback
        traceback.print_exc()
