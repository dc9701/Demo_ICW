"""
selenium_functions.py.

Description: Functions to interact with Selenium WebDriver.

Classes:
    - None

Functions:
    - tokenGenerator(env=sys.argv[1]): Generates a token for the OTP Auth.
    - click_and_pause(context, web_page_name): Clicks on an element and pauses the execution.
    - open_url(context, url): Opens a URL.
    - web_page_url(context, web_page_name): Returns the URL of a web page.
    - wait_until_clickable(context, element): Waits until an element is clickable.
"""
from dotenv import load_dotenv
import glob
import logging
import os
import re
import pyotp
import sys
import time
from types import SimpleNamespace

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from common.framework import debug_screenshot, failed, get_property
from pages import locators as Page

env_files = glob.glob('*.env')
for env_file in env_files:
    load_dotenv(env_file)

# Get Github Login
GITHUB_USERNAME = os.getenv('GITHUB_USERNAME')
GITHUB_PASSWORD = os.getenv('GITHUB_PASSWORD')

GENERATE_SCERET_BUTTON = "/html/body/div[1]/div[5]/main/div[2]/div[2]/div[6]/div[1]/div/form/input[1]"
CLIENT_SECRET_INPUT_XPATH = "//*[@id='new-oauth-token']"  # noqa> S105 - This is not a password

# Get MFA Token
MFA_TOKEN = os.getenv('MFA_TOKEN')

accountTokens = {
    'dev': MFA_TOKEN
}


def authenticate_with_github(context, element):
    """Authenticate with GitHub either during sign-in or workspace setup."""
    # Save main window to return after handling popup login windows.
    main_window = context.driver.current_window_handle
    click(context, element)

    # Locate the popup login window and switch focus to it, if present.
    if context.driver.window_handles:
        login_popup = None
        time.sleep(5)
        for handle in context.driver.window_handles:
            if handle != main_window:
                login_popup = handle

        if login_popup:
            context.driver.switch_to.window(login_popup)
            time.sleep(2)

            # Retrieve TOTP secret from environment variable
            totp_secret = os.getenv("GITHUB_TOTP_SECRET")
            if not totp_secret:
                raise ValueError("GITHUB_TOTP_SECRET environment variable is not set!")
            totp = pyotp.TOTP(totp_secret)

            # Force-open the GitHub auth URL if it didn't open when click AUTHENTICATE...
            # REGULUS-1884 - 450-aiu-setup fails: We can’t connect to the server at cb740c0b5b3b...
            base_url = get_property(context, 'context.properties.stack.Tags.AiUnlimitedWorkspacesURL') + ":3000/auth/github?"
            print(f"Going to: {base_url}")
            if (not found_element(context, Page.Aiu.signin.username())):
                open_url(context, base_url)
                time.sleep(5)

            # Process username/password + TOTP auth, if needed.
            if (found_element(context, Page.Aiu.signin.username())):
                # Enter GitHub user email & password.
                set(context, Page.Aiu.signin.username(), os.getenv("GITHUB_USERNAME"))
                time.sleep(1)
                set(context, Page.Aiu.signin.password(), os.getenv("GITHUB_PASSWORD"))

                # Click sign-in > use authenticator link & enter authorization code
                time.sleep(15)
                click(context, Page.Aiu.signin.use_authenticator())
                time.sleep(10)
                set(context, Page.Aiu.signin.auth_code(), totp.now())

            # First time through, have a final oauth_authorize step in the still-present popup
            login_popup = None
            time.sleep(5)
            for handle in context.driver.window_handles:
                if handle != main_window:
                    login_popup = handle

            if login_popup:
                context.driver.switch_to.window(login_popup)
                time.sleep(2)
                if (not found_element(context, Page.Aiu.signin.oauth_authorize())):
                    new_url = re.sub(r"(.*?)(&redirect_uri=.*?callback)(.*)", r"\1\3", context.driver.current_url)
                    open_url(context, new_url)

                time.sleep(2)
                if (found_element(context, Page.Aiu.signin.oauth_authorize())):
                    click(context, Page.Aiu.signin.oauth_authorize())

                # Click sign-in > use authenticator link & enter authorization code
                try:
                    time.sleep(10)
                    if (found_element(context, Page.Aiu.signin.use_authenticator())):
                        click(context, Page.Aiu.signin.use_authenticator())
                    time.sleep(5)
                    if (found_element(context, Page.Aiu.signin.auth_code())):
                        set(context, Page.Aiu.signin.auth_code(), totp.now())
                except Exception as e:
                    logging.error(f"Failed to sign-in via authenticator app: {e}")

            # Wait for SSO redirection to complete, then return to main window.
            time.sleep(10)
            context.driver.switch_to.window(main_window)

        # If the Settings icon is clickable, do so.
        time.sleep(5)
        if (found_element(context, Page.Aiu.nav.settings())):
            click(context, Page.Aiu.nav.settings())


def authenticate_with_github_totp(context):
    """
    Authenticate with GitHub using email, password, and TOTP on the recovery page.

    If already logged in, it proceeds to the next steps.
    Requires the `GITHUB_TOTP_SECRET` environment variable for the TOTP secret key.

    Args:
        context: Behave context object.
    """
    # Retrieve TOTP secret from environment variable
    totp_secret = os.getenv("GITHUB_TOTP_SECRET")
    if not totp_secret:
        raise ValueError("GITHUB_TOTP_SECRET environment variable is not set!")

    totp = pyotp.TOTP(totp_secret)

    # Open GitHub login page
    login_url = "https://github.com/login"
    context.driver.get(login_url)

    try:
        # Check if user is already logged in by looking for the profile button
        profile_button_xpath = "/html/body/div[1]/div[1]/header/div/div[2]/div[4]"
        try:
            WebDriverWait(context.driver, 5).until(
                EC.presence_of_element_located((By.XPATH, profile_button_xpath))
            )
            logging.debug("User is already logged in to GitHub. Proceeding to next steps.")
            return  # Exit the function as the user is already logged in
        except TimeoutException:
            logging.debug("User is not logged in. Proceeding with login steps.")

        # Step 1: Enter email
        WebDriverWait(context.driver, 45).until(
            EC.presence_of_element_located((By.ID, "login_field"))
        ).send_keys(os.getenv("GITHUB_USERNAME"))

        # Step 2: Enter password
        WebDriverWait(context.driver, 45).until(
            EC.presence_of_element_located((By.ID, "password"))
        ).send_keys(os.getenv("GITHUB_PASSWORD"))

        # Step 3: Click sign-in button
        WebDriverWait(context.driver, 45).until(
            EC.element_to_be_clickable((By.NAME, "commit"))
        ).click()

        # Step 4: Navigate to the recovery page
        recovery_url = "https://github.com/sessions/two-factor/app"
        context.driver.get(recovery_url)
        logging.debug("Navigated to the GitHub two-factor recovery page.")

        # Step 5: Wait for the recovery code input field
        recovery_input = WebDriverWait(context.driver, 45).until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="app_totp"]'))
        )

        # Step 6: Generate TOTP and enter it
        otp_code = totp.now()
        recovery_input.send_keys(otp_code)

        # Step 7: Verify login success
        WebDriverWait(context.driver, 45).until(
            EC.presence_of_element_located((By.XPATH, profile_button_xpath))
        )
        logging.info("GitHub login successful!")
    except Exception as e:
        logging.error(f"GitHub login failed: {e}")
        raise


def click(context, element: SimpleNamespace):
    """Find an element and clicks on it."""
    find_element_and_click(context, element)


def fill_github_oauth_form(context, app_name, homepage_url, callback_url):
    """
    Fill the GitHub OAuth app creation form.

    Args:
        context: Behave context object.
        app_name (str): Application name.
        homepage_url (str): Homepage URL.
        callback_url (str): Authorization callback URL.
    """
    try:
        # Fill in the fields
        set(context, SimpleNamespace(type=By.ID, id="oauth_application_name"), app_name)
        set(context, SimpleNamespace(type=By.ID, id="oauth_application_url"), homepage_url)
        set(context, SimpleNamespace(type=By.ID, id="oauth_application_callback_url"), callback_url)

        # Click the Register button, if it is visible
        time.sleep(2)
        if (found_element(context, SimpleNamespace(type=By.XPATH, id='//*[@id="new_oauth_application"]/p/button'))):
            click(context, SimpleNamespace(type=By.XPATH, id='//*[@id="new_oauth_application"]/p/button'))
        logging.debug(
            f"Submitted GitHub OAuth app creation form: Name={app_name}, Homepage={homepage_url}, Callback={callback_url}"
        )
    except TimeoutException:
        logging.error("VERIFICATION FAILED: Element 'oauth_application_name' not found or not clickable.")
        raise


def delete_existing_oauth_app(context):
    """
    Delete the existing OAuth App by clicking the 'Advanced' button, then the delete and confirmation buttons.
    """
    # We use an XPath that finds an <a> element containing '/advanced' in its href and with a <span> that has "Advanced" text.
    advanced_button_xpath = "//a[contains(@href, '/advanced') and .//span[contains(text(), 'Advanced')]]"
    wait_until_clickable(context, SimpleNamespace(type=By.XPATH, id=advanced_button_xpath))
    click(context, SimpleNamespace(type=By.XPATH, id=advanced_button_xpath))

    # Click the delete button.
    delete_button_xpath = "/html/body/div[1]/div[5]/main/div[2]/div[2]/div[2]/div/details/summary"
    wait_until_clickable(context, SimpleNamespace(type=By.XPATH, id=delete_button_xpath))
    click(context, SimpleNamespace(type=By.XPATH, id=delete_button_xpath))

    # Click the confirmation delete button.
    confirm_delete_xpath = "/html/body/div[1]/div[5]/main/div[2]/div[2]/div[2]/div/details/details-dialog/div[4]/form/button"
    wait_until_clickable(context, SimpleNamespace(type=By.XPATH, id=confirm_delete_xpath))
    click(context, SimpleNamespace(type=By.XPATH, id=confirm_delete_xpath))

    # Allow time for deletion to complete
    time.sleep(2)


def find_element_and_click(context, element: SimpleNamespace):
    """Find an element and clicks on it (old name)."""
    debug_screenshot(context, element, '_CLICK_')
    wait_until_clickable(context, element)
    if ('ShadowRoot' in element.id):
        query_script = shadow_query_script(context, element.id)
        elem = context.driver.execute_script(query_script)
    else:
        elem = context.driver.find_element(element.type, element.id)

    # Ensure element is visible in the viewport.
    context.driver.execute_script("arguments[0].scrollIntoView(false);", elem)

    # Safari browser handles click() events differently.
    if (context.properties.browser == 'safari'):
        context.driver.execute_script("arguments[0].click();", elem)
    else:
        elem.click()


def find_element_and_send_keys(context, element: SimpleNamespace, keys: str):
    """Find an element and sends keys to it (handles stale element reference)."""
    for _ in range(3):  # Retry logic for handling stale elements
        try:
            debug_screenshot(context, element, '_SET_BEFORE_')
            wait_until_clickable(context, element)
            if 'ShadowRoot' in element.id:
                query_script = shadow_query_script(context, element.id)
                elem = context.driver.execute_script(query_script)
            else:
                elem = context.driver.find_element(element.type, element.id)

            # Ensure element is visible in the viewport.
            context.driver.execute_script("arguments[0].scrollIntoView(false);", elem)

            # Determine how to set value, based upon element type (input or select)
            if ('select' in element.id):  # Select drop-down (e.g., cv-select)
                elem.click()
                time.sleep(0.5)
                find_element_and_click(context, Page.Aiu.settings.application.log_level_item(keys))
                time.sleep(1)

            else:  # Text input (e.g., cv-textfield)
                # Clear any existing content of text input (twice)
                content = get(context, element)
                retries = 3
                while content and retries > 0:
                    elem.click()
                    time.sleep(0.5)
                    elem.send_keys(Keys.END)
                    time.sleep(0.5)
                    for n in content:
                        time.sleep(0.1)
                        elem.send_keys(Keys.BACKSPACE)

                    content = get(context, element)
                    retries -= 1

                # Now type the value into the text input
                elem.send_keys(keys)
                elem.send_keys(Keys.ENTER)

            debug_screenshot(context, element, '_SET_AFTER_')
            return  # Exit if successful
        except StaleElementReferenceException:
            logging.warning("StaleElementReferenceException encountered. Retrying...")
            time.sleep(2)  # Wait before retrying

    raise Exception(f"Failed to send keys to element {element.id} after retries.")


def found_element(context, element: SimpleNamespace):
    """Return true if the elementis found."""
    debug_screenshot(context, element, '_FIND_')
    return len(context.driver.find_elements(element.type, element.id)) > 0


def get(context, element: SimpleNamespace):
    """Get an element's value."""
    elem_value = None
    debug_screenshot(context, element, '_GET_')
    wait_until_clickable(context, element)

    if ('ShadowRoot' in element.id):
        query_script = shadow_query_script(context, element.id) + '.value'
        elem_value = context.driver.execute_script(query_script)

        if not elem_value:
            query_script = shadow_query_script(context, element.id) + '.text'
            elem_value = context.driver.execute_script(query_script)
    else:
        elem = context.driver.find_element(element.type, element.id)
        try:
            elem_value = elem.value
        except Exception:
            try:
                elem_value = elem.text
            except Exception:
                elem_value = ''

    return elem_value


def get_github_oauth_credentials(context):
    """
    Retrieve the generated OAuth credentials.

    Args:
        context: Behave context object.

    Returns:
        dict: A dictionary containing `Client ID` and `Client Secret`.
    """
    stack_name = context.properties.stack_name

    # Locate the link to the app with the matching stack_name
    app_link_xpath = f"//a[@class='text-bold' and contains(text(), '{stack_name}')]"
    wait_until_clickable(context, SimpleNamespace(type=By.XPATH, id=app_link_xpath))
    click(context, SimpleNamespace(type=By.XPATH, id=app_link_xpath))
    logging.debug(f"Clicked on the app link for '{stack_name}'.")

    # Retrieve the Client ID
    client_id_xpath = "/html/body/div[1]/div[5]/main/div[2]/div[2]/code"
    wait_until_clickable(context, SimpleNamespace(type=By.XPATH, id=client_id_xpath))
    client_id = get(context, SimpleNamespace(type=By.XPATH, id=client_id_xpath))
    logging.debug(f"Retrieved Client ID: {client_id}")

    # Click the button to generate a new Client Secret
    # nosec
    generate_secret_button_xpath = GENERATE_SCERET_BUTTON
    wait_until_clickable(context, SimpleNamespace(type=By.XPATH, id=generate_secret_button_xpath))
    click(context, SimpleNamespace(type=By.XPATH, id=generate_secret_button_xpath))
    logging.debug("Clicked the button to generate a new Client Secret.")

    maybe_reauthenticate_github_sudo(context)

    # After the page reloads, retrieve the new Client Secret
    secret_xpath = CLIENT_SECRET_INPUT_XPATH
    wait_until_clickable(context, SimpleNamespace(type=By.XPATH, id=secret_xpath))
    client_secret = get(context, SimpleNamespace(type=By.XPATH, id=secret_xpath))
    logging.debug(f"Retrieved Client Secret: {client_secret}")

    return {"ClientID": client_id, "ClientSecret": client_secret}


def open_url(context, url):
    """Open the specified URL."""
    context.driver.get(url)


def set(context, element: SimpleNamespace, value: str):
    """Set an element's value, handling stale element reference issues."""
    find_element_and_send_keys(context, element, value)


def set_elements(context, elements):
    """
    Set each element in the table to the specified value.

    Args:
        context: Behave context object.
        values: Table of element locators and (optional) values to set.
    """
    if (elements):
        log_failure = False
        set_ok = False
        for row in elements:
            # Elements will usually eval as a locator() starting with 'Page.*', or may be a context property.
            element_name = row['field']
            element = eval(element_name) if element_name and ('Page.' in element_name or 'context.' in element_name) else element_name

            # Values may be literal or an expression including a property reference beginning with 'context.*'; wrap this in a get_property().
            value_str = row['value']
            if (value_str and 'context.' in value_str):
                value_str = re.sub(r"(.*?)(context\.\S+)(.*)", r"\1get_property(context, '\2')\3", value_str)
                try:
                    value = eval(value_str)
                except Exception:
                    value = value_str  # Expression didn't evaluate successfully, so fall back to literal value.
            else:
                value = value_str  # Literal value.

            try:
                wait_until_clickable(context, element)
                log_failure = True
                if (value):
                    try:
                        set(context, element, value)
                        set_ok = True
                    except Exception as e:
                        failed(f"SET FAILED: Element '{element_name}' ({element.id}) could not be set to '{value}'\n{e}")
                        log_failure = False
                        set_ok = False

                    if (set_ok):
                        logging.debug(f"SET OK: Element '{element_name}' set to '{value}'")
                    else:
                        if log_failure:
                            failed(f"SET FAILED: Element '{element_name}' ({element.id}) could not be set to '{value}'")
                        log_failure = False
                else:
                    # TODO: REG-1180 - Support setting blank values.
                    logging.debug(f"SET OK: '{element_name}' value cleared")
            except Exception:
                if log_failure:
                    failed(f"SET FAILED: No such element: {element_name}")
    else:
        logging.warning("No elements listed to set!")


def shadow_query_script(context, element_id: str):
    """
    Returns a JS script to access an element inside a shadow DOM.

    Args:
        context: Behave context object.
        element_id (str): String locator to assemble into a script.

    Returns:
        str: The generated JS query script.  For example:

        element_id:  cv-textfield[name='baseUrl'] ShadowRoot input[name='baseUrl']
         JS script:  return document.querySelector("cv-textfield[name='baseUrl']").shadowRoot.querySelector("input[name='baseUrl']")
    """
    element_ids = element_id.split('ShadowRoot')
    query_script = ''
    # Shadow DOM elements need special handling (up to 4 levels of shadow content nesting, 2 being most common).
    if (len(element_ids) == 2):
        query_script = f'return document.querySelector("{element_ids[0].strip()}")' + \
                       f'.shadowRoot.querySelector("{element_ids[1].strip()}")'
    elif (len(element_ids) == 3):
        query_script = f'return document.querySelector("{element_ids[0].strip()}")' + \
                       f'.shadowRoot.querySelector("{element_ids[1].strip()}")' + \
                       f'.shadowRoot.querySelector("{element_ids[2].strip()}")'
    elif (len(element_ids) == 4):
        query_script = f'return document.querySelector("{element_ids[0].strip()}")' + \
                       f'.shadowRoot.querySelector("{element_ids[1].strip()}")' + \
                       f'.shadowRoot.querySelector("{element_ids[2].strip()}")' + \
                       f'.shadowRoot.querySelector("{element_ids[3].strip()}")'
    else:
        failed(f"VERIFICATION FAILED: Shadow element not found: {element_id}")

    return query_script


def tokenGenerator(env=sys.argv[1]):
    """Generate a token for the OTP Auth."""
    totp = pyotp.TOTP(accountTokens[env])
    otp = totp.now()
    return otp


def verify_elements(context, elements):
    """
    Checks that each element in the table exists and (optionally) matches the specified value.

    Args:
        context: Behave context object.
        values: Table of element locators and (optional) values to compare against.
    """
    if (elements):
        log_failure = False
        for row in elements:
            # Elements will usually eval as a locator() starting with 'Page.*', or may be a context property.
            element_name = row['field']
            element = eval(element_name) if element_name and ('Page.' in element_name or 'context.' in element_name) else element_name

            # Values may be literal or an expression including a property reference beginning with 'context.*'; wrap this in a get_property().
            value_str = row['value']
            if (value_str and 'context.' in value_str):
                value_str = re.sub(r"(.*?)(context\.\S+)(.*)", r"\1get_property(context, '\2')\3", value_str)
                try:
                    value = eval(value_str)
                except Exception:
                    value = value_str  # Expression didn't evaluate successfully, so fall back to literal value.
            else:
                value = value_str  # Literal value.

            try:
                debug_screenshot(context, element, '_VERIFY_')
                wait_until_clickable(context, element)
                log_failure = True
                if (value):
                    elem_value = get(context, element)
                    matches = False

                    # Handle numerics and empty strings separately from regex matches.
                    if value.isnumeric():
                        +elem_value == +value
                    elif value in ['', '""', "''"]:
                        matches = elem_value == ''
                    else:
                        match_1 = re.search(value.lower(), elem_value.lower())
                        match_2 = re.search(elem_value.lower(), value.lower())
                        matches = match_1 or (elem_value and match_2)

                    if (matches):
                        logging.info(f"VERIFIED OK: Element '{element_name}' ({elem_value}) matches '{value}'")
                    else:
                        log_failure = False
                        failed(f"VERIFICATION FAILED: Element '{element_name}' ({elem_value}) does NOT match expected value: '{value}'")
                else:
                    logging.info(f"VERIFIED OK: Element exists: '{element_name}' ({element})")
            except Exception:
                if log_failure:
                    failed(f"VERIFICATION FAILED: No such element: {element_name}")
    else:
        logging.warning("No elements listed to verify!")


def wait_until_clickable(context, element: SimpleNamespace, timeout: int = 45):
    """
    Wait for an element to be clickable within the specified timeout.

    Args:
        context: Behave context object.
        element: A SimpleNamespace with `type` and `id` attributes for locating the element.
        timeout: Maximum time to wait for the element to become clickable (default: 45 seconds).
    """
    try:
        if 'ShadowRoot' in element.id:
            # Handle Shadow DOM elements
            query_script = shadow_query_script(context, element.id)
            WebDriverWait(context.driver, timeout).until(
                lambda driver: driver.execute_script(query_script) is not None
            )
            logging.debug(f"Shadow DOM element '{element.id}' is clickable.")
        else:
            # Handle normal DOM elements
            WebDriverWait(context.driver, timeout).until(
                EC.element_to_be_clickable((element.type, element.id))
            )
            logging.debug(f"Element '{element.id}' is clickable.")
    except TimeoutException:
        logging.error(f"Timeout: Element '{element.id}' not found or not clickable within {timeout} seconds.")
        raise TimeoutException(f"Timeout waiting for element '{element.id}' to be clickable.")
    except Exception as e:
        logging.error(f"Error: Could not locate or click element '{element.id}'. Error: {str(e)}")
        raise e


def web_page_url(context, web_page_name):
    """
    Return the URL of a named web page (or the 'name' itself if a literal URL).

    NOTE: Useful for specifyinh URL 'nicknames'.
    """
    url_list = {
        "AI UNLIMITED":
            get_property(context, 'context.properties.stack.Tags.AiUnlimitedWorkspacesURL'),
        "AI UNLIMITED JUPYTER":
            get_property(context, 'context.properties.stack.Tags.AiUnlimitedJupyterURL'),
        "AI UNLIMITED WORKSPACES":
            get_property(context, 'context.properties.stack.Tags.AiUnlimitedWorkspacesURL'),
        "SETTINGS":
            get_property(context, 'context.properties.stack.Tags.AiUnlimitedWorkspacesURL'),
    }
    return url_list[web_page_name.upper()] if web_page_name.upper() in url_list else web_page_name


def maybe_reauthenticate_github_sudo(context):
    """
    If GitHub displays a 'sudo' prompt requiring re-auth (2FA) handle it.

    Args:
        context: Behave context object.
    """
    try:
        # 1) Look for the sudo container or the "sudo" prompt
        sudo_container_xpath = "//*[@id='sudo']"
        WebDriverWait(context.driver, 3).until(
            EC.presence_of_element_located((By.XPATH, sudo_container_xpath))
        )
        logging.info("GitHub Sudo re-auth page detected. Proceeding with TOTP re-auth.")
    except TimeoutException:
        # No sudo screen, so no re-auth needed
        logging.debug("No GitHub Sudo re-auth page found. Continuing without re-auth.")
        return

    # 2) Click the "Use authenticator code" button
    use_authenticator_button_xpath = "//*[@id='sudo']/sudo-credential-options/div[5]/div/ul/li[2]/button"
    click(context, SimpleNamespace(type=By.XPATH, id=use_authenticator_button_xpath))

    # 3) Wait for TOTP input field
    totp_input_xpath = "//*[@id='app_totp']"
    WebDriverWait(context.driver, 45).until(
        EC.presence_of_element_located((By.XPATH, totp_input_xpath))
    )

    # 4) Enter TOTP code
    totp_secret = os.getenv("GITHUB_TOTP_SECRET")
    if not totp_secret:
        raise ValueError("GITHUB_TOTP_SECRET environment variable is not set! 2FA re-auth cannot proceed.")

    totp = pyotp.TOTP(totp_secret)
    current_code = totp.now()

    set(context, SimpleNamespace(type=By.XPATH, id=totp_input_xpath), current_code)
    logging.info("Filled TOTP code for re-auth. GitHub should continue after submission.")


def delete_old_client_secrets(context):
    """
    Delete old client secrets from a GitHub OAuth App, keeping only the latest (topmost) secret.
    """
    secret_rows_xpath = "//div[@class='Box-row d-flex flex-items-center client-secret']"  # noqa> S105 - This is not a password

    # Find all secrets
    all_secret_rows = context.driver.find_elements(By.XPATH, secret_rows_xpath)

    if len(all_secret_rows) <= 1:
        logging.info("No old secrets to delete, or only one secret present.")
        return

    logging.info(f"Found {len(all_secret_rows)} secrets total. Will keep the first/newest.")

    # Keep deleting while more than 1 secret exists
    while len(context.driver.find_elements(By.XPATH, secret_rows_xpath)) > 1:
        try:
            # Re-fetch elements in each loop
            all_secret_rows = context.driver.find_elements(By.XPATH, secret_rows_xpath)
            row_to_delete = all_secret_rows[-1]  # Always delete the last one

            logging.info(f"Deleting old secret... {len(all_secret_rows)} remaining.")

            # Scroll into view
            context.driver.execute_script("arguments[0].scrollIntoView(true);", row_to_delete)
            time.sleep(1)

            # Click the red "Delete" button inside this row
            delete_button_xpath = ".//summary[contains(@class,'btn-danger')]"
            delete_button = row_to_delete.find_element(By.XPATH, delete_button_xpath)
            delete_button.click()
            time.sleep(1)  # Allow confirmation dialog to appear

            # Wait for the confirmation dialog inside this row
            dialog_xpath = ".//details-dialog"
            dialog_element = WebDriverWait(row_to_delete, 5).until(
                EC.presence_of_element_located((By.XPATH, dialog_xpath))
            )

            # Handle GitHub's "sudo" re-auth if needed
            maybe_reauthenticate_github_sudo(context)

            # Click the final "Delete" button inside the dialog
            confirm_delete_xpath = ".//button[@type='submit' and contains(@class,'btn-danger')]"
            confirm_delete_button = WebDriverWait(dialog_element, 5).until(
                EC.element_to_be_clickable((By.XPATH, confirm_delete_xpath))
            )
            confirm_delete_button.click()
            time.sleep(1)

            # Wait for the row to disappear before next iteration
            WebDriverWait(context.driver, 45).until(EC.staleness_of(row_to_delete))

            logging.info(f"Old secret deleted. Remaining: {len(context.driver.find_elements(By.XPATH, secret_rows_xpath))}")

        except Exception as e:
            logging.error(f"Failed to delete a secret: {e}")
            break  # Exit loop if an error occurs

    logging.info("Old secrets deleted, only the latest one remains.")
