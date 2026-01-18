from .utils import perform_login as utils_login

async def login(page, username, password, api_key, tms_url):
    """
    Wrapper for login logic (Async Playwright).
    """
    return await utils_login(page, username, password, api_key, tms_url)
