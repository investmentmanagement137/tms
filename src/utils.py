import re
import io
import time
import asyncio
from PIL import Image
import asyncio
from PIL import Image
from google import genai
from google.genai import types
from .toast_capture import log_toasts, capture_all_popups, is_error_message

async def solve_captcha(page, api_key):
    """Solves captcha using Gemini API (new google-genai SDK)."""
    try:
        print("Attempting to solve captcha using Gemini API...")
        
        print("Locating captcha image...")
        try:
            # Wait for captcha image
            captcha_loc = page.locator('img.captcha-image-dimension')
            await captcha_loc.wait_for(state='visible', timeout=5000)
        except:
            print("Could not find captcha image element.")
            return None
        
        print("Capturing captcha screenshot...")
        screenshot_bytes = await captcha_loc.screenshot()
        image = Image.open(io.BytesIO(screenshot_bytes))
        
        print("Sending to Gemini API...")
        # Client initialization
        client = genai.Client(api_key=api_key)
        
        # We run this in a thread executor because the new SDK might still be sync-heavy or we just want to be safe
        loop = asyncio.get_event_loop()
        
        def generate():
            response = client.models.generate_content(
                model='gemini-2.0-flash',
                contents=[
                    "What is the text in this captcha image? Return ONLY the alphanumeric text, no other words.",
                    image
                ]
            )
            return response.text

        captcha_text = await loop.run_in_executor(None, generate)
        
        if captcha_text:
            captcha_text = captcha_text.strip()
            print(f"Gemini solved captcha: '{captcha_text}'")
            return captcha_text
        else:
             print("Gemini returned empty text.")
             return None
        
    except Exception as e:
        print(f"Error solving captcha: {e}")
        return None

async def perform_login(page, username, password, api_key, tms_url):
    """
    Performs login to TMS (Async Playwright).
    Returns True if login is successful, False otherwise.
    
    Implements robust error handling:
    - Multiple navigation strategies
    - Explicit element waits with fallbacks
    - Error categorization and recovery
    - Fresh page creation on crash
    """
    # Ensure URL ends with /login for the initial navigation
    if not tms_url.endswith("/login"):
        login_url = f"{tms_url.rstrip('/')}/login"
    else:
        login_url = tms_url
        
    print(f"[LOGIN] Target URL: {login_url}")
    
    max_retries = 3
    
    for attempt in range(1, max_retries + 1):
        print(f"\n{'='*50}")
        print(f"[LOGIN] Attempt {attempt}/{max_retries}")
        print(f"{'='*50}")
        
        try:
            # === STEP 1: Navigate to Login Page ===
            print("[LOGIN] Step 1: Navigating to login page...")
            navigation_success = False
            
            # Try multiple navigation strategies
            nav_strategies = [
                ('domcontentloaded', 30000), 
                ('load', 60000),
                ('commit', 30000),
            ]
            
            for wait_until, timeout in nav_strategies:
                try:
                    await page.goto(login_url, wait_until=wait_until, timeout=timeout)
                    navigation_success = True
                    print(f"[LOGIN] Navigation successful (strategy: {wait_until})")
                    break
                except Exception as nav_err:
                    print(f"[LOGIN] Navigation failed with {wait_until}: {str(nav_err)[:80]}")
                    continue
            
            if not navigation_success:
                print("[LOGIN] Navigation strategies failed (stuck on loading?). Force reloading...")
                # Simulate Ctrl+Shift+R (Hard Reload) by clearing cache
                try:
                    client = await page.context.new_cdp_session(page)
                    await client.send('Network.clearBrowserCache')
                    print("[LOGIN] Browser cache cleared (Hard Reload simulation)")
                except Exception as cdp_err:
                    print(f"[LOGIN] Could not clear cache: {cdp_err}")
                
                # Proceed to next attempt loop which does reload/re-nav
                continue
            
            # Wait for page to stabilize
            await page.wait_for_timeout(1000)
            
            # === STEP 2: Check if Already Logged In ===
            current_url = page.url
            print(f"[LOGIN] Current URL: {current_url}")
            
            if "dashboard" in current_url or "tms/me" in current_url or "tms/client" in current_url:
                # CRITICAL: Verify it's actually the dashboard and not a redirect-in-progress or login masking
                try:
                    await page.wait_for_selector("app-client-dashboard, .user-profile, .row .card", timeout=5000)
                    print("[LOGIN] ✅ Already logged in (Dashboard elements detected)")
                    return True
                except:
                    print(f"[LOGIN] ⚠️ URL says dashboard but no elements found. Assuming false positive (Login needed).")
                    # Force navigation back to login page because we are stuck on a broken /dashboard view
                    try:
                        print(f"[LOGIN] Redirecting to {login_url} to ensure login form loads...")
                        await page.goto(login_url, wait_until='domcontentloaded', timeout=20000)
                    except Exception as nav_e:
                        print(f"[LOGIN] Failed to redirect to login: {nav_e}")
                    # Fall through to login inputs
            
            # === STEP 3: Fill Username ===
            print("[LOGIN] Step 3: Filling username...")
            username_selectors = [
                'input[placeholder="Client Code/ User Name"]',
                'input[name="username"]',
                'input[formcontrolname="username"]',
                '#username',
            ]
            
            # Wait for ANY username field to appear
            try:
                combined_selector = ", ".join(username_selectors)
                print(f"[LOGIN] Waiting for username field to appear (Timeout: 30s)...")
                await page.wait_for_selector(combined_selector, state='visible', timeout=30000)
            except Exception as e:
                print(f"[LOGIN] ❌ Username field did not appear in time: {e}")
                continue

            username_filled = False
            for selector in username_selectors:
                try:
                    username_loc = page.locator(selector).first
                    if await username_loc.count() > 0:
                        await username_loc.fill(username)
                        print(f"[LOGIN] Username filled using: {selector}")
                        username_filled = True
                        break
                except Exception as e:
                    continue
            
            if not username_filled:
                print("[LOGIN] ❌ Failed to fill username (even after wait)")
                continue
            
            # === STEP 4: Fill Password ===
            print("[LOGIN] Step 4: Filling password...")
            password_selectors = [
                '#password-field',
                'input[name="password"]',
                'input[type="password"]',
                'input[formcontrolname="password"]',
            ]
            
            password_filled = False
            for selector in password_selectors:
                try:
                    password_loc = page.locator(selector).first
                    if await password_loc.count() > 0:
                        await password_loc.wait_for(state='visible', timeout=5000)
                        await password_loc.fill(password)
                        print(f"[LOGIN] Password filled using: {selector}")
                        password_filled = True
                        break
                except Exception as e:
                    continue
            
            if not password_filled:
                print("[LOGIN] ❌ Could not find password field")
                continue
            
            # === STEP 5: Solve Captcha ===
            print("[LOGIN] Step 5: Solving captcha...")
            captcha_text = await solve_captcha(page, api_key)
            
            # Validate Captcha Response
            if not captcha_text or len(captcha_text) > 8 or "unable" in captcha_text.lower() or " " in captcha_text:
                print(f"[LOGIN] ❌ Invalid captcha solution: '{captcha_text}' (Length: {len(captcha_text) if captcha_text else 0})")
                
                # Logic to retry immediately? Or just fail attempt and reload page
                # Refresh to get new captcha is best
                print("[LOGIN] Reloading page to get fresh captcha...")
                try:
                    await page.reload(wait_until='domcontentloaded', timeout=20000)
                except: pass
                continue
            
            # Fill captcha input
            captcha_input_selectors = ['#captchaEnter', 'input[name="captcha"]', 'input[placeholder*="Captcha"]']
            captcha_filled = False
            
            for selector in captcha_input_selectors:
                try:
                    captcha_input = page.locator(selector).first
                    if await captcha_input.count() > 0:
                        await captcha_input.fill(captcha_text)
                        print(f"[LOGIN] Captcha filled: '{captcha_text}'")
                        captcha_filled = True
                        break
                except:
                    continue
            
            if not captcha_filled:
                print("[LOGIN] ❌ Could not find captcha input")
                continue
            
            # === STEP 6: Click Login Button ===
            print("[LOGIN] Step 6: Clicking login button...")
            login_button_selectors = [
                '.login__button',
                'button[type="submit"]',
                'button.btn-primary:has-text("Login")',
                'button:has-text("Login")',
            ]
            
            login_clicked = False
            for selector in login_button_selectors:
                try:
                    login_btn = page.locator(selector).first
                    if await login_btn.count() > 0 and await login_btn.is_visible():
                        await login_btn.click()
                        print(f"[LOGIN] Login button clicked: {selector}")
                        login_clicked = True
                        break
                except:
                    continue
            
            if not login_clicked:
                print("[LOGIN] ❌ Could not click login button")
                continue
            
            # === STEP 7: Verify Login Success ===
            print("[LOGIN] Step 7: Waiting for login result...")
            
            try:
                # Wait for a dashboard element OR the login page again (failure)
                # Success elements: .user-avatar, .dashboard-container, app-client-dashboard
                await page.wait_for_selector("app-client-dashboard, .user-profile, .row .card", timeout=15000)
                
                # Double check - sometimes we see elements but are still on login? No, wait_for_selector is safe.
                print("[LOGIN] ✅ Login SUCCESS! (Dashboard detected)")
                return True
                
            except Exception:
                # Check if we are still on login page or have error
                if "dashboard" in page.url and await page.locator("app-login").count() > 0:
                     print(f"[LOGIN] ❌ False positive detected: URL is '{page.url}' but Login Form is visible!")
                
                print("[LOGIN] Still on login page or failed to load dashboard elements")
                
                # Check for error messages using toast capture
                print("[LOGIN] Checking for toast/popup messages...")
                await log_toasts(page, prefix="[LOGIN][TOAST]")
                
                error_msg = await capture_all_popups(page)
                if error_msg:
                    print(f"[LOGIN] ⚠️ Error from TMS: {error_msg}")
                    
                    # Check if it's a captcha error (retry-able)
                    if "captcha" in error_msg.lower() or "invalid" in error_msg.lower():
                        print("[LOGIN] Captcha error - will retry with new captcha")
                
                # Still on login page - check if login form is still visible
                if "login" in current_url.lower():
                    print("[LOGIN] Still on login page - login may have failed")
                
            except Exception as wait_err:
                print(f"[LOGIN] Wait error: {wait_err}")
            
        except Exception as e:
            error_msg = str(e)
            print(f"[LOGIN] ❌ Exception during attempt: {error_msg[:100]}")
            
            # Categorize error for better handling
            if "net::ERR_ABORTED" in error_msg:
                print("[LOGIN] Page crash detected - need fresh page")
                return False  # Signal to main.py to recreate page
            elif "Timeout" in error_msg:
                print("[LOGIN] Timeout - TMS server may be slow")
            elif "Target closed" in error_msg:
                print("[LOGIN] Browser context closed")
                return False
        
        # === RETRY PREPARATION ===
        if attempt < max_retries:
            print(f"[LOGIN] Preparing for retry {attempt + 1}...")
            try:
                await page.reload(wait_until='domcontentloaded', timeout=15000)
                await page.wait_for_timeout(1500)
            except Exception as reload_err:
                print(f"[LOGIN] ❌ Reload failed: {reload_err}")
                # If reload fails, signal for page recreation
                return False
    
    print("[LOGIN] ❌ All login attempts exhausted")
    return False

async def get_toggle_state(page):
    """
    Get the current toggle state.
    Returns 'buy', 'sell', 'neutral', or None if not found.
    """
    try:
        # Check parent container classes first (fastest)
        container_class = await page.evaluate("""() => {
            const container = document.querySelector('.box-order-entry');
            return container ? container.className : '';
        }""")
        
        if "box-buy" in container_class:
            return "buy"
        if "box-sell" in container_class:
            return "sell"
            
        # Fallback to checking active wrapper
        result = await page.evaluate("""() => {
            const wrappers = document.querySelectorAll('app-three-state-toggle .xtoggler-btn-wrapper, .toggler-btn-wrapper');
            for (let i = 0; i < wrappers.length; i++) {
                if (wrappers[i].classList.contains('is-active')) {
                    if (i === 0) return 'sell'; // Left is usually Sell
                    if (i === wrappers.length - 1) return 'buy'; // Right is usually Buy
                    return 'neutral';
                }
            }
            return null;
        }""")
        return result
    except Exception as e:
        print(f"[UTILS] Error getting toggle state: {e}")
        return None

async def set_toggle_position(page, action):
    """
    Set the Buy/Sell toggle to the specified position.
    
    Args:
        page: Playwright page object
        action: 'buy' or 'sell'
        
    Returns:
        bool: True if successful, False otherwise
    """
    action = action.lower()
    if action not in ['buy', 'sell']:
        print(f"[UTILS] Invalid action: {action}")
        return False
        
    print(f"[UTILS] Setting toggle to: {action.upper()}")
    
    try:
        # Wait for toggle to be present using broad selector to support multiple versions
        # Documentation says `app-three-state-toggle`
        await page.wait_for_selector("app-three-state-toggle", timeout=10000)
    except:
        print("[UTILS] Toggle component not found (timeout)")
        return False

    # Check current state first
    current_state = await get_toggle_state(page)
    if current_state == action:
        print(f"[UTILS] Toggle already set to {action.upper()}")
        return True

    # Try standard click first
    try:
        # Determine index: 0 for Sell, -1 for Buy based on doc
        # "Sell" is Left (0), "Buy" is Right (Last/2)
        if action == 'sell':
            index = 0
            # Also try text locator
            text_locator = page.locator("label.order__options--sell, label:has-text('Sell')").first
        else: # buy
            index = -1 # Playwright uses count-1 or nth(-1) logic manually
            text_locator = page.locator("label.order__options--buy, label:has-text('Buy')").first
            
        # Strategy 1: Click the specific position wrapper
        # The documentation highlights .xtoggler-btn-wrapper
        # But existing code also used .toggler-btn-wrapper. We'll try both.
        
        wrappers = page.locator("app-three-state-toggle .xtoggler-btn-wrapper, app-three-state-toggle .toggler-btn-wrapper")
        count = await wrappers.count()
        
        if count >= 2:
            target_index = 0 if action == 'sell' else count - 1
            await wrappers.nth(target_index).click(force=True)
            print(f"[UTILS] Clicked wrapper index {target_index}")
            await page.wait_for_timeout(500)
            
            if await get_toggle_state(page) == action:
                return True
        else:
            print(f"[UTILS] Found only {count} toggle wrappers, unexpected.")

    except Exception as e:
        print(f"[UTILS] Click strategy failed: {e}")

    # Strategy 2: Javascript Injection (Most reliable per doc)
    try:
        print("[UTILS] Trying JS injection strategy...")
        success = await page.evaluate(f"""(action) => {{
            const toggler = document.querySelector('app-three-state-toggle');
            if (!toggler) return false;
            
            // support both class names just in case
            const wrappers = toggler.querySelectorAll('.xtoggler-btn-wrapper, .toggler-btn-wrapper');
            if (wrappers.length < 2) return false;
            
            const index = action === 'buy' ? wrappers.length - 1 : 0;
            const target = wrappers[index];
            
            if (target) {{
                // Click the wrapper
                target.click();
                
                // Find and click internal radio if present
                const radio = target.querySelector('input[type="radio"]');
                if (radio) {{
                    radio.checked = true;
                    radio.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    radio.dispatchEvent(new Event('click', {{ bubbles: true }}));
                }}
                
                return true;
            }}
            return false;
        }}""", action)
        
        await page.wait_for_timeout(500)
        
        if await get_toggle_state(page) == action:
            print(f"[UTILS] JS injection success")
            return True
            
    except Exception as e:
        print(f"[UTILS] JS strategy failed: {e}")

    # Final check
    final_state = await get_toggle_state(page)
    if final_state == action:
        # User Request: Check if the BUY/SELL button appeared
        # Image shows a blue button with text "BUY" (or likely "SELL")
        btn_text = "BUY" if action == "buy" else "SELL"
        print(f"[UTILS] Checking if {btn_text} button appeared...")
        
        try:
            # Look for button with specific text
            # Broad selectors to catch it
            btn_selectors = [
                f"button:has-text('{btn_text}')",
                f"button[type='submit']:has-text('{btn_text}')",
                ".box-order-entry button.btn-primary",
                ".order__form button.btn-primary"
            ]
            
            button_found = False
            for selector in btn_selectors:
                if await page.locator(selector).count() > 0:
                    btn = page.locator(selector).first
                    if await btn.is_visible():
                        txt = await btn.text_content()
                        if btn_text in txt.upper():
                            print(f"[UTILS] ✅ {btn_text} button appeared and is visible")
                            button_found = True
                            break
            
            if not button_found:
                 print(f"[UTILS] ⚠️ Toggle State check passed, but {btn_text} button NOT found/visible yet")
                 
        except Exception as e:
            print(f"[UTILS] Error checking button visibility: {e}")
            
        return True
        
    print(f"[UTILS] Failed to set toggle to {action}. Stuck at: {final_state}")
    return False

async def set_symbol(page, symbol):
    """
    Manually enters the symbol into the order entry form.
    Returns True if successful, False otherwise.
    """
    print(f"[UTILS] Setting symbol to: {symbol}")
    try:
        # 1. Find input field
        # Selectors based on common Angular forms in TMS
        input_selectors = [
            "input[formcontrolname='companyName']",
            "input[placeholder*='Symbol']",
            "input[placeholder*='Company']",
            ".k-autocomplete input",
            "kendo-autocomplete input"
        ]
        
        inp = None
        for selector in input_selectors:
            try:
                if await page.locator(selector).count() > 0:
                    inp = page.locator(selector).first
                    print(f"[UTILS] Found symbol input: {selector}")
                    break
            except: continue
            
        if not inp:
            print("[UTILS] Could not find symbol input field")
            return False
            
        # 2. Clear and Type
        await inp.click()
        await inp.clear()
        
        # Type slowly to trigger autocomplete
        await page.wait_for_timeout(200)
        await inp.type(symbol, delay=100)
        
        # 3. Wait for Dropdown Options
        print("[UTILS] Waiting for dropdown suggestions...")
        
        # Just wait a bit for network/processing
        await page.wait_for_timeout(1000)
        
        # 4. click the item
        # Try finding strict match first, then loose match
        
        # Strategy A: Click the first item in the dropdown list (usually the best match)
        # TMS often uses kendo-popup or .dropdown-menu
        
        # Wait for any popup/list item
        try:
             # Common container for these lists
             await page.wait_for_selector(".k-list-container, .dropdown-menu, .k-popup", timeout=5000)
        except:
             print("[UTILS] Dropdown container did not appear")
             
        # Look for the item
        clicked = False
        item_selectors = [
            f"li:has-text('{symbol}')", # generic li
            f".k-item:has-text('{symbol}')", # kendo item
            f"a:has-text('{symbol}')", # link item
            ".k-list-item" # fallback to first item
        ]
        
        for selector in item_selectors:
            try:
                items = page.locator(selector)
                count = await items.count()
                if count > 0:
                    # Prefer exact match if possible, otherwise first
                    # Loop to find exact match if multiple
                    target = items.first
                    for i in range(count):
                        txt = await items.nth(i).text_content()
                        if txt and symbol.upper() in txt.upper():
                            target = items.nth(i)
                            if symbol.upper() == txt.strip().split()[0]: # Perfect match at start
                                break
                    
                    await target.click()
                    print(f"[UTILS] Clicked symbol dropdown item: {selector}")
                    clicked = True
                    break
            except: continue
            
        if not clicked:
            print("[UTILS] Could not find/click symbol in dropdown. Trying Tab key...")
            await inp.press("Tab")
            
        # 5. Validation - Wait for price/qty fields to potentially enable or check input value
        await page.wait_for_timeout(500)
        
        # Verify value in input
        val = await inp.input_value()
        if symbol.upper() in val.upper():
            print(f"[UTILS] Symbol set confirmed: {val}")
            return True
        else:
            print(f"[UTILS] Symbol set mismatch? Input has: {val}")
            return False

    except Exception as e:
        print(f"[UTILS] Error setting symbol: {e}")
        return False

