import asyncio
from urllib.parse import urlencode

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
    # Only symbol parameter works natively - use it!
    order_url = f"{base_url}/tms/me/memberclientorderentry?symbol={symbol}"
    
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
        
        # === STEP 2: Click BUY toggle via JS ===
        print("[DEBUG] Step 2: Activating BUY toggle via JS...")
        await page.evaluate("""() => {
            // Find and click the BUY side of the toggle
            const buyLabel = document.querySelector('.order__options--buy');
            if (buyLabel) {
                buyLabel.click();
                console.log('BUY toggle clicked');
            }
        }""")
        await page.wait_for_timeout(300)
        print("[DEBUG] BUY toggle activated")
        
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
        
        # Find and click the submit button more robustly
        submit_clicked = False
        
        # The submit button is within the order entry form - target specifically
        # Analysis shows it might just be 'btn btn-sm' with text '-' (icon) and type='submit'
        # It is NOT always btn-primary
        submit_selectors = [
            ".box-order-entry button[type='submit']",
            ".order__form button[type='submit']", 
            ".box-order-entry button.btn-sm:not(.btn-default)",
            ".order__form button.btn-sm:not(.btn-default)",
            "button.btn-sm:has-text('-')", # Fallback for icon button
            "button.btn-primary.btn-lg:not([disabled])", # Old fallback
        ]
        
        for selector in submit_selectors:
            try:
                # Get all matches
                btns = page.locator(selector)
                count = await btns.count()
                
                for i in range(count):
                    btn = btns.nth(i)
                    if await btn.is_visible() and await btn.is_enabled():
                        # Check if it's not a cancel button
                        txt = await btn.text_content()
                        if txt and ("cancel" in txt.lower() or "close" in txt.lower()):
                            continue
                            
                        await btn.click()
                        print(f"[DEBUG] Clicked submit button with selector: {selector} (Index {i})")
                        submit_clicked = True
                        break
                if submit_clicked: break
            except Exception as e:
                print(f"[DEBUG] Selector {selector} failed: {str(e)[:50]}")
                continue
        
        if not submit_clicked:
            print("[DEBUG] Submit button not found via locators, trying targeted JS click...")
            # More targeted JS - find button after price input within form
            result = await page.evaluate("""() => {
                // Find the price input first
                const priceInput = document.querySelector('input.form-price, input[formcontrolname="price"]');
                if (priceInput) {
                    // Find the closest form or container
                    const container = priceInput.closest('.box-order-entry, form, .order-form');
                    if (container) {
                        // Find the primary submit button in this container
                        const btn = container.querySelector('button.btn-primary.btn-lg:not([disabled])');
                        if (btn) {
                            btn.click();
                            console.log('Clicked submit button in form container');
                            return {success: true, btnClass: btn.className};
                        }
                    }
                }
                
                // Fallback: Find the first visible, non-disabled btn-primary.btn-lg
                const btns = document.querySelectorAll('button.btn-primary.btn-lg:not([disabled])');
                for (const btn of btns) {
                    const text = btn.innerText.trim().toLowerCase();
                    // Skip buttons with known non-submit text
                    if (!text || (!text.includes('update') && !text.includes('close') && !text.includes('cancel'))) {
                        if (btn.offsetParent !== null) {  // Is visible
                            btn.click();
                            console.log('Clicked fallback button:', btn.className);
                            return {success: true, btnClass: btn.className, fallback: true};
                        }
                    }
                }
                return {success: false};
            }""")
            print(f"[DEBUG] JS click result: {result}")
            submit_clicked = result.get('success', False) if result else False
        
        # === STEP 7: Handle Confirmation Dialog (SweetAlert) ===
        print("[DEBUG] Step 7: Checking for confirmation dialog...")
        await page.wait_for_timeout(1500)
        
        # TMS uses SweetAlert for confirmations - look for confirm button
        confirm_selectors = [
            ".swal2-confirm",  # SweetAlert confirm button
            "button.swal2-confirm",
            ".swal2-actions button.swal2-confirm",
            "button:has-text('OK')",
            "button:has-text('Confirm')",
            "button:has-text('Yes')"
        ]
        
        for selector in confirm_selectors:
            try:
                confirm_btn = page.locator(selector).first
                if await confirm_btn.count() > 0 and await confirm_btn.is_visible():
                    await confirm_btn.click()
                    print(f"[DEBUG] Clicked confirmation button: {selector}")
                    await page.wait_for_timeout(1000)
                    break
            except:
                continue
        
        # === STEP 8: Capture Result ===
        await page.wait_for_timeout(2000)
        
        # Check for popup/toast messages
        popup_msg = ""
        popup_selectors = [
            ".swal2-title",  # SweetAlert title (success/error)
            ".swal2-html-container",  # SweetAlert message
            ".toast-container .toast-message",
            ".toast-message",
            ".toast-body",
            ".alert-danger",
            ".alert-success",
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
                    order_book.append({"row": i, "text": row_text.strip()})
            
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
            
    except Exception as e:
        print(f"[DEBUG] Error placing order: {e}")
        result["message"] = str(e)
        result["status"] = "EXCEPTION"
        
    return result
