import zipfile
from urllib.parse import urlparse

# ... (imports) ...

def get_proxy_auth_extension(proxy_url):
    """Creates a Chrome extension to handle proxy authentication."""
    parsed = urlparse(proxy_url)
    host = parsed.hostname
    port = parsed.port
    user = parsed.username
    password = parsed.password

    manifest_json = """
    {
        "version": "1.0.0",
        "manifest_version": 2,
        "name": "Chrome Proxy",
        "permissions": [
            "proxy",
            "tabs",
            "unlimitedStorage",
            "storage",
            "<all_urls>",
            "webRequest",
            "webRequestBlocking"
        ],
        "background": {
            "scripts": ["background.js"]
        },
        "minimum_chrome_version":"22.0.0"
    }
    """

    background_js = """
    var config = {
            mode: "fixed_servers",
            rules: {
              singleProxy: {
                scheme: "http",
                host: "%s",
                port: parseInt(%s)
              },
              bypassList: ["localhost"]
            }
          };

    chrome.proxy.settings.set({value: config, scope: "regular"}, function() {});

    function callbackFn(details) {
        return {
            authCredentials: {
                username: "%s",
                password: "%s"
            }
        };
    }

    chrome.webRequest.onAuthRequired.addListener(
                callbackFn,
                {urls: ["<all_urls>"]},
                ['blocking']
    );
    """ % (host, port, user, password)

    plugin_file = 'proxy_auth_plugin.zip'
    with zipfile.ZipFile(plugin_file, 'w') as zp:
        zp.writestr("manifest.json", manifest_json)
        zp.writestr("background.js", background_js)
    
    return plugin_file

async def main():
    async with Actor:
        print("Actor Starting...")
        
        # ... (Inputs) ...
        # (Copy previous input logic here - abbreviated for brevity in replacement)
        actor_input = await Actor.get_input() or {}
        tms_website_url = actor_input.get('tmsWebsiteUrl', os.environ.get('TMS_WEBSITE_URL', 'https://tms58.nepsetms.com.np/login'))
        tms_login_id = actor_input.get('tmsLoginId', os.environ.get('TMS_LOGIN_ID'))
        tms_password = actor_input.get('tmsPassword', os.environ.get('TMS_PASSWORD'))
        gemini_api_key = actor_input.get('geminiApiKey', os.environ.get('GEMINI_API_KEY'))
        action = actor_input.get('action', os.environ.get('ACTION', 'EXTRACT_TRADEBOOK'))
        history_months = actor_input.get('historyDurationMonths', int(os.environ.get('HISTORY_MONTHS', 12)))
        order_details = actor_input.get('orderDetails', {})
        proxy_config_input = actor_input.get('proxyConfiguration')

        # Headless Configuration
        is_headless = os.environ.get("HEADLESS", "true").lower() == "true"

        if not tms_login_id or not tms_password:
            print("ERROR: Missing TMS Login ID or Password.")
            await Actor.fail(status_message="Missing Credentials")
            return
        
        if not gemini_api_key:
            print("WARNING: Missing Gemini API Key. Captcha solving might fail if strictly required.")

        print(f"Configuration: URL={tms_website_url}, User: {tms_login_id}, Action: {action}, Headless: {is_headless}, Months: {history_months}")

        # 2. Setup Selenium & Proxy
        chrome_options = Options()
        if is_headless:
            # Note: Extension support in Headless mode can be tricky. 
            # Standard 'headless' might not support extensions.
            # 'headless=new' is recommended for newer Chrome versions logic.
            chrome_options.add_argument("--headless=new") 
        
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")
        
        # Proxy Setup
        if proxy_config_input:
            print("[DEBUG] Proxy configuration found. Setting up proxy...")
            proxy_configuration = await Actor.create_proxy_configuration(actor_proxy_input=proxy_config_input)
            if proxy_configuration:
                proxy_url = await proxy_configuration.new_url()
                if proxy_url:
                    print(f"[DEBUG] Generated Proxy URL: {proxy_url}")
                    # Check for auth
                    parsed = urlparse(proxy_url)
                    if parsed.username and parsed.password:
                         print("[DEBUG] Authenticated Proxy detected. Injecting helper extension...")
                         try:
                             extension_path = get_proxy_auth_extension(proxy_url)
                             chrome_options.add_extension(extension_path)
                         except Exception as ext_err:
                             print(f"[DEBUG] Failed to create proxy extension: {ext_err}. Fallback to arg...")
                             chrome_options.add_argument(f'--proxy-server={proxy_url}')
                    else:
                         print("[DEBUG] Non-authenticated proxy. Using standard arg.")
                         chrome_options.add_argument(f'--proxy-server={proxy_url}')
                else:
                     print("[DEBUG] Proxy URL generation failed (None returned). Running without proxy.")
            else:
                print("[DEBUG] Failed to create proxy configuration.")
        else:
            print("[DEBUG] No proxy configuration provided.")

        print("Launching Chrome...")
        # ... (Driver init) ...
        try:
             service = Service(ChromeDriverManager().install())
             driver = webdriver.Chrome(service=service, options=chrome_options)
        except:
             driver = webdriver.Chrome(options=chrome_options)

        client = TMSClient(driver)
        
        try:
            # 3. Login
            login_url = tms_website_url
            success = perform_login(driver, tms_login_id, tms_password, gemini_api_key, login_url)
            
            if not success:
                await Actor.fail(status_message="Login Failed")
                return

            # 4. Perform Action
            result_data = {}
            
            if action == "EXTRACT_TRADEBOOK":
                data = client.extract_tradebook(months=history_months)
                result_data = {"tradebook": data}
                print(f"Extracted {len(data)} rows.")
                
            elif action == "BUY":
                symbol = order_details.get('symbol')
                qty = order_details.get('quantity')
                price = order_details.get('price')
                res = client.place_order("BUY", symbol, qty, price)
                result_data = res
                
            elif action == "SELL":
                symbol = order_details.get('symbol')
                qty = order_details.get('quantity')
                price = order_details.get('price')
                res = client.place_order("SELL", symbol, qty, price)
                result_data = res
                
            elif action == "EXTRACT_INFO":
                # For now same as tradebook, or add more
                data = client.extract_tradebook()
                result_data = {"info": data}
            
            # 5. Push Data
            await Actor.push_data(result_data)
            print("Data pushed to dataset.")

        except Exception as e:
            print(f"Actor execution failed: {e}")
            await Actor.fail(status_message=str(e))
        finally:
            driver.quit()

if __name__ == '__main__':
    # Need to run async
    asyncio.run(main())
