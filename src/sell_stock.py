import asyncio
from urllib.parse import urlencode

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
    # Only symbol parameter works natively - use it!
    order_url = f"{base_url}/tms/me/memberclientorderentry?symbol={symbol}"
    
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
        # Navigate - symbol will be auto-filled via URL param
        await page.goto(order_url, wait_until='networkidle')
        await page.wait_for_timeout(2000)  # Wait for Angular to fully load
        
        # === STEP 1: Set Instrument via JS (if not EQ) ===
        if instrument != "EQ":
            print(f"[DEBUG] Step 1: Setting Instrument to {instrument} via JS...")
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
            print("[DEBUG] Step 1: Instrument is EQ (default), skipping")
        
        # === STEP 2: Click SELL toggle via JS ===
        print("[DEBUG] Step 2: Activating SELL toggle via JS...")
        await page.evaluate("""() => {
            // Find and click the SELL side of the toggle
            const sellLabel = document.querySelector('.order__options--sell');
            if (sellLabel) {
                sellLabel.click();
                console.log('SELL toggle clicked');
            }
        }""")
        await page.wait_for_timeout(300)
        print("[DEBUG] SELL toggle activated")
        
        # === STEP 3: Wait for symbol to load (from URL param) and verify ===
        print(f"[DEBUG] Step 3: Verifying Symbol: {symbol}")
        await page.wait_for_timeout(1000)
        
        # Check if symbol dropdown appeared and needs clicking
        dropdown = page.locator(".dropdown-menu li a").first
        try:
            if await dropdown.is_visible(timeout=2000):
                await dropdown.click()
                print("[DEBUG] Symbol dropdown item clicked")
                await page.wait_for_timeout(500)
        except:
            print("[DEBUG] No dropdown visible, symbol may already be set")
        
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
                priceInput.dispatchEvent(new Event('blur', {{ bubbles: true }}));
                console.log('Price set to: ' + '{price}');
            }}
        }}""")
        await page.wait_for_timeout(200)
        print(f"[DEBUG] Price set to: {price}")
        
        # === STEP 6: Click Submit Button ===
        print("[DEBUG] Step 6: Looking for Submit button...")
        await page.wait_for_timeout(500)  # Wait for form validation
        
        # Check submit button state
        btn_info = await page.evaluate("""() => {
            const btn = document.querySelector('button.btn-sm:not(.btn-default), button.btn-primary');
            if (btn) {
                return {
                    text: btn.innerText.trim(),
                    disabled: btn.disabled,
                    className: btn.className
                };
            }
            return null;
        }""")
        
        print(f"[DEBUG] Submit button state: {btn_info}")
        
        if btn_info and "SELL" in btn_info.get("text", "").upper() and not btn_info.get("disabled"):
            submit_btn = page.locator("button.btn-sm:not(.btn-default), button.btn-primary:has-text('SELL')").first
            await submit_btn.click()
            print("[DEBUG] Submit button clicked!")
            submit_clicked = True
        else:
            print("[DEBUG] Submit button not ready, trying force click...")
            # Force click via JS
            await page.evaluate("""() => {
                const btn = document.querySelector('button.btn-sm:not(.btn-default)');
                if (btn) btn.click();
            }""")
            submit_clicked = True
        
        # === STEP 7: Capture Result ===
        await page.wait_for_timeout(2500)
        
        # Check for popup/toast messages
        popup_msg = ""
        popup_selectors = [
            ".toast-container .toast-message",
            ".toast-message",
            ".toast-body",
            ".alert-danger",
            ".alert-success",
            ".swal2-title",
        ]
        
        for selector in popup_selectors:
            popups = page.locator(selector)
            count = await popups.count()
            for i in range(count):
                if await popups.nth(i).is_visible():
                    txt = await popups.nth(i).text_content()
                    if txt and txt.strip():
                        popup_msg += txt.strip() + " "
        
        popup_msg = popup_msg.strip()
        print(f"[DEBUG] Popup message: {popup_msg}")
        
        if popup_msg:
            result["popupMessage"] = popup_msg
            if any(err in popup_msg.lower() for err in ["error", "failed", "invalid", "rejected"]):
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
