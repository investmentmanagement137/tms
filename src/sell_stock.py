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
        # 1. Select Instrument (Native Select)
        try:
             await page.select_option("select[formcontrolname='instType']", label=instrument)
        except Exception as err:
             print(f"[DEBUG] Instrument selection failed: {err}")
             try:
                 await page.select_option("select[formcontrolname='instType']", value=instrument)
             except: pass

        # 2. Select Sell Tab
        try:
            sell_tab = page.locator("xpath=//a[contains(text(), 'Sell')] | //button[contains(text(), 'Sell')]").first
            if await sell_tab.is_visible():
                await sell_tab.click()
            else:
                 await page.click(".btn-sell, .sell-tab, input[value='2']")
        except:
             print("[DEBUG] Sell tab selection exception (ignoring)")

        print("[DEBUG] Selected SELL tab")

        # 3. Enter Symbol
        print(f"[DEBUG] Entering Symbol: {symbol}")
        await page.click("input[formcontrolname='symbol']")
        await page.fill("input[formcontrolname='symbol']", symbol)
        await page.keyboard.press("Tab") 
        await page.wait_for_timeout(1500)
        await page.keyboard.press("Enter")

        # 4. Enter Quantity
        print(f"[DEBUG] Entering Quantity: {quantity}")
        await page.fill("input[formcontrolname='quantity']", str(quantity))

        # 5. Enter Price
        print(f"[DEBUG] Entering Price: {price}")
        await page.fill("input[formcontrolname='price']", str(price))
        
        await page.wait_for_timeout(500)
        
        # 6. Click Submit (Sell Button)
        print("[DEBUG] Clicking Sell Button...")
        submit_btn = page.locator("button[type='submit'], button.btn-primary, button.btn-danger, button.btn-success").first
        await submit_btn.click()
        print("[DEBUG] Clicked Submit.")
        
        # 7. Check for Errors/Success
        await page.wait_for_timeout(2000)
        
        error_msg = ""
        toasts = page.locator(".toast-message, .alert-danger")
        count = await toasts.count()
        if count > 0:
            for i in range(count):
                if await toasts.nth(i).is_visible():
                    txt = await toasts.nth(i).text_content()
                    error_msg += txt + " "
            
        if error_msg and "success" not in error_msg.lower():
            print(f"[DEBUG] Order Error: {error_msg}")
            result["message"] = f"Error: {error_msg}"
            result["status"] = "ERROR"
        else:
            print("[DEBUG] Order Submitted.")
            result["status"] = "SUBMITTED"
            result["message"] = "Order submitted successfully"
            
            # --- 8. EXTRACT ON-PAGE ORDER BOOK (With Refresh & Actions) ---
            print("[DEBUG] Refreshing On-Page Order Book...")
            try:
                # 1. Click Refresh Button
                refresh_btn = page.locator(".nf-refresh, button:has(.nf-refresh)").last
                if await refresh_btn.is_visible():
                    await refresh_btn.click()
                    await page.wait_for_timeout(1500)
                else:
                    print("[DEBUG] Refresh button not found.")

                # 2. Scrape Client's Order Book
                try:
                    daily_tab = page.locator("a:has-text('Daily Order Book'), span:has-text('Daily Order Book')").first
                    if await daily_tab.is_visible():
                         await daily_tab.click()
                         await page.wait_for_timeout(1000)
                except: pass

                # Strategy: Target the KENDO GRID specifically (class k-grid)
                kendo_grid = page.locator("kendo-grid, .k-grid").first
                if await kendo_grid.is_visible():
                    print("[DEBUG] Found Kendo Grid (Order Book)")
                    rows = kendo_grid.locator("tbody tr, .k-grid-content tbody tr")
                else:
                    # Fallback: try to find any table that contains the symbol we just ordered
                    print("[DEBUG] Kendo Grid not found, falling back to symbol search...")
                    tables = page.locator("table")
                    count_tables = await tables.count()
                    target_table = None
                    
                    for t_idx in range(count_tables):
                        tbl = tables.nth(t_idx)
                        tbl_text = await tbl.text_content()
                        if symbol.upper() in tbl_text.upper():
                            target_table = tbl
                            print(f"[DEBUG] Found table containing symbol at index {t_idx}")
                            break
                    
                    if target_table:
                        rows = target_table.locator("tbody tr")
                    else:
                        rows = page.locator(".table tbody tr")

                count = await rows.count()
                order_book_entries = []
                
                for i in range(min(count, 10)):
                    row = rows.nth(i)
                    row_text = await row.inner_text()
                    
                    if "No records available" in row_text:
                        break
                    
                    cells = row.locator("td")
                    cell_count = await cells.count()
                    row_data = []
                    action_links = []
                    
                    for j in range(cell_count):
                        cell = cells.nth(j)
                        text = (await cell.inner_text()).strip()
                        row_data.append(text)
                        
                        links = cell.locator("a, button")
                        if await links.count() > 0:
                            for k in range(await links.count()):
                                link = links.nth(k)
                                href = await link.get_attribute("href")
                                title = await link.get_attribute("title")
                                if href and href != "#":
                                    action_links.append(f"Link: {href}")
                                elif title:
                                    action_links.append(f"Action: {title}")
                    
                    order_book_entries.append({
                        "row_text": " | ".join(row_data),
                        "actions": action_links
                    })
                
                result["orderBook"] = order_book_entries
                print(f"[DEBUG] Extracted {len(order_book_entries)} entries.")
                
            except Exception as e:
                print(f"Order book check failed: {e}")
            
    except Exception as e:
        print(f"[DEBUG] Error placing order: {e}")
        result["message"] = str(e)
        result["status"] = "EXCEPTION"
        
    return result
