from .utils import perform_login as utils_login

def login(driver, username, password, api_key, tms_url):
    """
    Wrapper for login logic.
    """
    return utils_login(driver, username, password, api_key, tms_url)
