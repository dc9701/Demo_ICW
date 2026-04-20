"""
framework.py.

Description:
    This module provides the common functions and classes required for the test scripts.

Classes:
    - None

Functions (alphabetical):
    - save_test_results: Writes updated reports/allure results and pushes to GitHub.
    - set_test_result: Set Allure test report result value (displayed as a link name).
"""
import allure
import os


def save_test_results(context):
    """
    Writes updated reports/allure results and pushes to GitHub.

    Args:
        context: Behave context object.

    # Replace tags with actual values in all results JSON files.
    """
    # Slightly different syntax and no need for 'allure generate' when running via GitHub actions.
    if (os.getenv('GITHUB_ACTIONS')):
        os.system(f"""
        sed -i "s/{{context.properties.test_results.version}}/{context.properties.test_results.version}/g" reports/allure/*.json
        sed -i "s/{{context.properties.stack_name}}/{context.properties.stack_name}/g" reports/allure/*.json >/dev/null 2>&1
        """)
    else:
        os.system(f"""
        sed -i ".bak" "s/{{context.properties.test_results.version}}/{context.properties.test_results.version}/g" reports/allure/*.json
        sed -i ".bak" "s/{{context.properties.stack_name}}/{context.properties.stack_name}/g" reports/allure/*.json >/dev/null 2>&1
        rm reports/allure/*.json*.bak
        """)


def set_test_result(context, property, value):
    """
    Set Allure test report result value (displayed as a link name).

    Args:
        context: Behave context object.
        property (str): Property name, such as 'ENGINE_VERSION'.
        value (str): Property value, such as '20.00.18.29'.

    NOTE: Results may be referenced after being saved; e.g.:  context.properties.test_results.ENGINE_VERSION
    """
    context.properties.test_results.__dict__[property] = value
    allure.dynamic.link(f"https://github.com/dc9701/ICW?{property}={value}", name=f"{property} = {value}")
