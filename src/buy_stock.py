import asyncio
import re
from urllib.parse import urlencode
from .toast_capture import capture_all_popups, wait_for_toast, is_error_message
from .toast_capture import capture_all_popups, wait_for_toast, is_error_message
from .utils import set_toggle_position, set_symbol, wait_for_loading_screen_to_vanish


def parse_order_book_row(row_text):
    """
    Parse a tab-separated order book row into structured data.
    
    Input format: "1\t\n\tOPEN\tKSY\tBuy\t4000\t9.07\t4000\t36,280.00"
    
    Returns dict with: rowNum, status, symbol, side, quantity, price, remainingQty, totalAmount
    """
    # Split by tab and filter out empty strings and newlines
    parts = [p.strip() for p in row_text.split('\t') if p.strip() and p.strip() != '\n']
    
    if len(parts) >= 8:
        return {
            "rowNum": int(parts[0]) if parts[0].isdigit() else parts[0],
            "status": parts[1],
            "symbol": parts[2],
            "side": parts[3],
            "quantity": int(parts[4].replace(',', '')) if parts[4].replace(',', '').isdigit() else parts[4],
            "price": float(parts[5].replace(',', '')) if re.match(r'^[\d,\.]+$', parts[5]) else parts[5],
            "remainingQty": int(parts[6].replace(',', '')) if parts[6].replace(',', '').isdigit() else parts[6],
            "totalAmount": parts[7]  # Keep as string to preserve formatting
        }
    elif len(parts) >= 1:
        # Partial row, return what we have
        return {"raw": parts, "parseError": "Insufficient columns"}
    else:
        return {"raw": row_text, "parseError": "Could not parse"}


async def execute(page, tms_url, symbol, quantity, price, instrument="EQ"):
    """
    Places a BUY order using Playwright.
    
    Strategy (validated via browser testing):
    1. Navigate with ?symbol=XXX (only URL param that works natively)
    2. Use JavaScript to set Instrument, Toggle, Quantity, Price
    3. Click Submit button
    
    Returns result dictionary.
    """
    print(f"\n[DEBUG] Placing BUY Order: {symbol}, Qty: {quantity}, Price: {price}, Instrument: {instrument}")
    
    base_url = tms_url.rstrip('/')
    # Remove symbol parameter from URL for manual entry
    order_url = f"{base_url}/tms/me/memberclientorderentry"
    
    print(f"[DEBUG] Navigating to: {order_url}")
    
    result = {
        "status": "FAILED",
        "message": "",
        "buyEntryUrl": order_url,
        "orderDetails": {
            "symbol": symbol,
            "quantity": quantity,
            "price": price,
            "action": "BUY",
            "quantity": quantity,
            "price": price,
            "action": "BUY",
            "instrument": instrument
        },
        "validationStatus": "UNKNOWN", # NEW: VALIDATED / NOT_VALIDATED
        "failureType": None            # NEW: Error Code
    }
    
    try:
        # Navigate without symbol
        await page.goto(order_url, wait_until='domcontentloaded')
        # CRITICAL: Reload page to ensure fresh form state for batch orders
        await page.reload(wait_until='domcontentloaded')
        # Handle preloader if present after reload
        await wait_for_loading_screen_to_vanish(page)
        
        try:
            await page.wait_for_selector('app-three-state-toggle', timeout=20000)
        except:
            print("[DEBUG] ❌ Toggle not found even after reload")
            result["status"] = "FAILED"
            result["message"] = "Order form not loaded (Toggle missing)"
            result["failureType"] = "ORDER_FORM_NOT_LOADED"
            return result
        
        # === STEP 1: Activate BUY toggle with robust retry ===
        # Reverting to Toggle -> Instrument order to match working JS script
        print("[DEBUG] Step 1: Activating BUY toggle...")
        is_buy_active = await set_toggle_position(page, "buy")
        
        if not is_buy_active:
             print("[DEBUG] WARNING: Could not verify BUY toggle state! Proceeding anyway but order might fail.")
        else:
             print("[DEBUG] BUY toggle confirmed active")

        # === STEP 2: Set Instrument via JS (if not EQ) ===
        if instrument != "EQ":
            print(f"[DEBUG] Step 2: Setting Instrument to {instrument} via JS...")
            await page.evaluate(f"""() => {{
                const select = document.querySelector('select.form-inst, select[formcontrolname="instType"]');
                if (select) {{
                    for (let i = 0; i < select.options.length; i++) {{
                        if (select.options[i].text === "{instrument}") {{
                            select.selectedIndex = i;
                            select.value = select.options[i].value;
                            select.dispatchEvent(new Event('change', {{ bubbles: true }}));
                            select.dispatchEvent(new Event('input', {{ bubbles: true }}));
                            console.log('Instrument set to: ' + "{instrument}");
                            break;
                        }}
                    }}
                }}
            }}""")
            await page.wait_for_timeout(500)
            print(f"[DEBUG] Instrument set to: {instrument}")
        else:
            print("[DEBUG] Step 2: Instrument is EQ (default), skipping")
        
        # === STEP 3: Set Symbol (After Toggle and Instrument) ===
        print(f"[DEBUG] Step 3: Setting symbol {symbol} manually...")
        if not await set_symbol(page, symbol):
            print(f"[DEBUG] Failed to set symbol {symbol}")
            result["status"] = "FAILED"
            result["message"] = f"Failed to set symbol {symbol}"
            result["failureType"] = "SYMBOL_SEARCH_FAILED"
            return result
        
        # await page.wait_for_timeout(1000) # Removed arbitrary wait

        # === STEP 4: Set Quantity via JS ===
        print(f"[DEBUG] Step 4: Setting Quantity to {quantity} via JS...")
        await page.evaluate(f"""() => {{
            const qtyInput = document.querySelector('input.form-qty, input[formcontrolname="quantity"]');
            if (qtyInput) {{
                qtyInput.value = '{quantity}';
                qtyInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                qtyInput.dispatchEvent(new Event('change', {{ bubbles: true }}));
                qtyInput.dispatchEvent(new Event('blur', {{ bubbles: true }}));
                console.log('Quantity set to: ' + '{quantity}');
            }}
        }}""")
        await page.wait_for_timeout(200)
        print(f"[DEBUG] Quantity set to: {quantity}")
        
        # === STEP 5: Set Price via JS ===
        print(f"[DEBUG] Step 5: Setting Price to {price} via JS...")
        await page.evaluate(f"""() => {{
            const priceInput = document.querySelector('input.form-price, input[formcontrolname="price"]');
            if (priceInput) {{
                priceInput.value = '{price}';
                priceInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                priceInput.dispatchEvent(new Event('change', {{ bubbles: true }}));
                priceInput.dispatchEvent(new Event('keyup', {{ bubbles: true }}));
                priceInput.dispatchEvent(new Event('blur', {{ bubbles: true }}));
                console.log('Price set to: ' + '{price}');
            }}
        }}""")
        await page.wait_for_timeout(200)
        print(f"[DEBUG] Price set to: {price}")
        
        # === STEP 6: Click Submit Button ===
        print("[DEBUG] Step 6: Looking for Submit button...")
        await page.wait_for_timeout(500)  # Wait for form validation
        
        # Strategy from JS snippet: Try generic submit button first
        submit_clicked = False
        submit_btn = page.locator('button[type="submit"]').first
        
        try:
            if await submit_btn.count() > 0:
                 await submit_btn.click()
                 print("[DEBUG] Clicked generic submit button (button[type='submit'])")
                 submit_clicked = True
            else:
                 print("[DEBUG] Generic submit button not found, falling back to Enter key")
                 await page.keyboard.press("Enter")
                 submit_clicked = True
        except Exception as e:
            print(f"[DEBUG] Submit strategy failed: {e}")
            
        # === STEP 7: Handle Confirmation Dialog (SweetAlert) ===
        print("[DEBUG] Step 7: Checking for confirmation dialog...")
        # await page.wait_for_timeout(1000) # Removed arbitrary wait, selector wait handles it
        
        # Priority list of selectors from JS snippet
        # Key insight: Modals are usually appended to the end of the DOM, so use .last()
        confirm_selectors = [
            f"button:has-text('BUY')",
            f"button:has-text('Buy')", 
            "button:has-text('Confirm')",
            "button:has-text('Yes')"
        ]
        
        clicked_confirm = False
        for selector in confirm_selectors:
            try:
                # Use .last() because modals are usually appended to the end of the DOM.
                btn = page.locator(selector).last
                
                if await btn.count() > 0:
                    if await btn.is_visible():
                        print(f"[DEBUG] Found Confirmation Button: {selector}")
                        await btn.click()
                        clicked_confirm = True
                        break
            except: continue
        
        if not clicked_confirm:
             print("[DEBUG] ⚠️ No specific confirmation button found (BUY/Confirm). Checked multiple selectors.")
        
        # === STEP 8: Capture Result ===
        # Wait for toast to appear after confirmation click (toasts are transient)
        print("[DEBUG] Waiting for toast notification...")
        toast_messages = await wait_for_toast(page, timeout_ms=5000)
        popup_msg = " ".join(toast_messages) if toast_messages else ""
        print(f"[DEBUG] Toast/Popup message: {popup_msg}")
        
        if popup_msg:
            result["popupMessage"] = popup_msg
            if is_error_message(popup_msg):
                result["status"] = "ERROR"
                result["message"] = popup_msg
            else:
                result["status"] = "SUBMITTED"
                result["message"] = popup_msg
        else:
            result["status"] = "SUBMITTED"
            result["message"] = "Order submitted (no popup captured)"
        
        # === STEP 8: Extract Order Book ===
        print("[DEBUG] Extracting Order Book...")
        try:
            # Click refresh
            refresh_btn = page.locator("#kendo__refresh, .k-i-refresh").first
            if await refresh_btn.is_visible():
                await refresh_btn.click()
                await page.wait_for_timeout(2000)
            
            # Get order book rows
            # Get order book rows - target specifically the data content table
            # The structure separates headers (.k-grid-header) and data (.k-grid-content)
            data_rows_selector = ".k-grid-content tbody tr"
            try:
                await page.wait_for_selector(data_rows_selector, timeout=5000)
            except:
                print("[DEBUG] Timeout waiting for order book rows")

            rows = page.locator(data_rows_selector)
            count = await rows.count()
            
            order_book = []
            for i in range(min(count, 10)):
                row_text = await rows.nth(i).inner_text()
                if row_text.strip() and "No records" not in row_text:
                    parsed_row = parse_order_book_row(row_text.strip())
                    parsed_row["row"] = i  # Keep the index for reference
                    order_book.append(parsed_row)
            
            result["orderBook"] = order_book
            print(f"[DEBUG] Extracted {len(order_book)} order book entries")

            if len(order_book) == 0:
                 print("[DEBUG] Order book empty! Saving debug info to Store...")
                 try:
                     from apify import Actor
                     # Dump HTML
                     html_content = await page.content()
                     await Actor.set_value('order_entry_dump.html', html_content, content_type='text/html')
                     # Capture Screenshot
                     png_data = await page.screenshot(full_page=True)
                     await Actor.set_value('order_entry_fail.png', png_data, content_type='image/png')
                     print("[DEBUG] Saved order_entry_dump.html and order_entry_fail.png")
                 except Exception as dump_err:
                     print(f"[DEBUG] Failed to save debug dump: {dump_err}")
            
        except Exception as e:
            print(f"[DEBUG] Order book extraction failed: {e}")
            result["failureType"] = "ORDER_BOOK_EXTRACTION_FAILED"
        
        # === STEP 9: Validation (Reload & Check) ===
        # Criteria: Symbol, Side=Buy, Qty match, Price match
        
        def check_order_in_book(book, sym, qty, prc):
            for entry in book:
                # Basic matching - parsing might differ slightly (float vs string)
                # entry['symbol'] should match sym
                # entry['side'] should contain 'Buy'
                # entry['quantity'] == qty
                # entry['price'] == prc
                try:
                    if (entry.get('symbol') == sym and 
                        'Buy' in entry.get('side', '') and
                        int(entry.get('quantity', 0)) == int(qty) and
                        float(entry.get('price', 0)) == float(prc)):
                        return True
                except: pass
            return False

        print("[DEBUG] Validating order in Order Book...")
        is_found = False
        
        # Check 1: Immediate
        if "orderBook" in result and result["orderBook"]:
            if check_order_in_book(result["orderBook"], symbol, quantity, price):
                is_found = True
                print("[DEBUG] ✅ Order found in initial Order Book check.")
        
        # Check 2: Reload if not found and status was SUBMITTED
        if not is_found and result["status"] == "SUBMITTED":
            print("[DEBUG] ⚠️ Order not found immediately. Reloading page to verify...")
            try:
                await page.reload(wait_until='domcontentloaded')
                await wait_for_loading_screen_to_vanish(page)
                
                # Re-extract
                # Wait for grid to be visible again
                try:
                    await page.wait_for_selector(data_rows_selector, timeout=10000)
                except:
                    print("[DEBUG] Timeout waiting for grid after reload")
                
                rows_v2 = page.locator(data_rows_selector)
                count_v2 = await rows_v2.count()
                book_v2 = []
                for i in range(min(count_v2, 10)):
                    row_txt = await rows_v2.nth(i).inner_text()
                    parsed = parse_order_book_row(row_txt.strip())
                    book_v2.append(parsed)
                
                if check_order_in_book(book_v2, symbol, quantity, price):
                    is_found = True
                    print("[DEBUG] ✅ Order found after reload.")
                else:
                    print("[DEBUG] ❌ Order NOT found even after reload.")
                    
            except Exception as reload_err:
                 print(f"[DEBUG] Error during validation reload: {reload_err}")

        if is_found:
            result["validationStatus"] = "VALIDATED"
        else:
            result["validationStatus"] = "NOT_VALIDATED"
            # If we thought it was submitted but can't find it, that's suspicious
            if result["status"] == "SUBMITTED":
                 print("[DEBUG] WARNING: Order was submitted but not validated.")
            
    except Exception as e:
        print(f"[DEBUG] Error placing order: {e}")
        result["message"] = str(e)
        result["status"] = "EXCEPTION"
        result["failureType"] = "UNHANDLED_EXCEPTION"
        
    return result
