from selenium.webdriver.common.by import By
import time

def execute(driver, tms_url, symbol, quantity, price):
    """
    Places a SELL order.
    Returns result dictionary.
    """
    print(f"\n[DEBUG] Placing SELL Order: {symbol}, Qty: {quantity}, Price: {price}")
    
    # Construct paths using base URL
    base_url = tms_url.rstrip('/')
    order_url = f"{base_url}/tms/n/order/order-entry"
    
    print(f"[DEBUG] Navigating to Order Entry: {order_url}")
    driver.get(order_url)
    time.sleep(3)
    
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
            # Try finding a tab/button with text "Sell"
            sell_tab = driver.find_element(By.XPATH, "//a[contains(text(), 'Sell')] | //button[contains(text(), 'Sell')]")
            sell_tab.click()
        except:
            # Fallback to probable class names
            driver.execute_script("document.querySelector('.btn-sell, .sell-tab, input[value=\"2\"]').click()") # value=2 is common for Sell in some forms
        print("[DEBUG] Selected SELL tab")
        time.sleep(1)

        # 2. Enter Symbol
        print(f"[DEBUG] Entering Symbol: {symbol}")
        sym_input = driver.find_element(By.CSS_SELECTOR, "input[placeholder='Symbol'], input[name='symbol']")
        sym_input.clear()
        sym_input.send_keys(symbol)
        time.sleep(1)
        # Trigger autocomplete
        from selenium.webdriver.common.keys import Keys
        sym_input.send_keys(Keys.TAB)
        time.sleep(1)

        # 3. Enter Quantity
        print(f"[DEBUG] Entering Quantity: {quantity}")
        qty_input = driver.find_element(By.CSS_SELECTOR, "input[placeholder='Qty'], input[name='quantity']")
        qty_input.clear()
        qty_input.send_keys(str(quantity))

        # 4. Enter Price
        print(f"[DEBUG] Entering Price: {price}")
        price_input = driver.find_element(By.CSS_SELECTOR, "input[placeholder='Price'], input[name='price']")
        price_input.clear()
        price_input.send_keys(str(price))
        
        time.sleep(1)
        
        # 5. Click Submit (Sell Button might be Red/Distinct)
        print("[DEBUG] Clicking Sell Button...")
        submit_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit'], button.btn-primary, button.btn-danger, button.btn-success")
        # Note: Sell buttons are often 'btn-danger' or red.
        
        if "Place Order" in submit_btn.text or "Sell" in submit_btn.text:
            submit_btn.click()
            print("[DEBUG] Clicked Submit.")
        else:
             print("[DEBUG] Warning: Submit button text mismatch? Clicking anyway.")
             submit_btn.click()
        
        # 6. Check for Errors/Success
        time.sleep(2)
        
        # Check for error toast
        error_msg = ""
        try:
            toasts = driver.find_elements(By.CSS_SELECTOR, ".toast-message, .alert-danger")
            for t in toasts:
                if t.is_displayed():
                    error_msg += t.text + " "
        except:
            pass
            
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
