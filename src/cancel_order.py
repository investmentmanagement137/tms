import asyncio
from urllib.parse import urlparse, parse_qs

async def execute(page, tms_url):
    """
    Automates order cancellation based on user provided logic.
    1. Navigates to /tms/me/order-book-v3
    2. Cancels all OPEN orders
    3. Extracts modify URLs for PARTIALLY_TRADED orders
    """
    print("\n[DEBUG] 🚀 Starting Order Cancellation Script...")
    
    base_url = tms_url.rstrip('/')
    target_url = f"{base_url}/tms/me/order-book-v3"
    
    print(f"[DEBUG] Navigating to Order Book: {target_url}")
    
    result = {
        "status": "SUCCESS",
        "cancelledCount": 0,
        "partiallyTradedOrders": [],
        "message": ""
    }
    
    try:
        await page.goto(target_url, wait_until='networkidle')
        
        # Wait for grid
        try:
            await page.wait_for_selector('kendo-grid', timeout=20000)
        except:
             print("[DEBUG] ❌ Failed to load Order Book table.")
             result["status"] = "FAILED"
             result["message"] = "Failed to load Order Book table"
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
        
        while True:
            # Re-extract rows to get fresh DOM state
            current_rows = await extract_open_rows()
            target = next((r for r in current_rows if r['status'] == 'OPEN'), None)
            
            if not target:
                break
                
            print(f"[DEBUG]   Cancelling: {target['symbol']} ({target['qty']} @ {target['price']})")
            
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
                    await page.reload(wait_until='networkidle')
                    await page.wait_for_timeout(2000)

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
                    break # Stop to avoid infinite loop
            else:
                print("    ⚠️ Cancel button not found")
                break # Stop to avoid infinite loop
                
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
                    await page.goto(target_url, wait_until='networkidle')
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
