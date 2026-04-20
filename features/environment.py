"""
environment.py.

Description:
This module provides the environment setup and teardown functions for the AI Unlimited tests.

Functions:
- before_all: Setup the environment before all tests.
- before_feature: Setup the environment before each feature.
- after_feature: Teardown the environment after each feature.
- after_all: Teardown the environment after all tests.
"""
import logging
import os
from datetime import datetime
from dotenv import load_dotenv, find_dotenv
from types import SimpleNamespace

from common.framework import save_test_results, set_test_result

dotenv_path = find_dotenv()
if dotenv_path:
    print(f'Loading .env file from: {dotenv_path}')
    load_dotenv(dotenv_path)


def before_all(context) -> None:
    """
    Setup the environment before all tests.

    Args:
    - context: The test context.

    Returns:
    - None
    """
    # Set up logging for all tests
    # -- SET LOG LEVEL: behave --logging-level=ERROR ...
    # on behave command-line or in "behave.ini" (default is INFO).
    context.config.setup_logging()

    # AWS secrets
    context.properties = SimpleNamespace()
    context.properties.aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID')
    context.properties.aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')
    context.properties.aws_session_token = os.getenv('AWS_SESSION_TOKEN') or None

    # Other secrets
    context.properties.github_password = os.getenv('GITHUB_PASSWORD')
    context.properties.github_username = os.getenv('GITHUB_USERNAME')
    context.properties.mfa_token = os.getenv('MFA_TOKEN')
    context.properties.rsa_key = os.getenv('RSA_KEY')

    # Other properties
    context.properties.stack_name = os.getenv('STACK_NAME') or None
    context.properties.jupyter_kernel = {}
    context.properties.jupyter_notebook = SimpleNamespace()
    context.properties.jupyter_pass = 'jupyterpass'  # noqa: S105
    context.properties.test_results = SimpleNamespace()

    # Set engine_bom_version & suite_id
    set_test_result(context, 'version', os.getenv('ICW_VERSION') or None)
    set_test_result(context, 'suite_id', datetime.now().strftime('%Y%m%d%H%M%S%f'))


def set_run_id(context):
    """
    Set run ID.
    """
    run_id = datetime.now().strftime('%Y%m%d%H%M%S%f')
    set_test_result(context, 'run_id', run_id)


def before_feature(context, feature) -> None:
    """
    Before each feature file.
    """
    return


def after_feature(context, feature) -> None:
    """
    Teardown the environment after each feature.
    """
    return


def after_all(context) -> None:
    """
    Teardown the environment after all tests.
    """
    # Writes updated reports/allure results and pushes to GitHub.
    save_test_results(context)
    logging.info(f"AFTER_ALL: Completed ICW tests with FAILED={context.failed} and ABORTED={context.aborted}")
