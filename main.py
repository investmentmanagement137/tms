"""
Apify Actor entry point for TMS Trade Book Scraper
"""
import os
import sys
from apify import Actor
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import tms_utils
from trade_book import scrape_trade_book, upload_to_supabase


async def main():
    async with Actor:
        # Get input from Apify
        actor_input = await Actor.get_input() or {}
        
        # Extract inputs with fallbacks
        tms_username = actor_input.get('tmsUsername')
        tms_password = actor_input.get('tmsPassword')
        gemini_api_key = actor_input.get('geminiApiKey')
        
        supabase_endpoint = actor_input.get('supabaseEndpoint', '')
        supabase_region = actor_input.get('supabaseRegion', 'ap-southeast-1')
        supabase_access_key = actor_input.get('supabaseAccessKey', '')
        supabase_secret_key = actor_input.get('supabaseSecretKey', '')
        supabase_bucket_name = actor_input.get('supabaseBucketName', 'investment_management')
        days_to_scrape = actor_input.get('daysToScrape', 365)
        upload_to_s3 = actor_input.get('uploadToS3', True)
        
        # Validate required inputs
        if not all([tms_username, tms_password, gemini_api_key]):
            await Actor.fail('Missing required inputs: tmsUsername, tmsPassword, or geminiApiKey')
            return
        
        Actor.log.info('Starting TMS Trade Book Scraper...')
        Actor.log.info(f'Scraping last {days_to_scrape} days of trade history')
        
        # Setup Chrome Options for Apify environment
        chrome_options = Options()
        
        # Apify runs in headless mode
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-software-rasterizer")
        chrome_options.add_argument("--window-size=1920,1080")
        
        # Add realistic User-Agent
        chrome_options.add_argument(
            'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
        )
        
        # Anti-detection measures
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        
        # Initialize WebDriver
        Actor.log.info('Launching Chrome browser...')
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        try:
            # Login using tms_utils
            login_url = "https://tms43.nepsetms.com.np/login"
            Actor.log.info('Attempting login to TMS...')
            
            success = tms_utils.perform_login(
                driver, 
                tms_username, 
                tms_password, 
                gemini_api_key, 
                login_url
            )
            
            if not success:
                await Actor.fail('Login failed after maximum attempts')
                return
            
            Actor.log.info('Login successful!')
            
            # Set environment variables for trade_book script
            os.environ['TMS_USERNAME'] = tms_username
            os.environ['TMS_PASSWORD'] = tms_password
            os.environ['GEMINI_API_KEY'] = gemini_api_key
            os.environ['SUPABASE_ENDPOINT'] = supabase_endpoint
            os.environ['SUPABASE_REGION'] = supabase_region
            os.environ['SUPABASE_ACCESS_KEY'] = supabase_access_key
            os.environ['SUPABASE_SECRET_KEY'] = supabase_secret_key
            os.environ['SUPABASE_BUCKET_NAME'] = supabase_bucket_name
            
            # Scrape trade book
            Actor.log.info('Starting trade book scraping...')
            csv_file = scrape_trade_book(driver, days=days_to_scrape)
            
            if not csv_file:
                await Actor.fail('Failed to scrape trade book data')
                return
            
            Actor.log.info(f'Successfully scraped data to {csv_file}')
            
            # Save CSV to Apify key-value store
            Actor.log.info('Saving CSV to Apify storage...')
            await Actor.set_value('OUTPUT', open(csv_file, 'r').read(), content_type='text/csv')
            
            # Upload to S3 if enabled
            if upload_to_s3 and all([supabase_endpoint, supabase_access_key, supabase_secret_key]):
                Actor.log.info('Uploading to Supabase S3...')
                upload_to_supabase(csv_file)
                Actor.log.info('Upload complete!')
            elif upload_to_s3:
                Actor.log.warning('S3 upload requested but credentials missing - skipping')
            
            # Parse CSV and push to dataset for easy viewing
            Actor.log.info('Parsing CSV data for Apify dataset...')
            import csv
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                
                if rows:
                    await Actor.push_data(rows)
                    Actor.log.info(f'Pushed {len(rows)} records to dataset')
                else:
                    Actor.log.warning('No data rows found in CSV')
            
            Actor.log.info('✅ Scraping completed successfully!')
            
        except Exception as e:
            Actor.log.error(f'Error during scraping: {e}')
            await Actor.fail(str(e))
            
        finally:
            driver.quit()
            Actor.log.info('Browser closed')


if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
