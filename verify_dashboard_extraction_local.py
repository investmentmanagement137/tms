
import asyncio
import os
import sys
from playwright.async_api import async_playwright
from src import dashboard

# Mock or override the goto behavior? 
# Or just let it fail navigation but continue? 
# No, fail navigation usually raises exception.

async def main():
    # Path to dump
    dump_path = os.path.abspath("dashboard_dump.html")
    file_url = f"file:///{dump_path.replace(os.sep, '/')}"
    
    print(f"Testing with dump: {file_url}")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        
        # Load the HTML content
        await page.goto(file_url)
        print("Loaded dashboard_dump.html")
        
        # Mock goto to prevent navigating away
        # We can route the dashboard URL to the file URL or just do nothing
        dashboard_url_suffix = "/tms/client/dashboard"
        
        await page.route("**/*", lambda route: route.continue_())
        
        # We need to trick extract_dashboard_data to NOT navigate or navigate to our file
        # But the function constructs the URL.
        # Let's monkeypatch page.goto
        original_goto = page.goto
        
        async def mock_goto(url, **kwargs):
            print(f"Intercepted goto: {url}")
            if "dashboard" in url:
                print("Skipping real navigation, staying on dump.")
                return 
            return await original_goto(url, **kwargs)
            
        page.goto = mock_goto
        
        # Run extraction
        # We pass a dummy URL base
        print("\n--- Running Extraction ---")
        data = await dashboard.extract_dashboard_data(page, "https://mock.tms.com.np")
        
        print("\n--- Extraction Result ---")
        import json
        print(json.dumps(data, indent=2))
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
