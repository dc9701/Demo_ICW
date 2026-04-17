"""
github_oauth_steps.py.

Description: This module contains the Github OAuthApp step definitions.
"""
import os
import json
import logging
from behave import given, when
from types import SimpleNamespace

from common.framework import update_stack_tags

from common.github_oauth_requests import (
    init_session,
    fetch_login_tokens,
    do_u2f_fragment,
    do_primary_login,
    fetch_two_factor_token,
    submit_two_factor,
    fetch_oauth_form,
    create_oauth_app,
    get_oauth_app_id,
    parse_client_id_and_secret,
    delete_all_oauth_apps_with_name
)

GITHUB_USERNAME = os.getenv("GITHUB_USERNAME")
GITHUB_PASSWORD = os.getenv("GITHUB_PASSWORD")
GITHUB_TOTP_SECRET = os.getenv("GITHUB_TOTP_SECRET")


@given("I am signed in to GitHub using my email and password")
def step_login_github_email_password(context):
    """
    1. Initialize a requests.Session().

    2. GET /login to grab authenticity_token, timestamp, timestamp_secret
    3. GET /u2f/login_fragment (populates cookies)
    4. POST /session (username+password)
    5. GET /sessions/two-factor/app, parse out authenticity_token
    6. POST /sessions/two-factor (TOTP) → now _gh_sess cookie is valid
    """
    if not all([GITHUB_USERNAME, GITHUB_PASSWORD, GITHUB_TOTP_SECRET]):
        raise RuntimeError("GITHUB_USERNAME, GITHUB_PASSWORD, and GITHUB_TOTP_SECRET must be set in env")

    # Keep a session for all subsequent steps:
    session = init_session()
    context.oauth_session = session

    # GET /login
    tokens = fetch_login_tokens(session)

    # U2F “fragment” step
    do_u2f_fragment(session)

    # Primary login POST /session
    do_primary_login(session, GITHUB_USERNAME, GITHUB_PASSWORD, tokens)

    # GET /sessions/two-factor/app → parse 2FA token
    tf_token = fetch_two_factor_token(session)

    # POST TOTP
    submit_two_factor(session, tf_token, GITHUB_TOTP_SECRET)

    logging.info("GitHub login (incl. 2FA) succeeded.")


@given("I have a valid stack definition JSON file named context.properties.stack_name")
def step_load_stack_definition_from_context(context):
    """
    Load the stack definition JSON file using the stack_name from context.properties.
    """
    if not hasattr(context.properties, "stack_name") or not context.properties.stack_name:
        raise ValueError("context.properties.stack_name is not set!")

    stack_name = context.properties.stack_name
    stack_path = os.path.abspath(f"../resources/stacks/{stack_name}.json")
    logging.debug(f"Looking for stack JSON at: {stack_path}")

    if not os.path.exists(stack_path):
        raise FileNotFoundError(f"Stack definition file not found: {stack_path}")

    with open(stack_path, "r") as f:
        context.properties.stack = SimpleNamespace(**json.load(f))
        logging.info(f"Loaded stack definition: {stack_path}")


@when("I fill the GitHub OAuth form with")
def step_fill_github_oauth_form(context):
    """
    1) Build homepage_url + callback_url (as before).

    2) Delete all existing OAuth Apps whose name == context.properties.stack_name.
    3) Fetch form token and POST to create a single new OAuth App.
    """
    # Construct the two URLs
    tags = context.properties.stack.Tags
    if not isinstance(tags, list):
        raise ValueError("Expected Tags to be a list")
    base_url = None
    for tag in tags:
        if tag.get("TagKey") == "AiUnlimitedWorkspacesURL":
            base_url = tag.get("TagValue")
            break
    if not base_url:
        raise KeyError("AiUnlimitedWorkspacesURL tag not found in stack Tags.")

    homepage_url = f"{base_url}:3000"
    callback_url = f"{base_url}:3000/auth/github/callback"
    app_name = context.properties.stack_name

    # DELETE any existing apps with the same name
    session = context.oauth_session
    delete_all_oauth_apps_with_name(session, app_name)

    # CREATE a fresh OAuth App
    auth_token = fetch_oauth_form(session)
    create_oauth_app(
        session,
        auth_token=auth_token,
        name=app_name,
        url=homepage_url,
        description="",
        callback_url=callback_url,
        device_flow=False
    )
    logging.info(f"Created OAuth App named '{app_name}'")


@when("I retrieve the generated OAuth credentials")
def step_retrieve_github_oauth_credentials(context):
    """
    1. Use get_oauth_app_id() to find the numeric app_id for context.properties.stack_name.

    2. Call parse_client_id_and_secret(session, app_id) to scrape ClientID + ClientSecret.
    3. Store them on context.properties.github_credentials.
    """
    session = context.oauth_session
    app_name = context.properties.stack_name

    # Grab the new app's numeric ID
    oauth_app_id = get_oauth_app_id(session, app_name)
    logging.debug(f"Found OAuth app_id = {oauth_app_id} for name '{app_name}'")

    # Scrape out the client ID + client secret from the "Advanced" page
    creds = parse_client_id_and_secret(session, oauth_app_id)
    if not creds.get("ClientID") or not creds.get("ClientSecret"):
        raise RuntimeError("Failed to parse ClientID/ClientSecret via requests")
    logging.info(f"Retrieved OAuth credentials for '{app_name}': {creds}")

    # Save onto context
    context.properties.github_credentials = creds


@when("I update the deployment JSON file with the credentials")
def step_update_deployment_json(context):
    """
    Read context.properties.github_credentials and call update_stack_tags().
    """
    if not hasattr(context.properties, "github_credentials") or not context.properties.github_credentials:
        raise AssertionError("GitHub credentials not found on context")

    creds = context.properties.github_credentials
    tags = [
        {"TagKey": "GitHubClientID",    "TagValue": creds["ClientID"]},
        {"TagKey": "GitHubClientSecret", "TagValue": creds["ClientSecret"]}
    ]
    update_stack_tags(context, tags)
    logging.info("Deployment JSON updated with new GitHub OAuth ClientID + ClientSecret")
