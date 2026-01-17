/**
 * BROWSERLESS.IO TEST SCRIPT
 * 
 * Instructions:
 * 1. Go to https://chrome.browserless.io/
 * 2. Paste your API key: 2To6qH78Sfku5YD24ba34fadec8da31d0b68eef0f1825147d
 * 3. Paste this code in the editor
 * 4. Click "Run"
 * 
 * This will test if TMS is accessible through Browserless
 */

const puppeteer = require('puppeteer');

module.exports = async ({ page, context }) => {
    console.log('Starting TMS Login Test...');

    try {
        // Navigate to TMS Login
        console.log('Navigating to TMS43...');
        await page.goto('https://tms43.nepsetms.com.np/login', {
            waitUntil: 'networkidle2',
            timeout: 30000
        });

        // Wait for page load
        await page.waitForTimeout(3000);

        // Check page title
        const title = await page.title();
        console.log('Page Title:', title);

        // Check for 403 Forbidden
        const bodyText = await page.evaluate(() => document.body.innerText);
        if (bodyText.includes('403') || bodyText.includes('Forbidden')) {
            console.log('❌ 403 FORBIDDEN DETECTED!');
            console.log('Browserless IP is blocked by TMS');
            return {
                success: false,
                error: '403 Forbidden',
                title: title
            };
        }

        // Check for login form elements
        const hasUsername = await page.$('input[placeholder*="Client Code"]') !== null;
        const hasPassword = await page.$('#password-field') !== null;
        const hasCaptcha = await page.$('.captcha-image-dimension') !== null;

        console.log('Login Form Check:');
        console.log('  Username field:', hasUsername ? '✓' : '✗');
        console.log('  Password field:', hasPassword ? '✓' : '✗');
        console.log('  Captcha image:', hasCaptcha ? '✓' : '✗');

        if (hasUsername && hasPassword && hasCaptcha) {
            console.log('✅ Page loaded successfully! All elements present.');

            // Take screenshot
            const screenshot = await page.screenshot({ encoding: 'base64' });

            return {
                success: true,
                title: title,
                formElements: {
                    username: hasUsername,
                    password: hasPassword,
                    captcha: hasCaptcha
                },
                screenshot: screenshot.substring(0, 100) + '...' // Truncate for display
            };
        } else {
            console.log('⚠️ Page loaded but form elements missing');
            return {
                success: false,
                error: 'Missing form elements',
                formElements: {
                    username: hasUsername,
                    password: hasPassword,
                    captcha: hasCaptcha
                }
            };
        }

    } catch (error) {
        console.error('Error during test:', error.message);
        return {
            success: false,
            error: error.message
        };
    }
};
