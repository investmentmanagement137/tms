import asyncio

async def execute(page, tms_url, symbol, quantity, price):
    """
    Places a SELL order using Playwright.
    Returns result dictionary.
    """
    print(f"\n[DEBUG] Placing SELL Order: {symbol}, Qty: {quantity}, Price: {price}")
    
    # Construct paths using base URL
    base_url = tms_url.rstrip('/')
    order_url = f"{base_url}/tms/n/order/order-entry"
    
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
        # 1. Select Sell Tab
        try:
            sell_tab = page.locator("xpath=//a[contains(text(), 'Sell')] | //button[contains(text(), 'Sell')]").first
            if await sell_tab.is_visible():
                await sell_tab.click()
            else:
                 await page.click(".btn-sell, .sell-tab, input[value='2']")
        except:
             print("[DEBUG] Sell tab selection exception (ignoring)")

        print("[DEBUG] Selected SELL tab")

        # 2. Enter Symbol
        print(f"[DEBUG] Entering Symbol: {symbol}")
        await page.fill("input[placeholder='Symbol'], input[name='symbol']", symbol)
        await page.keyboard.press("Tab") # Trigger autocomplete
        await page.wait_for_timeout(1000)

        # 3. Enter Quantity
        print(f"[DEBUG] Entering Quantity: {quantity}")
        await page.fill("input[placeholder='Qty'], input[name='quantity']", str(quantity))

        # 4. Enter Price
        print(f"[DEBUG] Entering Price: {price}")
        await page.fill("input[placeholder='Price'], input[name='price']", str(price))
        
        await page.wait_for_timeout(500)
        
        # 5. Click Submit (Sell Button)
        print("[DEBUG] Clicking Sell Button...")
        submit_btn = page.locator("button[type='submit'], button.btn-primary, button.btn-danger, button.btn-success").first
        await submit_btn.click()
        print("[DEBUG] Clicked Submit.")
        
        # 6. Check for Errors/Success
        await page.wait_for_timeout(2000)
        
        error_msg = ""
        toasts = page.locator(".toast-message, .alert-danger")
        count = await toasts.count()
        if count > 0:
            for i in range(count):
                if await toasts.nth(i).is_visible():
                    txt = await toasts.nth(i).text_content()
                    error_msg += txt + " "
            
        if error_msg:
            print(f"[DEBUG] Order Error: {error_msg}")
            result["message"] = f"Error: {error_msg}"
            result["status"] = "ERROR"
        else:
            print("[DEBUG] Order Submitted (No immediate error detected).")
            result["status"] = "SUBMITTED"
            result["message"] = "Order submitted successfully"
            
    except Exception as e:
        print(f"[DEBUG] Error placing order: {e}")
        result["message"] = str(e)
        result["status"] = "EXCEPTION"
        
    return result
