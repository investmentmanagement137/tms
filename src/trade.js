import { chromium } from 'playwright';
import * as fs from 'fs';
import * as path from 'path';
import { fileURLToPath } from 'url';
import { GoogleGenerativeAI } from '@google/generative-ai';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const rootDir = path.resolve(__dirname, '../'); // Assuming src/trade.js
const secretsPath = path.resolve(rootDir, 'secrets.json');
const authPath = path.resolve(rootDir, 'auth.json');

// --- CONFIGURATION ---
// You can modify this or pass arguments
const TRADE = {
    action: 'Buy',        // 'Buy' or 'Sell'
    instrument: 'MF',
    symbol: 'NICFC',      // Changed to match recent logs or keep SFEF
    quantity: '100',
    price: '8.8'
};

const URLS = {
    base: 'https://tms43.nepsetms.com.np',
    orderEntry: 'https://tms43.nepsetms.com.np/tms/me/memberclientorderentry'
};

// --- CREDENTIALS ---
let username = '';
let password = '';
let geminiKey = '';

// Load from secrets.json
if (fs.existsSync(secretsPath)) {
    try {
        const secrets = JSON.parse(fs.readFileSync(secretsPath, 'utf8'));
        // Try mapped keys first (id, password, gemini_api_key matches Python scripts)
        username = secrets.id || secrets.TMS_USERNAME || '';
        password = secrets.password || secrets.TMS_PASSWORD || '';
        geminiKey = secrets.gemini_api_key || secrets.GEMINI_API_KEY || '';

        if (secrets.TMS_URL) URLS.base = secrets.TMS_URL.replace(/\/$/, '');
        URLS.orderEntry = `${URLS.base}/tms/me/memberclientorderentry`;
    } catch (e) {
        console.error("Error reading secrets.json:", e);
    }
}

if (!username || !password || !geminiKey) {
    console.error("❌ Missing credentials in secrets.json (Compatible keys: id/TMS_USERNAME, password/TMS_PASSWORD, gemini_api_key/GEMINI_API_KEY)");
    process.exit(1);
}

// --- HELPER FUNCTIONS ---
async function solveCaptcha(page) {
    console.log('Solving Captcha...');
    try {
        const captchaEl = page.locator('img.captcha-image-dimension');
        if (await captchaEl.count() === 0) return null;

        await captchaEl.waitFor({ state: 'visible', timeout: 5000 });
        const buffer = await captchaEl.screenshot();

        const genAI = new GoogleGenerativeAI(geminiKey);
        const model = genAI.getGenerativeModel({ model: "gemini-2.0-flash" });
        const result = await model.generateContent(["Return ONLY the alphanumeric text.", { inlineData: { data: buffer.toString('base64'), mimeType: "image/png" } }]);
        const text = result.response.text();
        return text.trim().replace(/ /g, '').toLowerCase();
    } catch (e) {
        console.log("Captcha error:", e.message);
        return null;
    }
}

async function login(page, context) {
    console.log('Login Check...');
    // Check if already logged in
    try {
        await page.waitForFunction(() => window.location.href.includes('dashboard'), null, { timeout: 3000 });
        console.log('✅ Already Logged In.');
        return true;
    } catch (e) { }

    // Needs Login
    console.log('Performing Login...');
    try {
        if (await page.locator('input[placeholder="Client Code/ User Name"]').count() > 0) {
            await page.fill('input[placeholder="Client Code/ User Name"]', username);
            await page.fill('input[id="password-field"]', password);
        }
    } catch (e) {
        // Maybe already on dashboard but timing issue?
    }

    for (let attempts = 0; attempts < 3; attempts++) {
        const captcha = await solveCaptcha(page);
        if (captcha) {
            console.log(`Captcha Attempt ${attempts + 1}: ${captcha}`);
            await page.fill('input[id="captchaEnter"]', captcha);
            // FIX: Always use Enter key
            await page.keyboard.press('Enter');

            try {
                await page.waitForFunction(() => window.location.href.includes('dashboard'), null, { timeout: 15000 });
                console.log('✅ Login Successful.');
                if (authPath) await context.storageState({ path: authPath });
                return true;
            } catch (e) { console.log('Login wait timed out, retrying...'); }
        }
        await page.reload();
        await page.waitForTimeout(2000);
    }
    return false;
}

// --- MAIN SCRIPT ---
(async () => {
    try {
        console.log('🚀 Launching Final Trade Script (JavaScript)...');

        // Use Playwright directly
        const browser = await chromium.launch({ headless: false, args: ['--start-maximized'] });
        const context = await browser.newContext({ viewport: null });
        const page = await context.newPage();

        // Load Session
        if (fs.existsSync(authPath)) {
            try {
                const state = JSON.parse(fs.readFileSync(authPath, 'utf8'));
                if (state.cookies) await context.addCookies(state.cookies);
            } catch (e) { }
        }

        // 1. LOGIN
        await page.goto(URLS.base);
        if (!await login(page, context)) {
            console.error('❌ Login Failed after retries.');
            return;
        }

        // 2. NAVIGATE TO ORDER ENTRY
        console.log('Navigating to Order Entry...');
        const orderUrl = `${URLS.base}/tms/me/memberclientorderentry`;
        if (!page.url().includes('memberclientorderentry')) {
            await page.goto(orderUrl);
        }
        await page.waitForSelector('.form-inst', { timeout: 20000 });
        await page.waitForTimeout(1000);

        // 3. TOGGLE ACTION (Using Index Strategy)
        console.log(`Setting Action: ${TRADE.action.toUpperCase()}`);
        const toggler = page.locator('app-three-state-toggle');

        // Wait for toggle
        try {
            await toggler.waitFor({ state: 'visible', timeout: 20000 });
        } catch (e) {
            console.log("Toggle wait timeout!");
        }

        if (await toggler.count() > 0) {
            const wrappers = toggler.locator('.xtoggler-btn-wrapper');
            const count = await wrappers.count(); // Should be 3
            if (count >= 3) {
                const index = TRADE.action.toLowerCase() === 'buy' ? 2 : 0; // 0=Sell, 2=Buy

                // Retry click logic
                for (let i = 0; i < 3; i++) {
                    const isActive = await wrappers.nth(index).getAttribute('class').then(c => c.includes('is-active'));
                    if (!isActive) {
                        console.log(`Clicking toggle index ${index}...`);
                        await wrappers.nth(index).click({ force: true });
                        await page.waitForTimeout(1000);
                    } else {
                        console.log(`Action confirmed set to ${TRADE.action}.`);
                        break;
                    }
                }
            }
        }

        // 4. FILL FORM (Using Tab Navigation Strategy)
        console.log('Filling Form...');

        // Instrument
        await page.selectOption('.form-inst', { label: TRADE.instrument });
        await page.waitForTimeout(500);

        // Symbol (Type & Select)
        await page.focus('.form-inst');
        await page.keyboard.press('Tab'); // Move to Symbol

        await page.keyboard.type(TRADE.symbol, { delay: 100 });
        await page.waitForTimeout(1000); // Wait for dropdown

        // Select logic
        await page.keyboard.press('ArrowDown');
        await page.keyboard.press('Enter');
        console.log(`Symbol ${TRADE.symbol} selected.`);

        await page.waitForTimeout(1000); // Wait for price fetch

        // Quantity & Price (Move with Tab)
        // Note: Sometimes we need another tab to get past available quantity display?
        // Logic: Focus Symbol -> Tab -> Quantity

        await page.keyboard.press('Tab'); // Move to Qty
        await page.keyboard.type(TRADE.quantity, { delay: 50 });
        console.log(`Qty ${TRADE.quantity} typed.`);

        await page.keyboard.press('Tab'); // Move to Price
        // Better strategy for inputs with values: Select All + Type
        await page.keyboard.down('Control');
        await page.keyboard.press('A');
        await page.keyboard.up('Control');
        await page.keyboard.press('Backspace');
        await page.keyboard.type(TRADE.price, { delay: 50 });
        console.log(`Price ${TRADE.price} typed.`);

        await page.waitForTimeout(500);

        // 5. SUBMIT
        console.log('Submitting Order...');
        // Let's click the specific button.
        const submitBtn = page.locator('button[type="submit"]').first();
        if (await submitBtn.count() > 0) {
            await submitBtn.click();
        } else {
            // Fallback
            await page.keyboard.press('Enter');
        }

        // 6. CONFIRMATION
        await page.waitForTimeout(1000);

        // Confirmation dialog often has "BUY" or "SELL" button matching the action
        const confirmSelectors = [
            `button:has-text("${TRADE.action.toUpperCase()}")`, // "BUY"
            `button:has-text("${TRADE.action}")`,               // "Buy"
            `button:has-text("Confirm")`,
            `button:has-text("Yes")`
        ];

        let clickedConfirm = false;
        for (const selector of confirmSelectors) {
            // We want to avoid clicking the main form submit button again if it's still visible
            // But usually modal is on top.
            // Let's look for a button that is visible.
            const btn = page.locator(selector).last(); // Often the confirmation is the last one added to DOM

            // Or look for button inside a modal/dialog if possible, but generic is okay for now
            // Just filtered by specific text.
            if (await btn.count() > 0 && await btn.isVisible()) {
                console.log(`Found Confirmation Button: ${selector}`);
                await btn.click();
                clickedConfirm = true;
                break;
            }
        }

        if (!clickedConfirm) {
            console.log('⚠️ No specific confirmation button found (BUY/Confirm). Checked multiple selectors.');
        }

        console.log('✅ ALL STEPS DONE.');

        // Keep browser open for a bit to verify
        // setInterval(() => { }, 1000); 
        // We probably shouldn't keep it open infinitely in this agent run, forcing timeout.
        // But user code had setInterval. 
        // I will wait 10 seconds then close.
        await page.waitForTimeout(10000);
        await browser.close();

    } catch (e) {
        console.error('Final Script Error:', e);
    }
})();
