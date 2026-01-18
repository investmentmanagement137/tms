import asyncio
from playwright.async_api import async_playwright
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.getcwd(), 'src'))

from dashboard import extract_dashboard_data

async def run_mock_test():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Load dump file
        dump_path = os.path.abspath("dashboard_dump.html")
        print(f"Loading dump from: {dump_path}")
        
        # Read file content
        with open(dump_path, "r", encoding="utf-8") as f:
            html_content = f.read()
        
        # Set content
        await page.set_content(html_content)
        
        # Run extraction
        print("Running extractor...")
        try:
            data = await extract_dashboard_data(page)
            print("\n--- TEST RESULTS ---")
            print(data)
            
            # Assertions
            if data['collateral'].get('amount'):
                print("PASS: Collateral Amount found")
            else:
                print("FAIL: Collateral Amount missing")

            if data['limits'].get('available'):
                print("PASS: Available Limit found")
            else:
                print("FAIL: Available Limit missing")
                
        except Exception as e:
            print(f"ERROR: {e}")
            import traceback
            traceback.print_exc()
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_mock_test())
