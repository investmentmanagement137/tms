import os
import sys
import asyncio
import json

# Add src to path to allow imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from apify import Actor, ProxyConfiguration
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

from utils import perform_login
from tms_client import TMSClient

async def main():
    async with Actor:
        print("Actor Starting...")
        
        # 1. Get Input
        actor_input = await Actor.get_input() or {}
        
        # Environment variables as fallback
        tms_website_url = actor_input.get('tmsWebsiteUrl', os.environ.get('TMS_WEBSITE_URL', 'https://tms58.nepsetms.com.np/login'))
        tms_login_id = actor_input.get('tmsLoginId', os.environ.get('TMS_LOGIN_ID'))
        tms_password = actor_input.get('tmsPassword', os.environ.get('TMS_PASSWORD'))
        gemini_api_key = actor_input.get('geminiApiKey', os.environ.get('GEMINI_API_KEY'))
        action = actor_input.get('action', os.environ.get('ACTION', 'EXTRACT_TRADEBOOK'))
        history_months = actor_input.get('historyDurationMonths', int(os.environ.get('HISTORY_MONTHS', 12)))
        order_details = actor_input.get('orderDetails', {})
        proxy_config_input = actor_input.get('proxyConfiguration')

        # Headless Configuration
        is_headless = os.environ.get("HEADLESS", "true").lower() == "true"

        if not tms_login_id or not tms_password:
            print("ERROR: Missing TMS Login ID or Password.")
            await Actor.fail(status_message="Missing Credentials")
            return
        
        if not gemini_api_key:
            print("WARNING: Missing Gemini API Key. Captcha solving might fail if strictly required.")

        print(f"Configuration: URL={tms_website_url}, User: {tms_login_id}, Action: {action}, Headless: {is_headless}, Months: {history_months}")

        # 2. Setup Selenium & Proxy
        chrome_options = Options()
        if is_headless:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")
        
        # Proxy Setup
        if proxy_config_input:
            print("[DEBUG] Proxy configuration found. Setting up proxy...")
            proxy_configuration = ProxyConfiguration(actor_input=proxy_config_input)
            proxy_url = await proxy_configuration.new_url()
            if proxy_url:
                print(f"[DEBUG] Using Proxy: {proxy_url}")
                chrome_options.add_argument(f'--proxy-server={proxy_url}')
            else:
                 print("[DEBUG] Proxy URL generation failed (None returned). Running without proxy.")
        else:
            print("[DEBUG] No proxy configuration provided.")

        print("Launching Chrome...")
        try:
             service = Service(ChromeDriverManager().install())
             driver = webdriver.Chrome(service=service, options=chrome_options)
        except:
             driver = webdriver.Chrome(options=chrome_options)

        client = TMSClient(driver)
        
        try:
            # 3. Login
            login_url = tms_website_url
            success = perform_login(driver, tms_login_id, tms_password, gemini_api_key, login_url)
            
            if not success:
                await Actor.fail(status_message="Login Failed")
                return

            # 4. Perform Action
            result_data = {}
            
            if action == "EXTRACT_TRADEBOOK":
                data = client.extract_tradebook(months=history_months)
                result_data = {"tradebook": data}
                print(f"Extracted {len(data)} rows.")
                
            elif action == "BUY":
                symbol = order_details.get('symbol')
                qty = order_details.get('quantity')
                price = order_details.get('price')
                res = client.place_order("BUY", symbol, qty, price)
                result_data = res
                
            elif action == "SELL":
                symbol = order_details.get('symbol')
                qty = order_details.get('quantity')
                price = order_details.get('price')
                res = client.place_order("SELL", symbol, qty, price)
                result_data = res
                
            elif action == "EXTRACT_INFO":
                # For now same as tradebook, or add more
                data = client.extract_tradebook()
                result_data = {"info": data}
            
            # 5. Push Data
            await Actor.push_data(result_data)
            print("Data pushed to dataset.")

        except Exception as e:
            print(f"Actor execution failed: {e}")
            await Actor.fail(status_message=str(e))
        finally:
            driver.quit()

if __name__ == '__main__':
    # Need to run async
    asyncio.run(main())
