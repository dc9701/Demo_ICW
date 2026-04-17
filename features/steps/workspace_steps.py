"""
workspace_steps.py.

Description: This module contains the step definitions for the workspace.feature file.
"""
from behave import given, then, when
from common import selenium_functions as web
import logging
import time

from common.framework import failed, get_property, set_test_result
from pages import locators as Page

# 'GIVEN ...' STEPS:


@given("I am signed in to AI Unlimited on stack {stack}")
def step_given_signed_in_ai_unlimited_stack(context, stack):
    """
    Signs in to AI Unlimited web app for the specified stack.

    Args:
        context: Behave context object.
        stack: context.properties.stack_name, from os.getenv('AIU_STACK_NAME').
    """
    stack = eval(stack) if 'context.' in stack else stack
    url = get_property(context, 'context.properties.stack.Tags.AiUnlimitedWorkspacesURL')
    if (url):
        web.open_url(context, url + '/landing')
        time.sleep(15)
        if (web.found_element(context, Page.Aiu.nav.settings())):
            web.authenticate_with_github(context, Page.Aiu.nav.settings())
        else:
            web.authenticate_with_github(context, Page.Aiu.signin.with_github())
    else:
        failed(f"Could not log in to AI Unlimited on stack: {stack}")


# 'WHEN ...' STEPS:


@when("I authenticate with GitHub")
def step_when_authenticate_github(context):
    """
    Authenticate with GitHub either during sign-in or workspace setup.

    Args:
        context: Behave context object.
    """
    if (web.found_element(context, Page.Aiu.settings.github.auth_success())):
        logging.info("Already authenticated...")
    else:
        web.authenticate_with_github(context, Page.Aiu.settings.github.authenticate())
        logging.info("Authenticated with GitHub")


@when("I click {element}")
def step_when_click_next(context, element):
    """
    Click specified element.

    Args:
        context: Behave context object.
        element: Element to click.
    """
    element = eval(element) if element and ('context.' in element or 'Page.' in element) else element
    web.click(context, element)
    logging.debug(f"Clicked {element}...")


@when("I open the {web_page} page")
def step_when_open_page(context, web_page):
    """
    Open the specified web page.

    Args:
        context: Behave context object.
        web_page: Web page name (string literal) or 'context.*' variable containing notebook name.
    """
    web_page = eval(web_page) if 'context.' in web_page else web_page
    context.properties.web_page_name = web_page
    context.properties.web_page_url = web.web_page_url(context, web_page)

    # Navigate as needed to specified web page once URL is opened successfully.
    if (web_page.upper() == 'SETTINGS'):
        web.click(context, Page.Aiu.nav.settings())
    else:
        web.open_url(context, context.properties.web_page_url)

    title = context.driver.title
    if title:
        logging.info(f"Successfully opened the '{web_page}' web page ({title}) at: {context.properties.web_page_url}")
        time.sleep(3)
    else:
        failed(f"Could not open the '{web_page}' web page at: {context.properties.web_page_url}")


@when("I save the following element values")
def step_when_save_element_values(context):
    """
    Save one or more elements are visible using a data table.

    Args:
        context: Behave context object.
        NOTE: The elements table is accessible via context.table
    """
    if context.table:
        for row in context.table:
            field_name = row['variable']
            field_value = web.get(context, eval(row['field']))
            set_test_result(context, field_name, field_value)


@when("I select the appropriate cloud service")
def step_when_select_cloud(context):
    """
    Click AWS or Azure cloud service, based upon stack name.

    Args:
        context: Behave context object.
    """
    element = Page.Aiu.settings.cloud.aws() if context.properties.cloud == 'aws' else Page.Aiu.settings.cloud.azure()
    time.sleep(1)
    web.click(context, element)
    time.sleep(1)


@when("I set the following element values")
def step_when_set_element_values(context):
    """
    Verify the set of elements are visible using a data table.

    Args:
        context: Behave context object.
        NOTE: The elements table is accessible via context.table
    """
    logging.info(f"Setting the following element values: {context.table}...")
    web.set_elements(context, context.table)


@when("I wait {secs} seconds")
def step_when_wait(context, secs):
    """
    Wait the specified number of secods.

    Args:
        context: Behave context object.
        secs: Seconds to wait.
    """
    logging.info(f"Waiting {secs} seconds...")
    time.sleep(int(secs))


# 'THEN ...' STEPS:


@then("I verify the following elements exist")
def step_then_verify_elements_exist(context):
    """
    Verify the set of elements exist in the DOM using a data table.

    Args:
        context: Behave context object.
        NOTE: The elements table is accessible via context.table.  If the table's Value column is blank,
              only element existence will be verified; otherwise, it will verify the element's value matches.
    """
    logging.info(f"Verifying the following elements exist: {context.table}...")
    web.verify_elements(context, context.table)


@then("I verify the following element values match")
def step_then_verify_element_values_match(context):
    """
    Verify the set of elements are visible using a data table.

    Args:
        context: Behave context object.
        NOTE: The elements table is accessible via context.table
    """
    logging.info(f"Verifying the following element values match: {context.table}...")
    web.verify_elements(context, context.table)
