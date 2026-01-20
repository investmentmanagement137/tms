import asyncio
from urllib.parse import urlencode
from .toast_capture import capture_all_popups, wait_for_toast, is_error_message
from .utils import set_toggle_position, set_symbol

async def execute(page, tms_url, symbol, quantity, price, instrument="EQ"):
    """
    Places a SELL order using Playwright.
    
    Strategy (validated via browser testing):
    1. Navigate with ?symbol=XXX (only URL param that works natively)
    2. Use JavaScript to set Instrument, Toggle, Quantity, Price
    3. Click Submit button
    
    Returns result dictionary.
    """
    print(f"\n[DEBUG] Placing SELL Order: {symbol}, Qty: {quantity}, Price: {price}, Instrument: {instrument}")
    
    base_url = tms_url.rstrip('/')
    # Remove symbol from URL for manual entry
    order_url = f"{base_url}/tms/me/memberclientorderentry"
    
    print(f"[DEBUG] Navigating to: {order_url}")
    
    result = {
        "status": "FAILED",
        "message": "",
        "sellEntryUrl": order_url,
        "orderDetails": {
            "symbol": symbol,
            "quantity": quantity,
            "price": price,
            "action": "SELL",
            "instrument": instrument
        }
    }
    
    try:
        # Navigate without symbol
        await page.goto(order_url, wait_until='networkidle')
        await page.wait_for_timeout(2000)  # Wait for Angular to fully load

        # === STEP 1: Activate SELL toggle with robust retry ===
        # Reverting to Toggle -> Instrument order to match working JS script
        print("[DEBUG] Step 1: Activating SELL toggle...")
        is_sell_active = await set_toggle_position(page, "sell")
        
        if not is_sell_active:
             print("[DEBUG] WARNING: Could not verify SELL toggle state! Proceeding anyway but order might fail.")
        else:
             print("[DEBUG] SELL toggle confirmed active")

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
            return result
        
        await page.wait_for_timeout(1000)
        
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
            
        # === STEP 7: Capture Result (Check for Confirmation Dialog first) ===
        # Note: New JS snippet implies confirmation happens right after submit
        print("[DEBUG] Step 7: Checking for confirmation dialog...")
        await page.wait_for_timeout(1000) # Allow modal to appear
        
        # Priority list of selectors from JS snippet
        # Key insight: Modals are usually appended to the end of the DOM, so use .last()
        confirm_selectors = [
            f"button:has-text('SELL')",
            f"button:has-text('Sell')", 
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
             print("[DEBUG] ⚠️ No specific confirmation button found (SELL/Confirm). Checked multiple selectors.")
        
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
            rows = page.locator("kendo-grid tbody tr, .k-grid tbody tr")
            count = await rows.count()
            
            order_book = []
            for i in range(min(count, 10)):
                row_text = await rows.nth(i).inner_text()
                if row_text.strip() and "No records" not in row_text:
                    order_book.append({"row": i, "text": row_text.strip()})
            
            result["orderBook"] = order_book
            print(f"[DEBUG] Extracted {len(order_book)} order book entries")
            
        except Exception as e:
            print(f"[DEBUG] Order book extraction failed: {e}")
            
    except Exception as e:
        print(f"[DEBUG] Error placing order: {e}")
        result["message"] = str(e)
        result["status"] = "EXCEPTION"
        
    return result
