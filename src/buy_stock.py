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
        # 1. Select Instrument
        # Analyzed HTML shows it is a native <select> with formcontrolname='instType'
        print(f"[DEBUG] Selecting Instrument: {instrument}")
        try:
             # 1. Select Instrument
             # Confirmed: Native select with formcontrolname='instType'
             print(f"[DEBUG] Selecting Instrument: {instrument}")
             await page.select_option("select[formcontrolname='instType']", label=instrument)
        except Exception as inst_err:
             print(f"[DEBUG] Instrument selection failed: {inst_err}")
             # Backup: try by value
             try:
                 await page.select_option("select[formcontrolname='instType']", value=instrument)
             except: pass

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
        # Confirmed Selector: input[formcontrolname='symbol']
        await page.click("input[formcontrolname='symbol']")
        await page.fill("input[formcontrolname='symbol']", symbol)
        await page.keyboard.press("Tab") 
        await page.wait_for_timeout(1500) 
        await page.keyboard.press("Enter")
        
        # 4. Enter Quantity
        print(f"[DEBUG] Entering Quantity: {quantity}")
        await page.fill("input[formcontrolname='quantity']", str(quantity))

        # 5. Enter Price
        print(f"[DEBUG] Entering Price: {price}")
        await page.fill("input[formcontrolname='price']", str(price))
        
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
            
            # --- 8. EXTRACT ON-PAGE ORDER BOOK (With Refresh & Actions) ---
            print("[DEBUG] Refreshing On-Page Order Book...")
            try:
                # 1. Click Refresh Button
                # Selector strategy: Look for 'refresh' icon (.nf-refresh) confirmed from dump
                refresh_btn = page.locator(".nf-refresh, button:has(.nf-refresh), .icon-refresh").last
                if await refresh_btn.is_visible():
                    await refresh_btn.click()
                    await page.wait_for_timeout(1500) # Wait for reload
                else:
                    print("[DEBUG] Refresh button not found, scraping current state.")

                # 2. Scrape Table with Actions
                rows = page.locator(".table tbody tr")
                count = await rows.count()
                order_book_entries = []
                
                print(f"[DEBUG] Found {count} rows in Order Book.")
                
                for i in range(min(count, 10)): # Check top 10
                    row = rows.nth(i)
                    row_text = await row.inner_text()
                    
                    if "No records available" in row_text:
                        break
                    
                    # Extract Data Columns (naive split or cell-by-cell)
                    cells = row.locator("td")
                    cell_count = await cells.count()
                    row_data = []
                    action_links = []
                    
                    for j in range(cell_count):
                        cell = cells.nth(j)
                        text = (await cell.inner_text()).strip()
                        row_data.append(text)
                        
                        # Check for Action Links/Buttons in any cell (usually the last or first)
                        # Look for <a> or <button>
                        links = cell.locator("a, button")
                        if await links.count() > 0:
                            for k in range(await links.count()):
                                link = links.nth(k)
                                # Get link info (href, title, or icon class)
                                href = await link.get_attribute("href")
                                title = await link.get_attribute("title")
                                if href and href != "#":
                                    action_links.append(f"Link: {href}")
                                elif title:
                                    action_links.append(f"Action: {title}")
                    
                    entry = {
                        "row_text": " | ".join(row_data),
                        "actions": action_links
                    }
                    order_book_entries.append(entry)
                
                result["orderBook"] = order_book_entries
                print(f"[DEBUG] Extracted {len(order_book_entries)} entries.")
                
            except Exception as e:
                print(f"[DEBUG] Order Book extraction failed: {e}")
            
    except Exception as e:
        print(f"[DEBUG] Error placing order: {e}")
        result["message"] = str(e)
        result["status"] = "EXCEPTION"
        
    return result
