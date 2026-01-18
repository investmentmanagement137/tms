"""
Apify Actor entry point for TMS Order Executor
"""
import os
import datetime
import json
import boto3
from apify import Actor
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# Import modular scripts
from src import utils, login, buy_stock, sell_stock, daily_history


def upload_to_supabase(file_path, endpoint, region, access_key, secret_key, bucket_name):
    """Upload file to Supabase S3"""
    try:
        session = boto3.session.Session()
        s3 = session.client(
            's3',
            region_name=region,
            endpoint_url=endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key
        )
        
        print(f"Uploading {file_path} to bucket: {bucket_name}")
        with open(file_path, "rb") as f:
            s3.upload_fileobj(f, bucket_name, file_path)
            
        print(f"Success! File '{file_path}' uploaded successfully.")
        return True
        
    except Exception as e:
        print(f"Error uploading to Supabase: {e}")
        return False


async def main():
    async with Actor:
        # Get input from Apify
        actor_input = await Actor.get_input() or {}
        
        # Extract inputs
        tms_username = actor_input.get('tmsUsername')
        tms_password = actor_input.get('tmsPassword')
        gemini_api_key = actor_input.get('geminiApiKey')
        tms_url = actor_input.get('tmsUrl')
        
        # Sanitize tmsUrl to remove trailing /login or /
        if tms_url:
            tms_url = tms_url.strip().rstrip('/')
            if tms_url.endswith('/login'):
                tms_url = tms_url[:-6] # Remove /login
            tms_url = tms_url.rstrip('/') # Clean again
            
        action = actor_input.get('action', 'CHECK_ORDERS') # Default to safer option
        
        supabase_endpoint = actor_input.get('supabaseEndpoint', '')
        supabase_region = actor_input.get('supabaseRegion', 'ap-southeast-1')
        supabase_access_key = actor_input.get('supabaseAccessKey', '')
        supabase_secret_key = actor_input.get('supabaseSecretKey', '')
        supabase_bucket_name = actor_input.get('supabaseBucketName', 'investment_management')
        upload_to_s3 = actor_input.get('uploadToS3', True)
        
        # Validate Credentials
        if not all([tms_username, tms_password, gemini_api_key, tms_url]):
            await Actor.fail('Missing required credentials: tmsUsername, tmsPassword, geminiApiKey, or tmsUrl')
            return

        Actor.log.info(f'Starting TMS Actor: Action = {action} on {tms_url}')
        
        # Setup Chrome Options
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument(
            'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
        )
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        
        # Initialize WebDriver
        Actor.log.info('Launching Chrome browser...')
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # --- Versioning ---
        VERSION = "1.1.0"
        Actor.log.info(f"TMS Actor Version: {VERSION}")
        
        try:
            # 1. Perform Login
            Actor.log.info('Executing Login Script...')
            success = login.login(driver, tms_username, tms_password, gemini_api_key, tms_url)
            
            if not success:
                await Actor.fail(status_message='Login failed')
                return
            
            Actor.log.info('Login successful!')
            
            final_output = {
                "version": VERSION,
                "status": "SUCCESS",
                "timestamp": str(datetime.datetime.now()),
                "batch_results": []
            }

            # Check for Batch Orders
            batch_orders = actor_input.get('orders', [])
            check_orders_flag = actor_input.get('checkOrders', True)
            
            executed_any_order = False

            if batch_orders and isinstance(batch_orders, list) and len(batch_orders) > 0:
                Actor.log.info(f"Processing Batch of {len(batch_orders)} orders...")
                
                for order in batch_orders:
                    o_symbol = str(order.get('symbol')).strip().upper()
                    o_qty = int(order.get('qty', 0))
                    o_price = float(order.get('price', 0))
                    o_side = str(order.get('side')).upper() # BUY or SELL
                    
                    Actor.log.info(f"Batch Processing: {o_side} {o_symbol} x {o_qty} @ {o_price}")
                    
                    res = {}
                    if o_side == 'BUY':
                        res = buy_stock.execute(driver, tms_url, o_symbol, o_qty, o_price)
                    elif o_side == 'SELL':
                        res = sell_stock.execute(driver, tms_url, o_symbol, o_qty, o_price)
                    else:
                        res = {"status": "SKIPPED", "message": f"Invalid side: {o_side}"}
                        
                    final_output["batch_results"].append(res)
                    executed_any_order = True
                    time.sleep(1) # Brief pause between orders

            else:
                # Fallback to Single Action Logic (Legacy/Single Mode)
                if action == 'BUY':
                    symbol = actor_input.get('symbol')
                    buy_price = actor_input.get('buyPrice')
                    buy_quantity = actor_input.get('buyQuantity')
                    
                    if all([symbol, buy_price, buy_quantity]):
                        Actor.log.info('Executing Single BUY...')
                        order_result = buy_stock.execute(driver, tms_url, str(symbol).strip().upper(), int(buy_quantity), float(buy_price))
                        final_output["batch_results"].append(order_result)
                        executed_any_order = True
                
                elif action == 'SELL':
                    symbol = actor_input.get('symbol')
                    sell_price = actor_input.get('sellPrice')
                    sell_quantity = actor_input.get('sellQuantity')
                     
                    if all([symbol, sell_price, sell_quantity]):
                        Actor.log.info('Executing Single SELL...')
                        order_result = sell_stock.execute(driver, tms_url, str(symbol).strip().upper(), int(sell_quantity), float(sell_price))
                        final_output["batch_results"].append(order_result)
                        executed_any_order = True

            # Global Verification (Once at the end)
            if (executed_any_order and check_orders_flag) or action == 'CHECK_ORDERS':
                 Actor.log.info('Executing Daily History Script (Verification)...')
                 orders = daily_history.extract(driver, tms_url)
                 final_output["todaysOrderPage"] = orders
            else:
                 Actor.log.info("Skipping verification.")
            

            
            # 3. Save Output
            today = datetime.date.today()
            filename = f"tms-output-{today}.json"
            
            Actor.log.info(f'Saving response to {filename}...')
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(final_output, f, indent=4, ensure_ascii=False)
            
            # Save to Apify Store
            await Actor.set_value('OUTPUT', final_output)
            await Actor.push_data(final_output)
            
            # Upload to S3
            if upload_to_s3 and all([supabase_endpoint, supabase_access_key, supabase_secret_key]):
                Actor.log.info('Uploading JSON to Supabase S3...')
                upload_to_supabase(filename, supabase_endpoint, supabase_region, supabase_access_key, supabase_secret_key, supabase_bucket_name)
            
            Actor.log.info('✅ Workflow Completed Successfully!')
            
        except Exception as e:
            Actor.log.error(f'Error during execution: {e}')
            import traceback
            Actor.log.error(traceback.format_exc())
            await Actor.fail(status_message=str(e))
            
        finally:
            driver.quit()
            Actor.log.info('Browser closed')

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
