import asyncio
import os
from playwright.async_api import async_playwright

# Config
TMS_URL = "https://tms43.nepsetms.com.np"
ORDER_ENTRY_PATH = "/tms/me/memberclientorderentry"

async def main():
    async with async_playwright() as p:
        # Launch non-headless for manual interaction if needed
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
        )
        
        # Load session if exists (optional, mostly for convenience)
        # try:
        #     await context.add_cookies(...) 
        # except: pass
        
        page = await context.new_page()
        
        print(f"Navigating to {TMS_URL}...")
        await page.goto(TMS_URL)
        
        print("\n" + "="*50)
        print("PLEASE LOG IN MANUALLY NOW.")
        print("Once logged in, the script will attempt to navigate to the Order Entry page.")
        print("Press ENTER in this terminal once you see the Dashboard.")
        print("="*50 + "\n")
        
        input("Press ENTER after Login...")
        
        target_url = TMS_URL + ORDER_ENTRY_PATH
        print(f"Navigating to Order Entry: {target_url}")
        await page.goto(target_url, wait_until='networkidle')
        
        # Wait a bit for dynamic forms to render
        await page.wait_for_timeout(5000)
        
        # Dump HTML
        content = await page.content()
        with open("order_entry_dump.html", "w", encoding="utf-8") as f:
            f.write(content)
            
        print(f"✅ HTML dumped to {os.path.abspath('order_entry_dump.html')}")
        
        # Dump Screenshot
        await page.screenshot(path="order_entry_dump.png")
        print(f"✅ Screenshot saved to order_entry_dump.png")
        
        input("Press ENTER to close browser...")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
