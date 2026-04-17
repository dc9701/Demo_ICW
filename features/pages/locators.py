"""
locators.py.

Description:
This module provides the locators for the Jupyter and Workspaces pages.

Classes:
- Jupyter: A class for Jupyter page locators.
- Workspaces: A class for Workspaces (New UI) page locators.

Functions:
- try_it: Return the locator for the "Try it in your browser" button.

Attributes:
- jupyterlab: A namespace for Jupyter.jupyterlab section locators.
- subprojects: A method to return the locator for a subproject.
- top_nav: A namespace for Jupyter.top_nav section locators.
- basic_setup: A namespace for Workspaces.basic_setup section locators.
- cloud_integration: A namespace for Workspaces.cloud_integration section locators.
- git_integration: A namespace for Workspaces.git_integration section locators.
"""

from selenium.webdriver.common.by import By
from types import SimpleNamespace


class Jupyter(object):
    """A class for Jupyter application locators."""

    # Locators for AI Unlimited Jupyter.launcher section - Landing page for AI Unlimited Jupyter instance

    def ai_unlimited_notebook():
        """AI Unlimited notebook icon."""
        return SimpleNamespace(type=By.CSS_SELECTOR, id="[data-category='Notebook'][title='AI Unlimited']")

    _launcher = {
        "ai_unlimited_notebook": ai_unlimited_notebook
    }
    launcher = SimpleNamespace(**_launcher)

    # Locators for AI Unlimited Jupyter.home page - Main page of AI Unlimited Jupyter instance

    def dismiss():
        """Dismiss button on Jupyter home page when an error appears upon loading."""
        return SimpleNamespace(type=By.XPATH, id="button.jp-Dialog-button")

    _home = {
        "dismiss": dismiss
    }
    home = SimpleNamespace(**_home)

    # Locators for Jupyter.jupyterlab section - JupyterLab: A Next-Generation Notebook Interface

    def try_it() -> SimpleNamespace:
        """
        Return the locator for the 'Try it in your browser' button.

        Returns:
        - A SimpleNamespace object with the locator type and id.
        """
        return SimpleNamespace(type=By.XPATH,
                               id="//section[@class='homepage-section section-grey']//a[.='Try it in your browser']")

    _jupyterlab = {
        "try_it": try_it
    }
    jupyterlab = SimpleNamespace(**_jupyterlab)

    # Locators for Jupyter.subprojects - List of Subprojects at bottom of page (single method; no dict req'd)
    def subprojects(project_name: str) -> SimpleNamespace:
        """
        Return the locator for a subproject.

        Args:
        - project_name: The name of the subproject.

        Returns:
        - A SimpleNamespace object with the locator type and id.
        """
        return SimpleNamespace(type=By.XPATH, id=f"//a[contains(.,'{project_name}')]")

    # Locators for Jupyter.top_nav - Top navigation bar
    def about() -> SimpleNamespace:
        """
        Return the locator for the 'About' link in the top navigation bar.

        Returns:
        - A SimpleNamespace object with the locator type and id.
        """
        return SimpleNamespace(type=By.CSS_SELECTOR, id=".navbar-links [href='/about']")

    def documentation() -> SimpleNamespace:
        """
        Return the locator for the 'Documentation' link in the top navigation bar.

        Returns:
        - A SimpleNamespace object with the locator type and id.
        """
        return SimpleNamespace(type=By.XPATH, id="//ul[@class='navbar-links']//a[contains(.,'Documentation')]")

    def get_involved() -> SimpleNamespace:
        """
        Return the locator for the 'Get Involved' link in the top navigation bar.

        Returns:
        - A SimpleNamespace object with the locator type and id.
        """
        return SimpleNamespace(type=By.CSS_SELECTOR, id=".navbar-links [href='/community']")

    def install() -> SimpleNamespace:
        """
        Return the locator for the 'Install' link in the top navigation bar.

        Returns:
        - A SimpleNamespace object with the locator type and id.
        """
        return SimpleNamespace(type=By.CSS_SELECTOR, id=".navbar-links [href='/about']")

    _top_nav = {
        "about": about,
        "documentation": documentation,
        "get_involved": get_involved,
        "install": install
    }
    top_nav = SimpleNamespace(**_top_nav)


class Aiu(object):
    """A class for AI Unlimited (workspaces) page locators."""

    # Locators for Aiu.nav - Left navigation bar

    def nav_account():
        """Left navigation bar > Account."""
        return SimpleNamespace(type=By.XPATH, id="//cv-icon[contains(.,'person')]")

    def nav_ai_unlimited():
        """Left navigation bar > Account."""
        return SimpleNamespace(type=By.XPATH, id="//cv-icon[contains(.,'teradata')]")

    def nav_help():
        """Left navigation bar > Help."""
        return SimpleNamespace(type=By.XPATH, id="//cv-icon[contains(.,'help')]")

    def nav_logs():
        """Left navigation bar > Help."""
        return SimpleNamespace(type=By.XPATH, id="//cv-icon[contains(.,'list_alt')]")

    def nav_projects():
        """Left navigation bar > Help."""
        return SimpleNamespace(type=By.XPATH, id="//cv-icon[contains(.,'deployed_code')]")

    def nav_settings():
        """Left navigation bar > Settings."""
        return SimpleNamespace(type=By.XPATH, id="//cv-icon[contains(.,'settings')]")

    _nav = {
        "account": nav_account,
        "ai_unlimited": nav_ai_unlimited,
        "help": nav_help,
        "logs": nav_logs,
        "projects": nav_projects,
        "settings": nav_settings
    }
    nav = SimpleNamespace(**_nav)

    # Locators for Aiu.account section

    def account_sign_out():
        """Account section > 'SIGN OUT' button."""
        return SimpleNamespace(type=By.CSS_SELECTOR, id="section.header cv-button")

    _account = {
        "sign_out": account_sign_out
    }
    account = SimpleNamespace(**_account)

    # Locators for Aiu.quick_links section

    def quick_links_create_run_your_first_project():
        """Quick Links section > 'Create and run your first Project' link."""
        return SimpleNamespace(type=By.CSS_SELECTOR, id="cv-icon.icon-right:nth-of-type(1) a")

    def quick_links_explore_sample_usecases():
        """Quick Links section > 'Explore sample usecases' link."""
        return SimpleNamespace(type=By.CSS_SELECTOR, id="cv-icon.icon-right:nth-of-type(2) a")

    _quick_links = {
        "create_run_your_first_project": quick_links_create_run_your_first_project,
        "explore_sample_usecases": quick_links_explore_sample_usecases
    }
    quick_links = SimpleNamespace(**_quick_links)

    # Locators for Aiu.settings.application page

    def settings_app_log_level():
        """Get Settings page > Application > Log Level."""
        return SimpleNamespace(type=By.CSS_SELECTOR, id="cv-select[name='serviceLogLevel']")

    def settings_app_log_level_item(item: str):
        """Get Settings page > Application > Log Level > Select Drop-Down Item."""
        return SimpleNamespace(type=By.XPATH, id=f"//cv-list-item[normalize-space()='{item}']")

    def settings_app_tls():
        """Get Settings page > Application > TLS."""
        return SimpleNamespace(type=By.CSS_SELECTOR, id="cv-switch[name='useTls']")

    _settings_app = {
        "log_level": settings_app_log_level,
        "log_level_item": settings_app_log_level_item,
        "tls": settings_app_tls
    }
    settings_app = SimpleNamespace(**_settings_app)

    # Locators for Aiu.settings.aws page

    def settings_aws_region():
        """Get Settings page > Cloud Service Provider = AWS > Region."""
        return SimpleNamespace(type=By.CSS_SELECTOR, id="cv-select[name='region'] ShadowRoot input[name='region']")

    def settings_aws_subnet():
        """Get Settings page > Cloud Service Provider = AWS > Subnet."""
        return SimpleNamespace(type=By.CSS_SELECTOR, id="cv-textfield[name='subnetId'] ShadowRoot input[name='subnetId']")

    def settings_aws_iam_role():
        """Get Settings page > Cloud Service Provider = AWS > IAM Role."""
        return SimpleNamespace(type=By.CSS_SELECTOR, id="cv-textfield[name='iamRole'] ShadowRoot input[name='iamRole']")

    def settings_aws_resource_tags():
        """Get Settings page > Cloud Service Provider = AWS > Resource Tags."""
        return SimpleNamespace(type=By.CSS_SELECTOR, id="cv-textfield[name='tags'] ShadowRoot input[name='tags']")

    def settings_aws_cidrs():
        """Get Settings page > Cloud Service Provider = AWS > Inbound Security > CIDRs."""
        return SimpleNamespace(type=By.CSS_SELECTOR, id="cv-textfield[name='accessCidrs'] ShadowRoot input[name='accessCidrs']")

    def settings_aws_prefix_list_names():
        """Get Settings page > Cloud Service Provider = AWS > Inbound Security > Prefix List Names."""
        return SimpleNamespace(type=By.CSS_SELECTOR, id="cv-textfield[name='accessPrefixLists'] ShadowRoot input[name='accessPrefixLists']")

    def settings_aws_security_group_names():
        """Get Settings page > Cloud Service Provider = AWS > Inbound Security > Security Group Names."""
        return SimpleNamespace(type=By.CSS_SELECTOR, id="cv-textfield[name='accessSecGroups'] ShadowRoot input[name='accessSecGroups']")

    def settings_aws_permissions_boundary_arns():
        """Get Settings page > Cloud Service Provider = AWS > Inbound Security > Permissions Boundary ARNs."""
        return SimpleNamespace(type=By.CSS_SELECTOR, id="cv-textfield[name='permissionsBoundary'] ShadowRoot input[name='permissionsBoundary']")

    def settings_aws_network_type():
        """Get Settings page > Cloud Service Provider = AWS > Network Type."""
        return SimpleNamespace(type=By.CSS_SELECTOR, id="cv-select[name='engineNetworkType']")

    _settings_aws = {
        "region": settings_aws_region,
        "subnet": settings_aws_subnet,
        "iam_role": settings_aws_iam_role,
        "resource_tags": settings_aws_resource_tags,
        "cidrs": settings_aws_cidrs,
        "prefix_list_names": settings_aws_prefix_list_names,
        "security_group_names": settings_aws_security_group_names,
        "permissions_boundary_arns": settings_aws_permissions_boundary_arns,
        "network_type": settings_aws_network_type
    }
    settings_aws = SimpleNamespace(**_settings_aws)

    # Locators for Aiu.settings.cloud page

    def settings_cloud_aws():
        """Get Settings page > Cloud Service Provider = AWS."""
        return SimpleNamespace(type=By.XPATH, id="//cv-radio-icon[1]")

    def settings_cloud_azure():
        """Get Settings page > Cloud Service Provider = Azure."""
        return SimpleNamespace(type=By.XPATH, id="//cv-radio-icon[2]")

    _settings_cloud = {
        "aws": settings_cloud_aws,
        "azure": settings_cloud_azure
    }
    settings_cloud = SimpleNamespace(**_settings_cloud)

    # Locators for Aiu.settings.github page

    def settings_github_github_url():
        """Get Settings page > Git Provider = GitHub > GitHub URL."""
        return SimpleNamespace(type=By.CSS_SELECTOR, id="cv-textfield[name='baseUrl'] ShadowRoot input[name='baseUrl']")

    def settings_github_homepage_url():
        """Get Settings page > Git Provider = GitHub > Homepage URL."""
        return SimpleNamespace(type=By.XPATH, id="(//div[contains(@class, 'urlInfo')])[1]")

    def settings_github_callback_url():
        """Get Settings page > Git Provider = GitHub > Authorization Callback URL."""
        return SimpleNamespace(type=By.XPATH, id="(//div[contains(@class, 'urlInfo')])[2]")

    def settings_github_client_id():
        """Get Settings page > Git Provider = GitHub > GitHub Client ID."""
        return SimpleNamespace(type=By.CSS_SELECTOR, id="cv-textfield[name='clientId'] ShadowRoot input[name='clientId']")

    def settings_github_client_secret():
        """Get Settings page > Git Provider = GitHub > GitHub Client Secret."""
        return SimpleNamespace(type=By.CSS_SELECTOR, id="cv-textfield[name='clientSecret'] ShadowRoot input[name='clientSecret']")

    def settings_github_authenticate():
        """Get Settings page > Git Provider = GitHub > AUTHENTICATE button."""
        return SimpleNamespace(type=By.CSS_SELECTOR, id="div.auth-section cv-button.auth-button")

    def settings_github_auth_success():
        """Get Settings page > Git Provider = GitHub > 'Authenticated Successfully' message."""
        return SimpleNamespace(type=By.CSS_SELECTOR, id="div.authenticated-message")

    def settings_github_authorizing_organization():
        """Get Settings page > Git Provider = GitHub > Organization Access > Authorizing Organization."""
        return SimpleNamespace(type=By.CSS_SELECTOR, id="cv-textfield[name='authOrganization'] ShadowRoot input[name='authOrganization']")

    def settings_github_repository_organization():
        """Get Settings page > Git Provider = GitHub > Organization Access > Repository Organization."""
        return SimpleNamespace(type=By.CSS_SELECTOR, id="cv-textfield[name='repoOrganization'] ShadowRoot input[name='repoOrganization']")

    _settings_github = {
        "github_url": settings_github_github_url,
        "homepage_url": settings_github_homepage_url,
        "callback_url": settings_github_callback_url,
        "client_id": settings_github_client_id,
        "client_secret": settings_github_client_secret,
        "authenticate": settings_github_authenticate,
        "auth_success": settings_github_auth_success,
        "authorizing_organization": settings_github_authorizing_organization,
        "repository_organization": settings_github_repository_organization
    }
    settings_github = SimpleNamespace(**_settings_github)

    # Locators for Aiu.settings pages

    def settings_next():
        """Get Settings page > NEXT button."""
        return SimpleNamespace(type=By.CSS_SELECTOR, id="cv-button.next-button")

    def settings_previous():
        """Get Settings page > PREVIOUS button."""
        return SimpleNamespace(type=By.CSS_SELECTOR, id="cv-button.prev-button")

    _settings = {
        "application": settings_app,
        "aws": settings_aws,
        "cloud": settings_cloud,
        "github": settings_github,
        "next": settings_next,
        "previous": settings_previous
    }
    settings = SimpleNamespace(**_settings)

    # Locators for Aiu.signin - Sign In page

    def signin_oauth_authorize():
        """Sign In page > OAuth Authorize <user> button."""
        return SimpleNamespace(type=By.CSS_SELECTOR, id="button[data-octo-click='oauth_application_authorization']")

    def signin_sso_continue():
        """Sign In page > SSO Continue button."""
        return SimpleNamespace(type=By.CSS_SELECTOR, id="button.Button--primary")

    def signin_teradata_email():
        """Sign In page > SSO > Teradata user email text field."""
        return SimpleNamespace(type=By.CSS_SELECTOR, id="input[type='email']")

    def signin_teradata_next():
        """Sign In page > SSO > Teradata 'Next' button'."""
        return SimpleNamespace(type=By.CSS_SELECTOR, id="input[type='submit']")

    def signin_teradata_password():
        """Sign In page > SSO > Teradata user password text field'."""
        return SimpleNamespace(type=By.CSS_SELECTOR, id="input[type='password']")

    def signin_teradata_signin():
        """Sign In page > SSO > Teradata 'Sign In' button'."""
        return SimpleNamespace(type=By.CSS_SELECTOR, id="input[type='submit']")

    def signin_teradata_stay_signedin_yes():
        """Sign In page > SSO > Teradata 'Stay Signed In?' > Yes button'."""
        return SimpleNamespace(type=By.CSS_SELECTOR, id="input[type='submit']")

    def signin_username():
        """Sign In page > Username text field."""
        return SimpleNamespace(type=By.CSS_SELECTOR, id="input#login_field")

    def signin_password():
        """Sign In page > Password text field."""
        return SimpleNamespace(type=By.CSS_SELECTOR, id="input#password")

    def signin_use_authenticator():
        """Sign In page > Use Authenticator App link in Confirm Access popup."""
        return SimpleNamespace(type=By.CSS_SELECTOR, id="a[data-test-selector='totp-app-link']")

    def signin_auth_code():
        """Sign In page > Use Passkey button in popup."""
        return SimpleNamespace(type=By.XPATH, id="//*[@id='app_totp']")

    def signin_with_github():
        """Sign In page > GITHUB button."""
        return SimpleNamespace(type=By.CSS_SELECTOR, id="cv-button.auth-button")

    def signin_with_your_identity_provider():
        """Sign In page > 'Sign in with you identity provider' button."""
        return SimpleNamespace(type=By.CSS_SELECTOR, id="input.js-sign-in-button")

    _signin = {
        "oauth_authorize": signin_oauth_authorize,
        "sso_continue": signin_sso_continue,
        "teradata_email": signin_teradata_email,
        "teradata_next": signin_teradata_next,
        "teradata_password": signin_teradata_password,
        "teradata_signin": signin_teradata_signin,
        "teradata_stay_signedin_yes": signin_teradata_stay_signedin_yes,
        "username": signin_username,
        "password": signin_password,
        "use_authenticator": signin_use_authenticator,
        "auth_code": signin_auth_code,
        "with_github": signin_with_github,
        "with_your_identity_provider": signin_with_your_identity_provider
    }
    signin = SimpleNamespace(**_signin)

    # Locators for Aiu.your_profile section

    def your_profile_api_keys():
        """Your Profile section > API Keys value."""
        return SimpleNamespace(type=By.CSS_SELECTOR, id="div.container-third div.apiKeys p.api-key")

    def your_profile_view_all():
        """Your Profile section > VIEW ALL button."""
        return SimpleNamespace(type=By.CSS_SELECTOR, id="cv-button.view-button")

    _your_profile = {
        "api_keys": your_profile_api_keys,
        "view_all": your_profile_view_all
    }
    your_profile = SimpleNamespace(**_your_profile)

    # Locators for Aiu.your_projects section

    def your_projects_view_all():
        """Your Projects section > VIEW ALL button."""
        return SimpleNamespace(type=By.CSS_SELECTOR, id="cv-button.view-button-projects")

    _your_projects = {
        "view_all": your_projects_view_all
    }
    your_projects = SimpleNamespace(**_your_projects)


class Other(object):
    """A class for Other page locators."""

    # Locators for main page
    def hsts():
        """http://www.neverssl.com > HSTS link (as an example of non-HTTPS URLS, only)."""
        return SimpleNamespace(type=By.XPATH, id="//a[.='HSTS']")

    _home = {
        "hsts": hsts
    }
    home = SimpleNamespace(**_home)
