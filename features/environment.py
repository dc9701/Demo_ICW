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

# GX-related imports.
import great_expectations as gx

# Our framework-related imports.
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

    # Define Snowflake connection.
    context.properties.sf_acct_name = os.getenv("MY_DB_ACCOUNT")
    context.properties.sf_user_name = os.getenv("MY_DB_USERNAME")
    context.properties.sf_password = os.getenv("MY_DB_PASSWORD")
    context.properties.sf_database = "OR_WORKERS_COMP"
    context.properties.sf_schema = "PUBLIC"
    context.properties.sf_warehouse = "COMPUTE_WH"
    context.properties.sf_role = "ACCOUNTADMIN"

    # Create GX context & Snowflake datasource/connection placeholders.  
    # Actual connections are made in common_steps.py.
    context.properties.gx_context = gx.get_context(mode="file", project_root_dir="./resources")
    context.properties.gx_datasource =  None
    context.properties.sf_conn_params = {
        "user":      context.properties.sf_user_name,
        "password":  context.properties.sf_password,
        "account":   context.properties.sf_acct_name,
        "warehouse": context.properties.sf_warehouse,
        "database":  context.properties.sf_database,
        "schema":    context.properties.sf_schema
    }
    context.properties.sf_conn = None
    
    # Other properties
    context.properties.stack_name = 'localhost'
    context.properties.test_results = SimpleNamespace()

    # Set version & suite_id
    set_test_result(context, 'version', 'latest')
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
    Teardown the environment after all tests (close DB connections, save results).
    """
    context.properties.sf_conn.close()

    # Writes updated reports/allure results and pushes to GitHub.
    save_test_results(context)
    logging.info(f"AFTER_ALL: Completed ICW tests with FAILED={context.failed} and ABORTED={context.aborted}")
