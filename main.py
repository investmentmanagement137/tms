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
                await Actor.fail('Login failed after maximum attempts')
                return
            
            Actor.log.info('Login successful!')
            
            # Create TMS client for scraping
            Actor.log.info('Starting trade book scraping...')
            client = tms_client.TMSClient(driver)
            
            # Convert days to months (approx 30 days per month)
            months = max(1, days_to_scrape // 30)
            
            data = client.extract_tradebook(months=months)
            
            if not data or len(data) == 0:
                await Actor.fail('No trade book data extracted')
                return
            
            # Save data to CSV
            today = datetime.date.today()
            csv_filename = f"trade-book-history-{today}.csv"
            
            Actor.log.info(f'Saving data to {csv_filename}...')
            with open(csv_filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                for row in data:
                    writer.writerow(row)
            
            Actor.log.info(f'Successfully saved {len(data)} rows to CSV')
            
            # Save CSV to Apify key-value store
            Actor.log.info('Saving CSV to Apify storage...')
            with open(csv_filename, 'r') as f:
                await Actor.set_value('OUTPUT', f.read(), content_type='text/csv')
            
            # Upload to S3 if enabled
            if upload_to_s3 and all([supabase_endpoint, supabase_access_key, supabase_secret_key]):
                Actor.log.info('Uploading to Supabase S3...')
                success = upload_to_supabase(
                    csv_filename,
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
            
            # Parse CSV and push to dataset for easy viewing (skip header row)
            if len(data) > 1:
                Actor.log.info('Pushing data to Apify dataset...')
                headers = data[0]
                rows = data[1:]
                
                dict_rows = []
                for row in rows:
                    if len(row) == len(headers):
                        dict_rows.append(dict(zip(headers, row)))
                
                if dict_rows:
                    await Actor.push_data(dict_rows)
                    Actor.log.info(f'Pushed {len(dict_rows)} records to dataset')
                else:
                    Actor.log.warning('No valid data rows to push to dataset')
            else:
                Actor.log.warning('Only header row found, no data to push')
            
            Actor.log.info('✅ Scraping completed successfully!')
            
        except Exception as e:
            Actor.log.error(f'Error during scraping: {e}')
            import traceback
            Actor.log.error(traceback.format_exc())
            await Actor.fail(str(e))
            
        finally:
            driver.quit()
            Actor.log.info('Browser closed')


if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
