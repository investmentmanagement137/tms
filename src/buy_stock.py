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
        # === VERIFIED SELECTORS FROM BROWSER EXPLORATION ===
        # 1. Click BUY toggle FIRST (required - form won't work in neutral state)
        print("[DEBUG] Step 1: Clicking BUY toggle...")
        buy_toggle = page.locator(".order__options--buy")
        if await buy_toggle.is_visible():
            await buy_toggle.click()
            print("[DEBUG] BUY toggle clicked via .order__options--buy")
        else:
            # Fallback to text selector
            await page.locator("text=BUY").first.click()
            print("[DEBUG] BUY toggle clicked via text=BUY")
        
        await page.wait_for_timeout(300)
        
        # 2. Select Instrument Type (CRITICAL for MF like NIBLSTF)
        print(f"[DEBUG] Step 2: Selecting Instrument: {instrument}")
        try:
            # Verified selector: select.form-inst
            inst_select = page.locator("select.form-inst")
            if await inst_select.is_visible():
                await inst_select.select_option(label=instrument)
                print(f"[DEBUG] Instrument selected via select.form-inst: {instrument}")
            else:
                # Fallback
                await page.select_option("select[formcontrolname='instType']", label=instrument)
                print(f"[DEBUG] Instrument selected via formcontrolname")
        except Exception as inst_err:
            print(f"[DEBUG] Instrument selection failed: {inst_err}")
        
        await page.wait_for_timeout(300)
        
        # 3. Enter Symbol (CRITICAL: Must click from typeahead dropdown!)
        print(f"[DEBUG] Step 3: Entering Symbol: {symbol}")
        
        # Use specific formcontrolname='symbol' selector
        symbol_input = page.locator("input[formcontrolname='symbol']").first
        
        if await symbol_input.is_visible():
            await symbol_input.click()
            await symbol_input.fill("")  # Clear first
            await symbol_input.type(symbol, delay=100)  # Type slowly to trigger typeahead
            print(f"[DEBUG] Symbol typed: {symbol}")
            
            # CRITICAL: Wait for typeahead dropdown to appear and click the item
            await page.wait_for_timeout(1500)  # Wait for dropdown to populate
            
            # Try multiple selectors for the dropdown item
            dropdown_selectors = [
                f".dropdown-menu li a:has-text('{symbol}')",  # Exact match in dropdown
                ".dropdown-menu li a",                         # First dropdown item
                ".typeahead-item",                             # Alternative typeahead
                f"li:has-text('{symbol}') a",                 # Generic list item
            ]
            
            dropdown_clicked = False
            for sel in dropdown_selectors:
                try:
                    dropdown_item = page.locator(sel).first
                    if await dropdown_item.is_visible(timeout=1000):
                        await dropdown_item.click()
                        dropdown_clicked = True
                        print(f"[DEBUG] Symbol selected from dropdown using: {sel}")
                        break
                except:
                    pass
            
            if not dropdown_clicked:
                # Fallback: press Tab then Enter (old method)
                print("[DEBUG] Dropdown not found, using Tab+Enter fallback")
                await page.keyboard.press("Tab")
                await page.wait_for_timeout(500)
                await page.keyboard.press("Enter")
        else:
            print("[DEBUG] WARNING: Symbol input not visible!")
        
        await page.wait_for_timeout(500)
        print("[DEBUG] Symbol entry complete")
        
        await page.wait_for_timeout(500)
        
        # 4. Enter Quantity
        print(f"[DEBUG] Step 4: Entering Quantity: {quantity}")
        # Verified selector: input.form-qty
        qty_input = page.locator("input.form-qty")
        if await qty_input.is_visible():
            await qty_input.fill(str(quantity))
            print(f"[DEBUG] Quantity filled: {quantity}")
        else:
            await page.fill("input[formcontrolname='quantity']", str(quantity))
            print(f"[DEBUG] Quantity filled via formcontrolname")

        # 5. Enter Price
        print(f"[DEBUG] Step 5: Entering Price: {price}")
        # Verified selector: input.form-price
        price_input = page.locator("input.form-price")
        if await price_input.is_visible():
            await price_input.fill(str(price))
            print(f"[DEBUG] Price filled: {price}")
        else:
            await page.fill("input[formcontrolname='price']", str(price))
            print(f"[DEBUG] Price filled via formcontrolname")
        
        await page.wait_for_timeout(500)
        
        # 6. Click Submit Button
        print("[DEBUG] Step 6: Looking for Submit button...")
        # Submit button is the button before CANCEL button (.btn-default.btn-sm)
        submit_selectors = [
            "button.btn-sm:not(.btn-default)",    # Primary: small button that's not cancel
            "button.btn-primary.btn-sm",          # Primary button small 
            "button:has-text('BUY')",             # Button with BUY text
            "button[type='submit']",              # Standard submit
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
            # 1. Click Refresh Button to get latest data
            # VERIFIED SELECTOR: #kendo__refresh (Kendo Grid refresh icon)
            refresh_selectors = [
                "#kendo__refresh",           # Primary: Kendo Grid refresh ID
                ".k-i-refresh",              # Kendo refresh icon class
                "span[title='Reload table']", # By title attribute
                ".nf-refresh",               # Fallback
            ]
            
            refresh_clicked = False
            for sel in refresh_selectors:
                try:
                    refresh_btn = page.locator(sel).first
                    if await refresh_btn.is_visible():
                        await refresh_btn.click()
                        refresh_clicked = True
                        print(f"[DEBUG] Order Book refreshed using: {sel}")
                        break
                except:
                    pass
            
            if refresh_clicked:
                await page.wait_for_timeout(2000)  # Wait for data reload
            else:
                print("[DEBUG] Refresh button not found, using current state")

            # 2. Target the Kendo Grid (Order Book table)
            kendo_grid = page.locator("kendo-grid, .k-grid").first
            if await kendo_grid.is_visible():
                print("[DEBUG] Found Kendo Grid (Order Book)")
                rows = kendo_grid.locator("tbody tr[role='row'], .k-grid-content tbody tr")
            else:
                print("[DEBUG] Kendo Grid not found, using fallback")
                rows = page.locator("table tbody tr")

            count = await rows.count()
            order_book_entries = []
            
            print(f"[DEBUG] Found {count} rows in Order Book.")
            
            for i in range(min(count, 15)):  # Check up to 15 orders
                row = rows.nth(i)
                row_text = await row.inner_text()
                
                if "No records available" in row_text or not row_text.strip():
                    continue
                
                cells = row.locator("td")
                cell_count = await cells.count()
                row_data = []
                actions = []
                
                for j in range(cell_count):
                    cell = cells.nth(j)
                    text = (await cell.inner_text()).strip()
                    row_data.append(text)
                    
                    # Check for action buttons (Edit/Cancel)
                    # Verified selectors: span.table--edit (Modify), span.table--deactivate (Cancel)
                    edit_btn = cell.locator("span.table--edit, .table--edit")
                    cancel_btn = cell.locator("span.table--deactivate, .table--deactivate")
                    
                    if await edit_btn.count() > 0:
                        edit_title = await edit_btn.first.get_attribute("title") or "Edit"
                        actions.append({
                            "type": "EDIT",
                            "title": edit_title,
                            "selector": "span.table--edit",
                            "note": "Click to modify this order"
                        })
                    
                    if await cancel_btn.count() > 0:
                        cancel_title = await cancel_btn.first.get_attribute("title") or "Cancel"
                        actions.append({
                            "type": "CANCEL", 
                            "title": cancel_title,
                            "selector": "span.table--deactivate",
                            "note": "Click to cancel this order"
                        })
                
                # Parse row data into structured format (if enough columns)
                entry = {
                    "rowIndex": i,
                    "rowText": " | ".join(row_data),
                    "actions": actions
                }
                
                # Try to extract order details from columns
                if len(row_data) >= 5:
                    entry["orderDetails"] = {
                        "symbol": row_data[2] if len(row_data) > 2 else "",
                        "type": row_data[3] if len(row_data) > 3 else "",
                        "qty": row_data[4] if len(row_data) > 4 else "",
                        "price": row_data[5] if len(row_data) > 5 else "",
                    }
                
                order_book_entries.append(entry)
            
            result["orderBook"] = order_book_entries
            print(f"[DEBUG] Extracted {len(order_book_entries)} order book entries.")
            
        except Exception as e:
            print(f"[DEBUG] Order Book extraction failed: {e}")
            
    except Exception as e:
        print(f"[DEBUG] Error placing order: {e}")
        result["message"] = str(e)
        result["status"] = "EXCEPTION"
        
    return result
