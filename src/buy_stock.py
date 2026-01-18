import asyncio

async def execute(page, tms_url, symbol, quantity, price, instrument="EQ"):
    """
    Places a BUY order using Playwright.
    Returns result dictionary.
    """
    print(f"\n[DEBUG] Placing BUY Order: {symbol}, Qty: {quantity}, Price: {price}")
    
    # Construct paths using base URL
    base_url = tms_url.rstrip('/')
    order_url = f"{base_url}/tms/me/memberclientorderentry"
    
    # Handle Alerts (e.g., "Order Placed Successfully" or Errors)
    # We set up the listener BEFORE action
    # But Playwright dialogs are auto-handling? No, default is dismiss.
    # We want to accept them and log.
    async def handle_dialog(dialog):
        print(f"[DEBUG] Dialog: {dialog.message}")
        await dialog.accept()
    
    # Remove any existing listeners to avoid dupes if reused? Simple script, likely fine.
    # page.on("dialog", handle_dialog) # We can attach locally, but page is shared.
    # Better to attach once in main or here. Let's attach here but be careful.
    
    print(f"[DEBUG] Navigating to Order Entry: {order_url}")
    await page.goto(order_url, wait_until='networkidle')
    
    result = {
        "status": "FAILED",
        "message": "",
        "buyEntryUrl": order_url,
        "orderDetails": {
            "symbol": symbol,
            "quantity": quantity,
            "price": price,
            "action": "BUY"
        }
    }
    
    try:
        # 1. Select Instrument (New)
        print(f"[DEBUG] Selecting Instrument: {instrument}")
        try:
             # It might be a select or a custom dropdown. 
             # Based on screenshot, it looks like a select or div dropdown.
             # We try generic selector first.
             await page.select_option("select[name='instrument'], select.form-control", label=instrument)
        except:
             # Fallback if it's not a native select (e.g. Angular/Kendo dropdown)
             # Clicking dropdown trigger then option
             print("[DEBUG] Native select failed, trying custom dropdown...")
             try:
                 # This selector needs to be generic enough or use text
                 await page.click("text='INST' >> .. >> .ng-select-container, .ng-select")
                 await page.click(f"div.ng-option:has-text('{instrument}')")
             except Exception as ex:
                 print(f"[DEBUG] Instrument selection failed (ignoring, simplified mode): {ex}")

        # 2. Select Buy Tab (if not already selected)
        # Try finding a tab with text "Buy" or class .btn-buy
        try:
            buy_tab = page.locator("xpath=//a[contains(text(), 'Buy')]").first
            if await buy_tab.is_visible():
                await buy_tab.click()
            else:
                # Fallback
                await page.click(".btn-buy, .buy-tab")
        except:
             # Maybe already on Buy? Or structured differently. Proceed.
             print("[DEBUG] Buy tab selection exception (ignoring)")

        print("[DEBUG] Selected BUY tab")
        
        # 3. Enter Symbol
        print(f"[DEBUG] Entering Symbol: {symbol}")
        # In Playwright, we can wait for selector
        # Sometimes clearing is needed
        symbol_input = page.locator("input[placeholder='Symbol'], input[name='symbol']").first
        await symbol_input.click()
        await symbol_input.fill(symbol)
        await page.keyboard.press("Tab") # Trigger autocomplete
        await page.wait_for_timeout(1000) # Wait for dropdown/fetch

        # 4. Enter Quantity
        print(f"[DEBUG] Entering Quantity: {quantity}")
        await page.fill("input[placeholder='Qty'], input[name='quantity']", str(quantity))

        # 5. Enter Price
        print(f"[DEBUG] Entering Price: {price}")
        await page.fill("input[placeholder='Price'], input[name='price']", str(price))
        
        await page.wait_for_timeout(500)
        
        # 6. Click Submit
        print("[DEBUG] Clicking Buy Button...")
        # Locating the primary submit button
        # Usually type=submit or class btn-primary
        submit_btn = page.locator("button[type='submit'], button.btn-primary, button.btn-success").first
        await submit_btn.click()
        print("[DEBUG] Clicked Submit.")
        
        # 7. Check for Errors/Success (Toast Messages)
        # Wait a bit for toast
        await page.wait_for_timeout(2000)
        
        error_msg = ""
        # Check toast or alert box
        toasts = page.locator(".toast-message, .alert-danger")
        count = await toasts.count()
        if count > 0:
            for i in range(count):
                if await toasts.nth(i).is_visible():
                    txt = await toasts.nth(i).text_content()
                    error_msg += txt + " "
        
        if error_msg and "success" not in error_msg.lower():
            print(f"[DEBUG] Order Error: {error_msg}")
            result["message"] = f"Error: {error_msg}"
            result["status"] = "ERROR"
        else:
            # If no error, assume success 
            print("[DEBUG] Order Submitted.")
            result["status"] = "SUBMITTED"
            result["message"] = "Order submitted successfully"
            
            # --- 8. EXTRACT ON-PAGE ORDER BOOK ---
            print("[DEBUG] Extracting On-Page Order Book...")
            try:
                # Locate table rows
                rows = page.locator(".table tbody tr")
                count = await rows.count()
                order_book_entries = []
                
                # We grab the first few rows (pagination handling needed? Usually latest is first)
                # User mentioned pagination - usually Kendo grid or standard pagination
                # For immediate verification, top rows are enough.
                for i in range(min(count, 5)): 
                    row_text = await rows.nth(i).inner_text()
                    if "No records available" in row_text:
                        break
                    order_book_entries.append(row_text.replace('\n', ' | '))
                
                result["orderBook"] = order_book_entries
                print(f"[DEBUG] Found {len(order_book_entries)} order entries.")
                
            except Exception as e:
                print(f"[DEBUG] Order Book extraction failed: {e}")
            
    except Exception as e:
        print(f"[DEBUG] Error placing order: {e}")
        result["message"] = str(e)
        result["status"] = "EXCEPTION"
        
    return result
