import asyncio
from playwright.async_api import async_playwright
import os

# CONFIG
TMS_URL = "https://tms43.nepsetms.com.np/login" 

async def main():
    print("Launching Browser for Inspection...")
    async with async_playwright() as p:
        # Launch Headful Chrome
        browser = await p.chromium.launch(headless=False, args=["--start-maximized"])
        context = await browser.new_context(viewport=None)
        page = await context.new_page()
        
        print(f"Navigating to {TMS_URL}...")
        await page.goto(TMS_URL)
        
        print("!!! ACTION REQUIRED !!!")
        print("Please log in to TMS manually in the opened browser window.")
        print("The script is monitoring the URL. Once it detects 'dashboard', it will proceed.")
        
        # Wait for dashboard
        while True:
            url = page.url
            if "dashboard" in url or "tms/me" in url:
                print("Dashboard detected!")
                break
            await asyncio.sleep(1)
            
        print("Waiting 5 seconds for dashboard widgets to load...")
        await page.wait_for_timeout(5000)
        
        # Scrape Dashboard
        print("Saving Dashboard HTML...")
        dashboard_html = await page.content()
        with open("dashboard_dump.html", "w", encoding="utf-8") as f:
            f.write(dashboard_html)
            
        # Optional: Scrape Order Entry?
        # print("Navigating to Order Entry...")
        # await page.goto("https://tms43.nepsetms.com.np/tms/n/order/order-entry")
        # await page.wait_for_timeout(3000)
        # order_html = await page.content()
        # with open("order_dump.html", "w", encoding="utf-8") as f:
        #    f.write(order_html)
            
        print("Done! Browser will close in 5 seconds.")
        await page.wait_for_timeout(5000)
        await browser.close()
        print("Inspection complete. Files saved: dashboard_dump.html")

if __name__ == "__main__":
    asyncio.run(main())
