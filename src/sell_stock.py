import asyncio

async def execute(page, tms_url, symbol, quantity, price, instrument="EQ"):
    """
    Places a SELL order using Playwright.
    Returns result dictionary.
    """
    print(f"\n[DEBUG] Placing SELL Order: {symbol}, Qty: {quantity}, Price: {price}")
    
    # Construct paths using base URL
    base_url = tms_url.rstrip('/')
    order_url = f"{base_url}/tms/me/memberclientorderentry"
    
    print(f"[DEBUG] Navigating to Order Entry: {order_url}")
    await page.goto(order_url, wait_until='networkidle')
    
    result = {
        "status": "FAILED",
        "message": "",
        "sellEntryUrl": order_url,
        "orderDetails": {
            "symbol": symbol,
            "quantity": quantity,
            "price": price,
            "action": "SELL"
        }
    }
    
    try:
        # === CORRECT ORDER: Instrument -> Toggle -> Form Fields ===
        
        # 1. Select Instrument Type FIRST
        print(f"[DEBUG] Step 1: Selecting Instrument: {instrument}")
        instrument_selected = False
        try:
            # Try standard Playwright selection first
            inst_selector = "select.form-inst, select[formcontrolname='instType']"
            try:
                await page.wait_for_selector(inst_selector, state="visible", timeout=5000)
                inst_select = page.locator(inst_selector).first
                await inst_select.select_option(label=instrument)
                print(f"[DEBUG] Instrument selected via UI: {instrument}")
                instrument_selected = True
            except Exception as e:
                print(f"[DEBUG] UI selection timed out/failed: {e}")
            
            # Fallback: JavaScript direct injection (Force for Angular)
            if not instrument_selected:
                print("[DEBUG] Attempting JS fallback for Instrument...")
                found = await page.evaluate(f"""() => {{
                    const select = document.querySelector("{inst_selector}");
                    if (!select) return false;
                    
                    // Try to find the option by text
                    for (let i = 0; i < select.options.length; i++) {{
                        if (select.options[i].text === "{instrument}") {{
                            select.selectedIndex = i;
                            select.value = select.options[i].value;
                            select.dispatchEvent(new Event('change', {{ bubbles: true }}));
                            select.dispatchEvent(new Event('input', {{ bubbles: true }}));
                            return true;
                        }}
                    }}
                    return false;
                }}""")
                
                if found:
                    print(f"[DEBUG] Instrument selected via JS: {instrument}")
                    instrument_selected = True
                else:
                    print("[DEBUG] CRITICAL WARNING: Could not select instrument via JS either!")

        except Exception as inst_err:
            print(f"[DEBUG] Instrument selection completely failed: {inst_err}")
        
        await page.wait_for_timeout(300)

        # 2. Click SELL toggle
        print("[DEBUG] Step 2: Clicking SELL toggle...")
        sell_toggle = page.locator(".order__options--sell")
        if await sell_toggle.is_visible():
            await sell_toggle.click()
            print("[DEBUG] SELL toggle clicked")
        else:
            await page.locator("text=SELL").first.click()
            print("[DEBUG] SELL toggle clicked via text=SELL")
        
        await page.wait_for_timeout(300)
        
        # 3. Enter Symbol (CRITICAL: Must click from typeahead dropdown!)
        print(f"[DEBUG] Step 3: Entering Symbol: {symbol}")
        
        symbol_input = page.locator("input[formcontrolname='symbol']").first
        
        if await symbol_input.is_visible():
            await symbol_input.click()
            await symbol_input.fill("")
            await symbol_input.type(symbol, delay=100)
            print(f"[DEBUG] Symbol typed: {symbol}")
            
            await page.wait_for_timeout(1500)
            
            dropdown_selectors = [
                f".dropdown-menu li a:has-text('{symbol}')",
                ".dropdown-menu li a",
                ".typeahead-item",
                f"li:has-text('{symbol}') a",
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
        qty_input = page.locator("input.form-qty")
        if await qty_input.is_visible():
            await qty_input.fill(str(quantity))
            print(f"[DEBUG] Quantity filled: {quantity}")
        else:
            await page.fill("input[formcontrolname='quantity']", str(quantity))

        # 5. Enter Price
        print(f"[DEBUG] Step 5: Entering Price: {price}")
        price_input = page.locator("input.form-price")
        if await price_input.is_visible():
            await price_input.fill(str(price))
            print(f"[DEBUG] Price filled: {price}")
        else:
            await page.fill("input[formcontrolname='price']", str(price))
        
        await page.wait_for_timeout(500)
        
        # 6. Click Submit Button
        print("[DEBUG] Step 6: Looking for Submit button...")
        # Submit button is the button before CANCEL button (.btn-default.btn-sm)
        # It should say "SELL" and be enabled
        submit_btn = page.locator("button.btn-sm:not(.btn-default), button.btn-primary:has-text('SELL')").first
        
        # Wait a moment for button state to update
        await page.wait_for_timeout(500)
        
        submit_clicked = False
        if await submit_btn.is_visible():
            btn_text = (await submit_btn.text_content()).strip()
            is_disabled = await submit_btn.is_disabled()
            
            print(f"[DEBUG] Found submit button: Text='{btn_text}', Disabled={is_disabled}")
            
            if not is_disabled and "SELL" in btn_text.upper():
                await submit_btn.click()
                print("[DEBUG] Submit button clicked")
                submit_clicked = True
            else:
                print(f"[DEBUG] Submit button is not ready (Text: {btn_text}, Disabled: {is_disabled})")
                
                # Try to force update by focusing fields
                print("[DEBUG] Attempting to refresh form state...")
                await page.locator("input[formcontrolname='price']").first.click()
                await page.keyboard.press("Tab")
                await page.wait_for_timeout(500)
                
                # Check again
                if not await submit_btn.is_disabled():
                    await submit_btn.click()
                    print("[DEBUG] Submit button clicked after refresh")
                    submit_clicked = True
        else:
             print("[DEBUG] Submit button not found")
             submit_clicked = False
        
        # 7. Check for Errors/Success (Toast Messages & Popups)
        await page.wait_for_timeout(2500)
        
        popup_msg = ""
        popup_selectors = [
            ".toast-container .toast-message", ".toast-message", ".toast-body",
            ".alert-danger:not(.header *)", ".alert-success:not(.header *)",
            ".swal2-title", ".swal2-content", "#toast-container .toast",
        ]
        
        for selector in popup_selectors:
            popups = page.locator(selector)
            count = await popups.count()
            for i in range(count):
                if await popups.nth(i).is_visible():
                    txt = await popups.nth(i).text_content()
                    if txt and txt.strip() and "notification" not in txt.lower() and "see all" not in txt.lower():
                        popup_msg += txt.strip() + " "
        
        popup_msg = popup_msg.strip()
        print(f"[DEBUG] Captured popup message: {popup_msg}")
        
        if popup_msg:
            result["popupMessage"] = popup_msg
            if any(err in popup_msg.lower() for err in ["error", "failed", "invalid", "rejected", "insufficient"]):
                result["message"] = popup_msg
                result["status"] = "ERROR"
            elif any(suc in popup_msg.lower() for suc in ["success", "placed", "submitted", "accepted"]):
                result["message"] = popup_msg
                result["status"] = "SUBMITTED"
            else:
                result["message"] = popup_msg
                result["status"] = "SUBMITTED"
        else:
            result["status"] = "SUBMITTED"
            result["message"] = "Order submitted (no popup captured)"
        
        # --- 8. EXTRACT ON-PAGE ORDER BOOK (ALWAYS runs) ---
        print("[DEBUG] Refreshing On-Page Order Book...")
        try:
            # 1. Click Refresh Button
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
                await page.wait_for_timeout(2000)
            else:
                print("[DEBUG] Refresh button not found")

            # 2. Target the Kendo Grid
            kendo_grid = page.locator("kendo-grid, .k-grid").first
            if await kendo_grid.is_visible():
                print("[DEBUG] Found Kendo Grid (Order Book)")
                rows = kendo_grid.locator("tbody tr[role='row'], .k-grid-content tbody tr")
            else:
                print("[DEBUG] Kendo Grid not found, using fallback")
                rows = page.locator("table tbody tr")

            count = await rows.count()
            order_book_entries = []
            
            for i in range(min(count, 15)):
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
                    
                    # Check for action buttons
                    edit_btn = cell.locator("span.table--edit, .table--edit")
                    cancel_btn = cell.locator("span.table--deactivate, .table--deactivate")
                    
                    if await edit_btn.count() > 0:
                        edit_title = await edit_btn.first.get_attribute("title") or "Edit"
                        actions.append({
                            "type": "EDIT",
                            "title": edit_title,
                            "selector": "span.table--edit"
                        })
                    
                    if await cancel_btn.count() > 0:
                        cancel_title = await cancel_btn.first.get_attribute("title") or "Cancel"
                        actions.append({
                            "type": "CANCEL", 
                            "title": cancel_title,
                            "selector": "span.table--deactivate"
                        })
                
                entry = {
                    "rowIndex": i,
                    "rowText": " | ".join(row_data),
                    "actions": actions
                }
                
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
            print(f"[DEBUG] Order book check failed: {e}")
            
    except Exception as e:
        print(f"[DEBUG] Error placing order: {e}")
        result["message"] = str(e)
        result["status"] = "EXCEPTION"
        
    return result
