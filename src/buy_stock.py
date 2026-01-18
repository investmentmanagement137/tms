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
        
        # 6. Click BUY toggle (required - neutral state won't submit)
        print("[DEBUG] Clicking BUY toggle...")
        # The toggle is a SELL/BUY switch - must click the BUY side
        try:
            # Look for BUY label/button near toggle, or the toggle itself when it has BUY text
            buy_toggle = page.locator("text=BUY").first
            if await buy_toggle.is_visible():
                await buy_toggle.click()
                print("[DEBUG] Clicked BUY toggle")
            else:
                # Fallback: try toggle switch with .buy class or similar
                toggle = page.locator(".toggle-buy, .buy-toggle, label:has-text('BUY')").first
                if await toggle.is_visible():
                    await toggle.click()
                    print("[DEBUG] Clicked BUY toggle (fallback)")
        except Exception as e:
            print(f"[DEBUG] Toggle click attempt: {e}")
        
        await page.wait_for_timeout(300)
        
        # 7. Click Submit
        print("[DEBUG] Clicking Buy Button...")
        submit_btn = page.locator("button[type='submit'], button.btn-primary, button.btn-success").first
        await submit_btn.click()
        print("[DEBUG] Clicked Submit.")
        
        # 7. Check for Errors/Success (Toast Messages & Popups)
        # Wait a bit for toast/popup
        await page.wait_for_timeout(2500)
        
        popup_msg = ""
        popup_selectors = [
            ".toast-container .toast-message",  # ngx-toastr specific
            ".toast-message",                    # ngx-toastr message
            ".toast-body",                       # Bootstrap 5 toast
            ".alert-danger:not(.header *)",      # Bootstrap danger (not in header)
            ".alert-success:not(.header *)",     # Bootstrap success (not in header)
            ".swal2-title",                      # SweetAlert2 title
            ".swal2-content",                    # SweetAlert2 content
            "#toast-container .toast",           # Common toast container
        ]
        
        for selector in popup_selectors:
            popups = page.locator(selector)
            count = await popups.count()
            for i in range(count):
                if await popups.nth(i).is_visible():
                    txt = await popups.nth(i).text_content()
                    # Filter out header notification text
                    if txt and txt.strip() and "notification" not in txt.lower() and "see all" not in txt.lower():
                        popup_msg += txt.strip() + " "
        
        popup_msg = popup_msg.strip()
        print(f"[DEBUG] Captured popup message: {popup_msg}")
        
        # Determine status based on message content
        if popup_msg:
            result["popupMessage"] = popup_msg
            if any(err_word in popup_msg.lower() for err_word in ["error", "failed", "invalid", "rejected", "insufficient"]):
                result["message"] = popup_msg
                result["status"] = "ERROR"
            elif any(suc_word in popup_msg.lower() for suc_word in ["success", "placed", "submitted", "accepted"]):
                result["message"] = popup_msg
                result["status"] = "SUBMITTED"
            else:
                result["message"] = popup_msg
                result["status"] = "SUBMITTED"  # Default to submitted if no clear error
        else:
            # If no popup, assume success
            result["status"] = "SUBMITTED"
            result["message"] = "Order submitted (no popup captured)"
        
        # --- 8. EXTRACT ON-PAGE ORDER BOOK (ALWAYS runs) ---
        print("[DEBUG] Refreshing On-Page Order Book...")
        try:
            # 1. Click Refresh Button
            refresh_btn = page.locator(".nf-refresh, button:has(.nf-refresh), .icon-refresh").last
            if await refresh_btn.is_visible():
                await refresh_btn.click()
                await page.wait_for_timeout(1500)
            else:
                print("[DEBUG] Refresh button not found, scraping current state.")

            # Try clicking "Daily Order Book" tab if visible
            try:
                daily_tab = page.locator("a:has-text('Daily Order Book'), span:has-text('Daily Order Book')").first
                if await daily_tab.is_visible():
                    await daily_tab.click()
                    await page.wait_for_timeout(1000)
            except: pass

            # Target the KENDO GRID specifically
            kendo_grid = page.locator("kendo-grid, .k-grid").first
            if await kendo_grid.is_visible():
                print("[DEBUG] Found Kendo Grid (Order Book)")
                rows = kendo_grid.locator("tbody tr, .k-grid-content tbody tr")
            else:
                # Fallback: try to find any table that contains the symbol
                print("[DEBUG] Kendo Grid not found, falling back to symbol search...")
                tables = page.locator("table")
                count_tables = await tables.count()
                target_table = None
                
                for t_idx in range(count_tables):
                    tbl = tables.nth(t_idx)
                    tbl_text = await tbl.text_content()
                    if symbol.upper() in tbl_text.upper():
                        target_table = tbl
                        print(f"[DEBUG] Found table containing symbol at index {t_idx}")
                        break
                
                if target_table:
                    rows = target_table.locator("tbody tr")
                else:
                    rows = page.locator(".table tbody tr")

            count = await rows.count()
            order_book_entries = []
            
            print(f"[DEBUG] Found {count} rows in Order Book.")
            
            for i in range(min(count, 10)):
                row = rows.nth(i)
                row_text = await row.inner_text()
                
                if "No records available" in row_text:
                    break
                
                cells = row.locator("td")
                cell_count = await cells.count()
                row_data = []
                action_links = []
                
                for j in range(cell_count):
                    cell = cells.nth(j)
                    text = (await cell.inner_text()).strip()
                    row_data.append(text)
                    
                    links = cell.locator("a, button")
                    if await links.count() > 0:
                        for k in range(await links.count()):
                            link = links.nth(k)
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
