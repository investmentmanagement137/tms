"""
TMS Toast Capture Utility
=========================

This module provides utilities for capturing toast notifications
from the TMS (Trade Management System) website.

Toast Types Captured:
- Error toasts (red) - e.g., "Invalid - Please select a business date"
- Success toasts (green) - e.g., "Order placed successfully"
- Warning toasts (yellow)
- Info toasts (blue)

Usage:
------
    from toast_capture import capture_toasts
    
    # In your async Playwright script:
    messages = await capture_toasts(page)
    for msg in messages:
        print(f"Toast: {msg}")

Selectors Used:
---------------
The TMS website uses ngx-toastr for notifications. Key selectors:
- #toast-container .toast
- .toast-error, .toast-success, .toast-warning, .toast-info
- .ngx-toastr

Author: TMS Automation Project
"""

import asyncio
from typing import List


async def capture_toasts(page) -> List[str]:
    """
    Captures all visible toast/popup messages from the page.
    
    This function scans for ngx-toastr style notifications that appear
    in the top-right corner of the TMS website. It captures the full
    text content including both title and message.
    
    Args:
        page: Playwright page object
        
    Returns:
        List[str]: List of captured toast message strings
        
    Example:
        >>> messages = await capture_toasts(page)
        >>> # ['Invalid\nPlease select a business date', 'Error\nPrice out of range']
    """
    messages = []
    
    # ngx-toastr selectors used by TMS
    toast_selectors = [
        "#toast-container .toast",   # Container-based selector
        ".toast-error",              # Red error toasts
        ".toast-success",            # Green success toasts
        ".toast-warning",            # Yellow warning toasts
        ".toast-info",               # Blue info toasts
        ".ngx-toastr",               # Angular toastr wrapper
    ]
    
    for selector in toast_selectors:
        try:
            elements = await page.query_selector_all(selector)
            for element in elements:
                if await element.is_visible():
                    # text_content() captures full text including nested elements
                    full_text = await element.text_content()
                    if full_text and full_text.strip():
                        # Avoid duplicates
                        if full_text.strip() not in messages:
                            messages.append(full_text.strip())
        except Exception:
            # Silently continue if selector fails
            pass
    
    return messages


async def wait_for_toast(page, timeout_ms: int = 5000) -> List[str]:
    """
    Waits for a popup/toast to appear and captures its content.
    
    Useful when you expect a popup after an action (like form submission).
    
    Args:
        page: Playwright page object
        timeout_ms: Maximum time to wait in milliseconds (default: 5000)
        
    Returns:
        List[str]: List of captured toast messages
        
    Example:
        >>> await page.click("button[type='submit']")
        >>> messages = await wait_for_toast(page, timeout_ms=3000)
    """
    try:
        # Wait for any toast to appear
        await page.wait_for_selector(
            ".toast, .toast-error, .toast-success, .ngx-toastr",
            timeout=timeout_ms
        )
        # Small delay to ensure toast is fully rendered
        await page.wait_for_timeout(500)
    except Exception:
        pass  # Timeout - no popup appeared
    
    return await capture_toasts(page)


async def log_toasts(page, prefix: str = "[TOAST]") -> None:
    """
    Captures and prints all visible toasts to console.
    
    Convenience function for debugging and logging.
    
    Args:
        page: Playwright page object
        prefix: Log prefix (default: "[TOAST]")
    """
    messages = await capture_toasts(page)
    for msg in messages:
        # Replace newlines for single-line logging
        clean_msg = msg.replace('\n', ' - ')
        print(f"{prefix} {clean_msg}")


async def capture_all_popups(page) -> str:
    """
    Captures all visible popups/toasts and returns a combined message string.
    
    This function scans for both ngx-toastr notifications AND SweetAlert dialogs,
    which are commonly used in TMS for confirmations and error messages.
    
    Args:
        page: Playwright page object
        
    Returns:
        str: Combined popup message string (space-separated)
    """
    messages = []
    
    # Combined selectors: ngx-toastr + SweetAlert + Bootstrap alerts
    popup_selectors = [
        # ngx-toastr selectors
        "#toast-container .toast",
        ".toast-error",
        ".toast-success",
        ".toast-warning", 
        ".toast-info",
        ".ngx-toastr",
        # SweetAlert selectors
        ".swal2-title",
        ".swal2-html-container",
        # Bootstrap alerts
        ".toast-container .toast-message",
        ".toast-message",
        ".toast-body",
        ".alert-danger",
        ".alert-success",
    ]
    
    for selector in popup_selectors:
        try:
            elements = await page.query_selector_all(selector)
            for element in elements:
                if await element.is_visible():
                    full_text = await element.text_content()
                    if full_text and full_text.strip():
                        if full_text.strip() not in messages:
                            messages.append(full_text.strip())
        except Exception:
            pass
    
    return " ".join(messages)


def is_error_message(message: str) -> bool:
    """
    Checks if a toast/popup message indicates an error.
    
    Args:
        message: The toast message string
        
    Returns:
        bool: True if message contains error indicators
    """
    error_keywords = ["error", "failed", "invalid", "rejected", "fail", "exception"]
    return any(keyword in message.lower() for keyword in error_keywords)


def is_success_message(message: str) -> bool:
    """
    Checks if a toast/popup message indicates success.
    
    Args:
        message: The toast message string
        
    Returns:
        bool: True if message contains success indicators
    """
    success_keywords = ["success", "submitted", "completed", "accepted", "placed"]
    return any(keyword in message.lower() for keyword in success_keywords)


# Demo/Test Function
async def demo():
    """
    Demonstrates toast capture on the Order Book History page.
    
    Run this script directly to test:
        python toast_capture.py
    """
    import os
    from playwright.async_api import async_playwright
    
    TMS_URL = "https://tms43.nepsetms.com.np"
    
    if not os.path.exists("auth.json"):
        print("ERROR: auth.json not found. Run main_scraper.py first to login.")
        return
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(storage_state="auth.json")
        page = await context.new_page()
        
        print("Navigating to Order Book History...")
        await page.goto(f"{TMS_URL}/tms/me/order-book-history", timeout=30000)
        await page.wait_for_timeout(3000)
        
        if "login" in page.url:
            print("Session expired. Please re-login.")
            await browser.close()
            return
        
        print("Clicking Search (without date) to trigger popup...")
        try:
            await page.click("button:has-text('Search')", timeout=3000)
        except:
            await page.click("button[type='submit']", timeout=3000)
        
        # Wait for and capture toast
        messages = await wait_for_toast(page, timeout_ms=3000)
        
        print("\n=== CAPTURED TOASTS ===")
        if messages:
            for i, msg in enumerate(messages, 1):
                print(f"{i}. {msg}")
        else:
            print("No toasts detected.")
        
        print("\nClosing in 5 seconds...")
        await page.wait_for_timeout(5000)
        await browser.close()


if __name__ == "__main__":
    asyncio.run(demo())
