"""
Apify Actor entry point for TMS Order Executor (Playwright Version)
"""
import os
import datetime
import json
import time
from apify import Actor
from playwright.async_api import async_playwright

# Import modular scripts
from src import utils, login, buy_stock, sell_stock, daily_history, dashboard


async def main():
    async with Actor:
        # Get input from Apify
        actor_input = await Actor.get_input() or {}
        
        # Extract inputs
        tms_username = actor_input.get('tmsUsername')
        tms_password = actor_input.get('tmsPassword')
        gemini_api_key = actor_input.get('geminiApiKey')
        tms_url = actor_input.get('tmsUrl')
        
        # Sanitize tmsUrl
        if tms_url:
            tms_url = tms_url.strip().rstrip('/')
            if tms_url.endswith('/login'):
                tms_url = tms_url[:-6]
            tms_url = tms_url.rstrip('/')

        action = actor_input.get('action', 'BATCH') # Default to safer option
        
        # Validate Credentials
        if not all([tms_username, tms_password, gemini_api_key, tms_url]):
            await Actor.fail(status_message='Missing required credentials: tmsUsername, tmsPassword, geminiApiKey, or tmsUrl')
            return

        Actor.log.info(f'Starting TMS Actor: Action = {action} on {tms_url}')
        
        # --- Versioning ---
        try:
            with open('VERSION', 'r') as vf:
                VERSION = vf.read().strip()
        except:
            VERSION = "1.2.0" # Bumped for Playwright
            
        Actor.log.info(f"TMS Actor Version: {VERSION}")
        
        # Launch Playwright Browser
        Actor.log.info('Launching Playwright browser...')
        
        # Use simple async_playwright manager
        async with async_playwright() as p:
            # Launch browser with Stealth Args
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox', 
                    '--disable-setuid-sandbox',
                    '--disable-blink-features=AutomationControlled', # Key for evasion
                    '--disable-infobars',
                    '--window-size=1920,1080',
                ]
            )
            
            # Create Context with User Agent (and optional storage state)
            
            # Create Context with User Agent (and optional storage state)
            
            # 1. Try to load session from NAMED Key-Value Store (Shared across runs)
            # We use a named store 'tms-sessions' so it persists!
            session_store = await Actor.open_key_value_store(name='tms-sessions')
            session_state = await session_store.get_value('SESSION')
            
            if session_state:
                Actor.log.info("Found saved session in 'tms-sessions' store. Loading...")
            else:
                Actor.log.info("No saved session found in 'tms-sessions' store.")
                
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                storage_state=session_state if session_state else None
            )
            
            # Stealth Script: Hide webdriver property
            await context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            page = await context.new_page()
            
            try:
                # 2. Check if Session is Valid (Skip Login?)
                is_logged_in = False
                if session_state:
                     Actor.log.info("Verifying saved session...")
                     try:
                        # Go to a secured page (Dashboard)
                        await page.goto(f"{tms_url}/tms/m/dashboard", wait_until='networkidle', timeout=15000)
                        if "login" not in page.url and ("dashboard" in page.url or "tms" in page.url):
                            Actor.log.info("Session is VALID! Skipping login.")
                            is_logged_in = True
                        else:
                            Actor.log.warning("Saved session expired or invalid.")
                     except:
                        Actor.log.warning("Session verification failed (timeout).")
                        # DO NOT return, just mark as not logged in.
                        is_logged_in = False
                        # If the page failed to load or got stuck, let's close context and retry clean
                        # But simplest is to just proceed to login logic.
                
                # 3. Perform Login (if not logged in)
                if not is_logged_in:
                    # Clear cookies if session failed validation to avoid weird states
                    if session_state:
                         Actor.log.info("Clearing invalid session state before re-login...")
                         await context.clear_cookies()
                    
                    Actor.log.info('Executing Login Script...')
                    success = await login.login(page, tms_username, tms_password, gemini_api_key, tms_url)
                    
                    if not success:
                        await Actor.fail(status_message='Login failed')
                        return
                    
                    Actor.log.info('Login successful!')
                    
                    # 4. Save New Session to NAMED Store
                    Actor.log.info("Saving session state to 'tms-sessions'...")
                    storage_state = await context.storage_state()
                    await session_store.set_value('SESSION', storage_state)
                
                # 5. Initialize Output Dict
                final_output = {
                    "version": VERSION,
                    "status": "SUCCESS",
                    "timestamp": str(datetime.datetime.now()),
                    "batch_results": []
                }

                # 6. Extract Dashboard Data (Collateral, Limits)
                # We are logged in now (either via session or fresh login)
                Actor.log.info("Extracting Dashboard Data...")
                try:
                    # Ensure we are on dashboard or navigate there?
                    # extract_dashboard_data runs on current page
                    dash_data = await dashboard.extract_dashboard_data(page)
                    final_output["dashboard"] = dash_data
                    Actor.log.info("Dashboard data extracted.")
                except Exception as e:
                     Actor.log.warning(f"Dashboard extraction failed: {e}")

                # Check for Batch Orders / BATCH action
                batch_orders = actor_input.get('orders', [])
                check_orders_flag = actor_input.get('checkOrders', True)
                
                executed_any_order = False

                if (action == 'BATCH' or (batch_orders and len(batch_orders) > 0)):
                    if not batch_orders:
                        Actor.log.warning('Action is BATCH but "orders" list is empty! Nothing to do.')
                        Actor.log.info('✅ Workflow Completed (No Orders Executed)')
                        await Actor.exit()
                        return

                    Actor.log.info(f"Processing Batch of {len(batch_orders)} orders...")
                    
                    for order in batch_orders:
                        o_symbol = str(order.get('symbol')).strip().upper()
                        o_qty = int(order.get('qty', 0))
                        o_price = float(order.get('price', 0))
                        o_side = str(order.get('side')).upper() # BUY or SELL
                        o_instrument = str(order.get('instrument', 'EQ')).strip().upper()
                        
                        Actor.log.info(f"Batch Processing: {o_side} {o_symbol} x {o_qty} @ {o_price} ({o_instrument})")
                        
                        res = {}
                        if o_side == 'BUY':
                            res = await buy_stock.execute(page, tms_url, o_symbol, o_qty, o_price, o_instrument)
                        elif o_side == 'SELL':
                            res = await sell_stock.execute(page, tms_url, o_symbol, o_qty, o_price, o_instrument)
                        else:
                            res = {"status": "SKIPPED", "message": f"Invalid side: {o_side}"}
                            
                        final_output["batch_results"].append(res)
                        executed_any_order = True
                        await page.wait_for_timeout(1000) # 1 sec pause

                else:
                    # Fallback to Single Action Logic
                    symbol = actor_input.get('symbol')
                    price = actor_input.get('price')
                    quantity = actor_input.get('quantity')
                    
                    if action == 'BUY':
                        if all([symbol, price, quantity]):
                            Actor.log.info('Executing Single BUY...')
                            order_result = await buy_stock.execute(page, tms_url, str(symbol).strip().upper(), int(quantity), float(price))
                            final_output["batch_results"].append(order_result)
                            executed_any_order = True
                        else:
                            Actor.log.warning("Skipping BUY: Missing symbol, price, or quantity.")
                    
                    elif action == 'SELL':
                        if all([symbol, price, quantity]):
                            Actor.log.info('Executing Single SELL...')
                            order_result = await sell_stock.execute(page, tms_url, str(symbol).strip().upper(), int(quantity), float(price))
                            final_output["batch_results"].append(order_result)
                            executed_any_order = True
                        else:
                            Actor.log.warning("Skipping SELL: Missing symbol, price, or quantity.")

                # Global Verification
                if (executed_any_order and check_orders_flag) or action == 'CHECK_ORDERS':
                     Actor.log.info('Executing Daily History Script (Verification)...')
                     orders = await daily_history.extract(page, tms_url)
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
                
                Actor.log.info('✅ Workflow Completed Successfully!')
                await Actor.exit() # Explicitly exit with success code 0
                
            except Exception as e:
                Actor.log.error(f'Error during execution: {e}')
                import traceback
                Actor.log.error(traceback.format_exc())
                await Actor.fail(status_message=str(e))
                
            finally:
                await browser.close()
                Actor.log.info('Browser closed')

if __name__ == '__main__':
    # Apify SDK automatically manages the loop if we use Actor.main() but we are using asyncio.run(main())
    import asyncio
    asyncio.run(main())
