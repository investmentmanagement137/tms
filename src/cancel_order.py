import asyncio
from urllib.parse import urlparse, parse_qs
from src.utils import wait_for_loading_screen_to_vanish

async def execute(page, tms_url):
    """
    Automates order cancellation based on user provided logic.
    2. Cancels all OPEN orders
    3. Extracts modify URLs for PARTIALLY_TRADED orders
    """
    print("\n[DEBUG] 🚀 Starting Order Cancellation Script...")
    
    # FIX: Ensure we use the root domain, stripping /login if present
    parsed = urlparse(tms_url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"
    target_url = f"{base_url}/tms/me/order-book-v3"
    
    # Helper for Hybrid Navigation
    async def navigate_to_order_book(page, url):
        print(f"[DEBUG] Navigating to Order Book...")
        
        # Strategy A: Direct URL
        try:
            print(f"[DEBUG] Strategy A: Direct URL ({url})")
            await page.goto(url, wait_until='domcontentloaded')
            
            # CRITICAL: Wait for the .preloader to vanish!
            await wait_for_loading_screen_to_vanish(page)
            
            # Broader selector: kendo-grid (tag), .k-grid (class), or just any table
            await page.wait_for_selector('kendo-grid, .k-grid, table.table', timeout=15000)
            print("[DEBUG] ✅ Direct URL navigation successful")
            return True
        except Exception as e:
            print(f"[DEBUG] ⚠️ Direct URL failed/timed out: {e}")
            
        print("[DEBUG] Strategy B: Button Click Fallback")
        try:
            # Check for "Order Management" sidebar item
            # Expanding sidebar if needed
            om_btn = page.locator("text=Order Management").first
            if await om_btn.count() > 0:
                 if await om_btn.is_visible():
                     await om_btn.click()
                     await page.wait_for_timeout(500)
            
            # Click "Order Book"
            # Try multiple text variations
            ob_btn = page.locator("text=Order Book").first
            if await ob_btn.count() == 0:
                 ob_btn = page.locator("a:has-text('Order Book')")
            
            if await ob_btn.count() > 0:
                await ob_btn.click()
                # Wait for grid
                await page.wait_for_selector('kendo-grid, .k-grid, table.table', timeout=15000)
                print("[DEBUG] ✅ Button Click navigation successful")
                return True
            else:
                print("[DEBUG] ❌ 'Order Book' button not found")
                
        except Exception as e:
             print(f"[DEBUG] ❌ Button fallback failed: {e}")
             
        return False

    result = {
        "status": "SUCCESS",
        "cancelledCount": 0,
        "partiallyTradedOrders": [],
        "failureType": None,
        "validationStatus": "N/A" # Cancellation doesn't use the standard validation loop yet
    }
    
    try:
        # Use Hybrid Navigation Helper
        if not await navigate_to_order_book(page, target_url):
             print("[DEBUG] ❌ Failed to load Order Book table (All strategies exhausted).")
             
             # --- DEBUG CAPTURE ---
             try:
                 print("[DEBUG] 📸 Saving screenshot to 'order_book_fail.png'...")
                 await page.screenshot(path="order_book_fail.png", full_page=True)
                 with open("order_book_fail.html", "w", encoding="utf-8") as f:
                     f.write(await page.content())
             except Exception as dump_err:
                 print(f"[DEBUG] Failed to save debug artifacts: {dump_err}")
             # ---------------------
             
             result["status"] = "FAILED"
             result["message"] = "Failed to load Order Book table"
             result["failureType"] = "ORDER_BOOK_NAV_FAILED"
             return result

        # Ensure "Open" tab is selected
        print("[DEBUG] Switching to 'Open' tab...")
        try:
            # Use strict matching for 'Open' text to avoid partial matches
            open_tab = page.locator('ul.k-tabstrip-items li span.k-link').filter(has_text="Open").first
            # Fallback to simple text match if specific structure fails
            if await open_tab.count() == 0:
                 open_tab = page.locator('text=Open').first
            
            await open_tab.click()
            await page.wait_for_timeout(1500)
        except Exception as e:
            print(f"[DEBUG] Error switching tab: {e}")
            
        # Helper to extract rows
        async def extract_open_rows():
            return await page.evaluate("""() => {
                const rows = [];
                const grid = document.querySelector('kendo-grid');
                if (!grid) return [];

                const tableRows = grid.querySelectorAll('tbody tr');
                tableRows.forEach((tr, index) => {
                    const cells = tr.querySelectorAll('td');
                    // Column Mapping for "Open" Tab (0-based index from script):
                    // Index 4: STATUS
                    // Index 7: SYMBOL
                    // Index 9: QTY
                    // Index 11: PRICE
                    rows.push({
                        rowIndex: index,
                        status: cells[4]?.innerText.trim() || '',
                        symbol: cells[7]?.innerText.trim() || '',
                        qty: cells[9]?.innerText.trim() || '',
                        price: cells[11]?.innerText.trim() || ''
                    });
                });
                return rows;
            }""")

        # PHASE 1: CANCEL OPEN ORDERS
        initial_rows = await extract_open_rows()
        orders_to_cancel = [r for r in initial_rows if r['status'] == 'OPEN']
        print(f"[DEBUG] 🗑️ Found {len(orders_to_cancel)} OPEN orders to cancel.")
        
        cancelled_count = 0
        
        # Track attempts to prevent infinite loops on stubborn orders
        # Signature: (status, symbol, qty, price)
        attempt_tracker = {} 
        MAX_RETRIES_PER_ORDER = 3

        while True:
            # Re-extract rows to get fresh DOM state
            current_rows = await extract_open_rows()
            
            # Find first OPEN order that hasn't exceeded retries
            possible_targets = [r for r in current_rows if r['status'] == 'OPEN']
            target = None
            
            for t in possible_targets:
                 sig = f"{t['symbol']}_{t['qty']}_{t['price']}"
                 if attempt_tracker.get(sig, 0) < MAX_RETRIES_PER_ORDER:
                     target = t
                     break
            
            if not target:
                if len(possible_targets) > 0:
                     print(f"[DEBUG] ⚠️ All {len(possible_targets)} remaining OPEN orders have reached max retries. Stopping.")
                else:
                     print("[DEBUG] No more OPEN orders found.")
                break
                
            # Create a unique signature for this order instance
            order_sig = f"{target['symbol']}_{target['qty']}_{target['price']}"
            
            # Check retry count
            attempts = attempt_tracker.get(order_sig, 0)
            if attempts >= MAX_RETRIES_PER_ORDER:
                print(f"[DEBUG] ⚠️ Max retries reached for stubborn order: {order_sig}. Skipping/Aborting loop.")
                result["message"] += f"Skipped stubborn order {order_sig}. "
                break
            
            attempt_tracker[order_sig] = attempts + 1
            
            print(f"[DEBUG]   Cancelling: {target['symbol']} ({target['qty']} @ {target['price']}) - Attempt {attempts + 1}")
            
            # Locate cancel button using User's selectors
            row_idx = target['rowIndex'] + 1 # nth-child is 1-based
            
            cancel_selector = (
                f"tbody tr:nth-child({row_idx}) td:nth-child(4) .nf-deactivate, "
                f"tbody tr:nth-child({row_idx}) td:nth-child(4) .table--deactivate, "
                f"tbody tr:nth-child({row_idx}) td [title='Cancel Order']"
            )
            
            cancel_btn = page.locator(cancel_selector).first
            
            if await cancel_btn.count() > 0:
                await cancel_btn.click()
                await page.wait_for_timeout(500)
                
                # Handle Confirmation Modal
                yes_btn = page.locator('button:has-text("Yes")').first
                if await yes_btn.count() > 0 and await yes_btn.is_visible():
                    await yes_btn.click()
                    await page.wait_for_timeout(1000) # Wait for action
                    print("    ✅ Cancelled")
                    cancelled_count += 1

                    # --- RELOAD to ensure fresh state ---
                    print("[DEBUG] Reloading page to refresh order list...")
                    await page.reload(wait_until='domcontentloaded')
                    await page.wait_for_selector('kendo-grid', timeout=10000)

                    # Re-select 'Open' tab
                    try:
                        open_tab = page.locator('ul.k-tabstrip-items li span.k-link').filter(has_text="Open").first
                        if await open_tab.count() == 0:
                            open_tab = page.locator('text=Open').first
                        await open_tab.click()
                        await page.wait_for_timeout(1500)
                    except Exception as e:
                         print(f"[DEBUG] Error switching tab after reload: {e}")
                    
                    # Continue loop to re-extract rows
                    continue
                else:
                    print("    ⚠️ Confirmation dialog not found or not visible")
                    result["message"] += f"Confirmation missing for {target['symbol']}. "
                    
                    # If we failed to confirm, we must reload or break to avoid staring at the same modal forever
                    # But since we didn't confirm, the order is still there. 
                    # We continue, which will trigger the retry limit next loop.
                    await page.reload(wait_until='domcontentloaded') 
                    continue
            else:
                print("    ⚠️ Cancel button not found")
                # Reload to see if UI was stale
                await page.reload(wait_until='domcontentloaded')
                continue
                
        result["cancelledCount"] = cancelled_count
        print(f"[DEBUG] ✅ Cancelled {cancelled_count} orders.")
        
        # PHASE 2: PARTIALLY TRADED ORDERS
        # Refresh rows
        current_rows = await extract_open_rows()
        partial_orders = [r for r in current_rows if r['status'] == 'PARTIALLY_TRADED']
        print(f"\n[DEBUG] 🔗 Found {len(partial_orders)} PARTIALLY_TRADED orders.")
        
        modify_results = []
        
        for order in partial_orders:
            # Find fresh row index
            current_refresh = await extract_open_rows()
            target_row = next((r for r in current_refresh if r['symbol'] == order['symbol'] and r['status'] == 'PARTIALLY_TRADED'), None)
            
            if target_row:
                print(f"[DEBUG]   Getting URL for: {order['symbol']}")
                row_idx = target_row['rowIndex'] + 1
                
                # Locate Edit Button
                edit_selector = (
                    f"tbody tr:nth-child({row_idx}) td:nth-child(4) .nf-table-edit, "
                    f"tbody tr:nth-child({row_idx}) td:nth-child(4) .table--edit"
                )
                edit_btn = page.locator(edit_selector).first
                
                if await edit_btn.count() > 0:
                    await edit_btn.click()
                    await page.wait_for_timeout(1500)
                    
                    # Capture URL
                    modify_url = page.url
                    query = urlparse(modify_url).query
                    params = parse_qs(query)
                    order_id = params.get('id', [None])[0]
                    
                    print(f"    ✅ URL: {modify_url}")
                    modify_results.append({
                        "symbol": order['symbol'],
                        "status": "PARTIALLY_TRADED",
                        "qty": order['qty'],
                        "price": order['price'],
                        "modifyUrl": modify_url,
                        "orderId": order_id
                    })
                    
                    # Navigate BACK to Order Book
                    await page.goto(target_url, wait_until='domcontentloaded')
                    try:
                        await page.wait_for_selector('kendo-grid', timeout=10000)
                        # Switch tab again
                        open_tab = page.locator('text=Open').first
                        await open_tab.click()
                        await page.wait_for_timeout(500)
                    except:
                        print("[DEBUG] Failed to return to order book properly")
                        break
        
        result["partiallyTradedOrders"] = modify_results
        
    except Exception as e:
        print(f"[DEBUG] ❌ Script Error: {e}")
        result["status"] = "ERROR"
        result["message"] = str(e)
        
    return result
