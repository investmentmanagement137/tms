"""
Apify Actor entry point for TMS Trade Book Scraper
"""
import os
import csv
import datetime
import boto3
from apify import Actor
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# Import from src folder
from src import utils
from src import tms_client


def upload_to_supabase(csv_filename, endpoint, region, access_key, secret_key, bucket_name):
    """Upload CSV file to Supabase S3"""
    try:
        session = boto3.session.Session()
        s3 = session.client(
            's3',
            region_name=region,
            endpoint_url=endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key
        )
        
        print(f"Uploading {csv_filename} to bucket: {bucket_name}")
        with open(csv_filename, "rb") as f:
            s3.upload_fileobj(f, bucket_name, csv_filename)
            
        print(f"Success! File '{csv_filename}' uploaded successfully.")
        return True
        
    except Exception as e:
        print(f"Error uploading to Supabase: {e}")
        return False


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
            # Login using utils
            login_url = "https://tms43.nepsetms.com.np/login"
            Actor.log.info('Attempting login to TMS...')
            
            success = utils.perform_login(
                driver, 
                tms_username, 
                tms_password, 
                gemini_api_key, 
                login_url
            )
            
            if not success:
                await Actor.fail(status_message='Login failed after maximum attempts')
                return
            
            Actor.log.info('Login successful!')
            
            # Create TMS client for scraping
            Actor.log.info('Starting trade book scraping...')
            client = tms_client.TMSClient(driver)
            
            # Convert days to months (approx 30 days per month)
            months = max(1, days_to_scrape // 30)
            
            data = client.extract_tradebook(months=months)
            
            if not data or len(data) == 0:
                await Actor.fail(status_message='No trade book data extracted')
                return
            
            # Parse data into list of dicts
            json_data = []
            if len(data) > 1:
                headers = data[0]
                rows = data[1:]
                for row in rows:
                    if len(row) == len(headers):
                        json_data.append(dict(zip(headers, row)))
            
            if not json_data:
                await Actor.fail(status_message='No trade book data to save (empty or header only)')
                return

            # Save data to JSON
            today = datetime.date.today()
            json_filename = f"trade-book-history-{today}.json"
            
            import json
            Actor.log.info(f'Saving formatted JSON to {json_filename}...')
            with open(json_filename, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=4, ensure_ascii=False)
            
            Actor.log.info(f'Successfully saved {len(json_data)} records to JSON')
            
            # Save JSON to Apify key-value store
            Actor.log.info('Saving JSON to Apify storage...')
            with open(json_filename, 'r', encoding='utf-8') as f:
                await Actor.set_value('OUTPUT', f.read(), content_type='application/json')
            
            # Upload to S3 if enabled
            if upload_to_s3 and all([supabase_endpoint, supabase_access_key, supabase_secret_key]):
                Actor.log.info('Uploading JSON to Supabase S3...')
                success = upload_to_supabase(
                    json_filename,
                    supabase_endpoint,
                    supabase_region,
                    supabase_access_key,
                    supabase_secret_key,
                    supabase_bucket_name
                )
                if success:
                    Actor.log.info('Upload complete!')
                else:
                    Actor.log.warning('S3 upload failed')
            elif upload_to_s3:
                Actor.log.warning('S3 upload requested but credentials missing - skipping')
            
            # Push to dataset as well (Apify handles formatting there too)
            Actor.log.info('Pushing data to Apify dataset...')
            await Actor.push_data(json_data)
            Actor.log.info(f'Pushed {len(json_data)} records to dataset')
            
            Actor.log.info('✅ Scraping completed successfully!')
            
        except Exception as e:
            Actor.log.error(f'Error during scraping: {e}')
            import traceback
            Actor.log.error(traceback.format_exc())
            
            # Upload any debug screenshots found (BEFORE failing)
            import glob
            screenshots = glob.glob("*.png")
            for screenshot in screenshots:
                try:
                    Actor.log.info(f"Uploading debug screenshot: {screenshot}")
                    with open(screenshot, 'rb') as f:
                        await Actor.set_value(screenshot, f.read(), content_type='image/png')
                except Exception as ex:
                    Actor.log.warning(f"Failed to upload screenshot {screenshot}: {ex}")
            
            await Actor.fail(status_message=str(e))
            
        finally:
            driver.quit()
            Actor.log.info('Browser closed')


if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
