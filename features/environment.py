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
import json
import logging
import os
import shutil
from datetime import datetime
from dotenv import load_dotenv, find_dotenv
from selenium import webdriver
from seleniumwire import webdriver as wire_webdriver
from types import SimpleNamespace

from common.azure_operator import AzureOperator
from common.aws_operator import AWSOperator
from common.framework import get_property, save_stack_def_file, save_test_results, set_test_result, update_test_status
from urllib.parse import urlparse, urlunparse

import re

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

    # Azure secrets
    context.properties.azure_client_id = os.getenv('AZURE_CLIENT_ID')
    context.properties.azure_client_secret = os.getenv('AZURE_CLIENT_SECRET')
    context.properties.azure_tenant_id = os.getenv('AZURE_TENANT_ID')
    context.properties.azure_subscription_id = os.getenv('AZURE_SUBSCRIPTION_ID')
    context.properties.region_name = 'eastus'

    # Other secrets
    context.properties.github_password = os.getenv('GITHUB_PASSWORD')
    context.properties.github_username = os.getenv('GITHUB_USERNAME')
    context.properties.mfa_token = os.getenv('MFA_TOKEN')
    context.properties.rsa_key = os.getenv('RSA_KEY')

    # Other properties
    context.properties.browser = os.getenv('AIU_BROWSER').lower() if os.getenv('AIU_BROWSER') else "chrome"
    context.properties.jupyter_kernel = {}
    context.properties.jupyter_notebook = SimpleNamespace()
    context.properties.jupyter_pass = 'jupyterpass'  # noqa: S105
    context.properties.test_results = SimpleNamespace()

    # Load stack definition file, if one exists.
    context.properties.stack_name = os.getenv('AIU_STACK_NAME') or None
    context.properties.stack_updated = False  # Used to check if stack def file needs to be updated in AFTER_ALL.
    context.properties.cloud = 'aws' if 'aws' in context.properties.stack_name.lower() else 'azure'
    context.properties.marketplace = (
        True
        if ('mkt' in context.properties.stack_name) or ('marketplace' in context.properties.stack_name)
        else False
    )
    context.properties.connection = (
        'unlimited' if (context.properties.marketplace) else context.properties.stack_name + "_private"
    )

    stack_path = os.path.abspath(f"../resources/stacks/{context.properties.stack_name}.json")
    if (context.properties.stack_name and os.path.isfile(stack_path)):
        f = open(stack_path)
        _stack = json.load(f)
        context.properties.stack = SimpleNamespace(**_stack)
        context.properties.region_name = get_property(context, 'context.properties.stack.Parameters.AvailablityZone')
        logging.info(f"BEFORE_ALL: Loaded stack definition file ../resources/stacks/{context.properties.stack_name}.json")
    else:
        logging.warning(f"BEFORE_ALL: Could not find stack definition file {stack_path}")
        context.properties.stack = SimpleNamespace()

    # Set engine_bom_version & suite_id
    set_test_result(context, 'engine_bom_version', os.getenv('AIU_ENGINE_BOM_VERSION'))
    set_test_result(context, 'suite_id', datetime.now().strftime('%Y%m%d%H%M%S%f'))


def restore_stack_name(context):
    """
    Get Stack name from .env.
    """
    context.properties.stack_name = os.getenv('AIU_STACK_NAME') or None


def set_run_id(context):
    """
    Set run ID.
    """
    run_id = datetime.now().strftime('%Y%m%d%H%M%S%f')
    set_test_result(context, 'run_id', run_id)


def init_aws_operator(context):
    """
    Initialize AWS Operator.
    """
    logging.info("BEFORE_FEATURE: Running test on AWS...")
    ctx = context.properties
    ctx.cloud = 'aws'
    ctx.region_name = 'us-west-2'
    ctx.template_type = 'full'
    ctx.network_type = 'pub'
    ctx.releases = ''
    try:
        context.aws_operator = AWSOperator(
            aws_access_key_id=ctx.aws_access_key_id,
            aws_secret_access_key=ctx.aws_secret_access_key,
            aws_session_token=ctx.aws_session_token,
            region_name=ctx.region_name
        )
        logging.info("AWS Operator initialized successfully.")
    except Exception as e:
        logging.error(f"Error initializing AWS Operator: {e}")
        raise


def init_azure_operator(context):
    """
    Initialize Azure Operator.
    """
    logging.info("BEFORE_FEATURE: Running test on Azure...")
    ctx = context.properties
    ctx.cloud = 'azure'
    ctx.region_name = 'eastus'
    try:
        context.azure_operator = AzureOperator(
            subscription_id=ctx.azure_subscription_id,
            tenant_id=ctx.azure_tenant_id,
            client_id=ctx.azure_client_id,
            client_secret=ctx.azure_client_secret,
            region_name=ctx.region_name
        )
        logging.info("Azure Operator initialized successfully.")
    except Exception as e:
        logging.error(f"Error initializing Azure Operator: {e}")
        raise


def init_cloud_operator(context, provider):
    """
    Choose Cloud Operator.
    """
    if provider == 'aws':
        init_aws_operator(context)
    elif provider == 'azure':
        init_azure_operator(context)


def build_webdriver_options(context):
    """
    Build Webdriver Options.
    """
    browser = context.properties.browser
    opts = {
        'firefox': webdriver.FirefoxOptions
        # 'safari': webdriver.SafariOptions
    }.get(browser, webdriver.ChromeOptions)()
    for arg in ("--allow-running-insecure-content", "--enable-automation",
                "--ignore-certificate-errors", "--no-sandbox"):
        opts.add_argument(arg)
    return opts


def prepare_user_data_dir(options):
    """
    Prepare User data dir.
    """
    path = "C:/Temp/chrome-data"
    if os.path.exists(path):
        shutil.rmtree(path)
    os.makedirs(path, exist_ok=True)
    options.add_argument(f"--user-data-dir={path}")


def maybe_headless_for_actions(options):
    """
    Headless for GHA.
    """
    if os.getenv('GITHUB_ACTIONS'):
        for arg in ("--disable-browser-side-navigation",
                    "--disable-dev-shm-usage", "--disable-extensions",
                    "--disable-gpu", "--dns-prefetch-disable", "--headless"):
            options.add_argument(arg)


def launch_driver(browser, options):
    """
    Launch Browser drivers.
    """
    if browser == 'firefox':
        driver = wire_webdriver.Firefox(options=options)
        version = 'geckodriver ' + driver.capabilities['browserVersion'].split(' ')[0]
    elif browser == 'safari':
        driver = wire_webdriver.Safari(options=options)
        version = 'safaridriver ' + driver.capabilities['browserVersion'].split(' ')[0]
    else:
        driver = wire_webdriver.Chrome(options=options)
        version = 'chromedriver ' + driver.capabilities['chrome']['chromedriverVersion'].split(' ')[0]
    return driver, version


def get_elb_host(context):
    """
    Get Host.
    """
    raw = get_property(context, 'context.properties.stack.Tags.AiUnlimitedWorkspacesURL')
    return re.sub(r'^https?://', '', raw).rstrip('/')


def rewrite_and_log(request, elb, logpath, context):
    """
    Inject request and logging.
    """
    parsed = urlparse(request.url)

    # Rewrite internal app hosts on ports 3000/3282
    if parsed.port in (3000, 3282):
        new_netloc = f"{elb}:{parsed.port}"
        request.url = urlunparse(parsed._replace(netloc=new_netloc))
        request.headers['Host'] = new_netloc
        for hdr in ('Origin', 'Access-Control-Request-Headers', 'Access-Control-Request-Method'):
            try:
                request.headers.pop(hdr, None)
            except Exception:
                logging.debug(f"Could not pop header {hdr}")


    # Flexible redirect_uri in OAuth URLs (percent-encoded)
    if 'redirect_uri=' in request.url:
        # replace any host in the redirect_uri param with our ELB
        request.url = re.sub(
            r'(redirect_uri=https?%3A%2F%2F)[^%]+',
            rf'\1{elb}',
            request.url
        )

    # JSON body rewrite for dynamic publicHostname and callbackApplicationUrl
    ctype = request.headers.get('Content-Type', '')
    if ctype.startswith('application/json') and request.body:
        try:
            data = json.loads(request.body.decode('utf-8'))
            changed = False
            if 'publicHostname' in data:
                data['publicHostname'] = elb
                changed = True
            if 'callbackApplicationUrl' in data:
                cb = urlparse(data['callbackApplicationUrl'])
                data['callbackApplicationUrl'] = cb._replace(netloc=f"{elb}:{cb.port}").geturl()
                changed = True
            if changed:
                request.body = json.dumps(data).encode('utf-8')
        except Exception:
            logging.info("Rewriting function failed")

    # Log everything
    with open(logpath, 'a') as f:
        f.write(json.dumps({
            'method': request.method,
            'url': request.url,
            'headers': dict(request.headers),
            'body': (request.body.decode('utf-8', 'ignore') if request.body else None)
        }) + "\n")

def make_request_rewriter(elb, logpath, context):
    """
    Rewrite and log function.
    """
    return lambda request: rewrite_and_log(request, elb, logpath, context)


def make_response_logger(logpath):
    """
    Log requests.
    """
    def logger(request, response):
        try:
            entry = {
                'url': request.url,
                'method': request.method,
                'request_headers': dict(request.headers),
                'request_body': request.body.decode('utf-8', 'ignore') if request.body else None,
                'status_code': response.status_code,
                'response_headers': dict(response.headers),
                'response_body': response.body.decode('utf-8', 'ignore') if response.body else None
            }
            with open(logpath, 'a') as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            logging.error(f"Failed to log response: {e}")
    return logger


def attach_request_logging(driver, elb, logpath, context):
    """
    Attach interceptors.
    """
    driver.request_interceptor = make_request_rewriter(elb, logpath, context)
    driver.response_interceptor = make_response_logger(logpath)


def _setup_ui_driver(context):
    options = build_webdriver_options(context)
    prepare_user_data_dir(options)
    maybe_headless_for_actions(options)
    driver, version = launch_driver(context.properties.browser, options)
    context.driver = driver
    driver.set_window_size(1200, 1400)
    driver.set_page_load_timeout(120)
    driver.implicitly_wait(45)

    logging.getLogger('seleniumwire').setLevel(logging.ERROR)  # Run selenium wire at ERROR level

    elb = get_elb_host(context)
    logpath = 'wire-requests.log'
    attach_request_logging(driver, elb, logpath, context)
    mode = "headless via GitHub Actions" if os.getenv('GITHUB_ACTIONS') else "on localhost"
    logging.info(f"BEFORE_FEATURE: Running UI test {mode} using {version}...")


def before_feature(context, feature) -> None:
    """
    Before each feature file.
    """
    restore_stack_name(context)
    set_run_id(context)
    if 'setup' in feature.tags or 'teardown' in feature.tags:
        init_cloud_operator(context, context.properties.cloud)
    if 'ui' in feature.tags:
        _setup_ui_driver(context)


def after_feature(context, feature) -> None:
    """
    Teardown the environment after each feature.

    Args:
    - context: The test context.
    - driver: The Selenium WebDriver.

    Returns:
    - None
    """
    if 'ui' in feature.tags:
        context.driver.quit()

    # Write updated stack definition file, if it has changed.
    if context.properties.stack_updated:
        save_stack_def_file(context)

    # Save test results to Vantage Lake Release & Test Status dashboard.
    update_test_status(context)


def after_all(context) -> None:
    """
    Teardown the environment after all tests.

    Args:
    - context: The test context.

    Returns:
    - None
    """
    # Writes updated reports/allure results and pushes to GitHub.
    save_test_results(context)
    logging.info(f"AFTER_ALL: Completed AI Unlimited tests with FAILED={context.failed} and ABORTED={context.aborted}")
