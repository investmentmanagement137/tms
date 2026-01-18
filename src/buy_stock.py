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
                print("[DEBUG] Clicked Buy tab via xpath")
            else:
                await page.click(".btn-buy, .buy-tab")
                print("[DEBUG] Clicked Buy tab via fallback selector")
        except Exception as e:
            print(f"[DEBUG] Buy tab selection exception (ignoring): {e}")

        print("[DEBUG] Proceeding to fill order form...")
        
        # 3. Enter Symbol
        print(f"[DEBUG] Step 3: Entering Symbol: {symbol}")
        symbol_input = page.locator("input[formcontrolname='symbol']")
        if await symbol_input.is_visible():
            print("[DEBUG] Symbol input FOUND and VISIBLE")
            await symbol_input.click()
            await symbol_input.fill(symbol)
            print(f"[DEBUG] Symbol filled: {symbol}")
        else:
            print("[DEBUG] WARNING: Symbol input NOT VISIBLE!")
        await page.keyboard.press("Tab") 
        await page.wait_for_timeout(1500) 
        await page.keyboard.press("Enter")
        print("[DEBUG] Symbol entry complete (Tab + Enter pressed)")
        
        # 4. Enter Quantity
        print(f"[DEBUG] Step 4: Entering Quantity: {quantity}")
        qty_input = page.locator("input[formcontrolname='quantity']")
        if await qty_input.is_visible():
            print("[DEBUG] Quantity input FOUND and VISIBLE")
            await qty_input.fill(str(quantity))
            print(f"[DEBUG] Quantity filled: {quantity}")
        else:
            print("[DEBUG] WARNING: Quantity input NOT VISIBLE!")

        # 5. Enter Price
        print(f"[DEBUG] Step 5: Entering Price: {price}")
        price_input = page.locator("input[formcontrolname='price']")
        if await price_input.is_visible():
            print("[DEBUG] Price input FOUND and VISIBLE")
            await price_input.fill(str(price))
            print(f"[DEBUG] Price filled: {price}")
        else:
            print("[DEBUG] WARNING: Price input NOT VISIBLE!")
        
        await page.wait_for_timeout(500)
        
        # 6. Click BUY toggle (required - neutral state won't submit)
        print("[DEBUG] Step 6: Looking for BUY toggle...")
        
        # Try multiple selectors for the toggle
        toggle_selectors = [
            "text=BUY",
            "span:text('BUY')",
            ".buy-label",
            "label:has-text('BUY')",
            ".toggle-right",
            ".slider:has-text('BUY')",
            "[class*='buy']",
        ]
        
        toggle_clicked = False
        for sel in toggle_selectors:
            try:
                toggle = page.locator(sel).first
                if await toggle.is_visible():
                    await toggle.click()
                    toggle_clicked = True
                    print(f"[DEBUG] BUY toggle clicked using selector: {sel}")
                    break
            except:
                pass
        
        if not toggle_clicked:
            print("[DEBUG] WARNING: Could not find BUY toggle with any selector!")
            # Dump page HTML for debugging
            try:
                html = await page.content()
                with open("order_entry_debug.html", "w", encoding="utf-8") as f:
                    f.write(html)
                print("[DEBUG] Page HTML saved to order_entry_debug.html for analysis")
            except:
                pass
        
        await page.wait_for_timeout(500)
        
        # 7. Click Submit
        print("[DEBUG] Step 7: Looking for Submit button...")
        submit_selectors = [
            "button[type='submit']",
            "button.btn-primary",
            "button.btn-success",
            "button:has-text('Submit')",
            "button:has-text('Place Order')",
            "button:has-text('Buy')",
        ]
        
        submit_clicked = False
        for sel in submit_selectors:
            try:
                btn = page.locator(sel).first
                if await btn.is_visible():
                    btn_text = await btn.text_content()
                    print(f"[DEBUG] Found submit button with selector '{sel}', text: '{btn_text}'")
                    await btn.click()
                    submit_clicked = True
                    print(f"[DEBUG] Submit button clicked using selector: {sel}")
                    break
            except Exception as e:
                print(f"[DEBUG] Selector '{sel}' failed: {e}")
        
        if not submit_clicked:
            print("[DEBUG] ERROR: Could not click any submit button!")
        else:
            print("[DEBUG] Submit button CLICKED successfully.")
        
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
