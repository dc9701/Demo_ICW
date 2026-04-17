"""
github_oauth_requests.py.

Description: This module contains the Github OAuthApp step definitions.
"""
import requests
from bs4 import BeautifulSoup
import re
import pyotp
import os


def init_session() -> requests.Session:
    """Create and return a new requests Session."""
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Checkout-for-GitHub-OAuthScript)"
    })
    return session


def fetch_login_tokens(session: requests.Session) -> dict:
    """GET /login and parse out authenticity_token, timestamp, and timestamp_secret."""
    url = "https://github.com/login"
    resp = session.get(url)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    form = soup.find("form", attrs={"action": "/session"})
    if not form:
        raise RuntimeError("Couldn't find the login form on /login")
    return {
        "authenticity_token": form.find("input", {"name": "authenticity_token"})["value"],
        "timestamp": form.find("input", {"name": "timestamp"})["value"],
        "timestamp_secret": form.find("input", {"name": "timestamp_secret"})["value"],
    }


def do_u2f_fragment(session: requests.Session) -> None:
    """Hit the U2F fragment endpoint to set some cookies before primary login."""
    url = "https://github.com/u2f/login_fragment"
    resp = session.get(url, params={"is_emu_login": "false"})
    resp.raise_for_status()
    # After this, session.cookies will hold _device_id and _gh_sess.


def do_primary_login(session: requests.Session, username: str, password: str, tokens: dict) -> None:
    """POST /session with username/password."""
    payload = {
        "commit": "Sign in",
        "authenticity_token": tokens["authenticity_token"],
        "login": username,
        "password": password,
        "webauthn-conditional": "undefined",
        "javascript-support": "true",
        "webauthn-support": "supported",
        "webauthn-iuvpaa-support": "unsupported",
        "return_to": "https://github.com/login",
        "allow_signup": "",
        "client_id": "",
        "integration": "",
        "required_field_fa1e": "",
        "timestamp": tokens["timestamp"],
        "timestamp_secret": tokens["timestamp_secret"],
    }
    url = "https://github.com/session"
    resp = session.post(url, data=payload)
    resp.raise_for_status()
    if resp.status_code not in (200, 302):
        raise RuntimeError(f"GitHub /session login failed with {resp.status_code}")


def fetch_two_factor_token(session: requests.Session) -> str:
    """GET /sessions/two-factor/app and parse out authenticity_token for 2FA."""
    url = "https://github.com/sessions/two-factor/app"
    resp = session.get(url)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    form = soup.find("form", attrs={"action": "/sessions/two-factor"})
    if not form:
        raise RuntimeError("Couldn't find the two-factor form")
    return form.find("input", {"name": "authenticity_token"})["value"]


def submit_two_factor(session: requests.Session, auth_token: str, totp_secret: str) -> None:
    """POST TOTP (from `totp_secret`) to /sessions/two-factor."""
    otp = pyotp.TOTP(totp_secret).now()
    payload = {
        "authenticity_token": auth_token,
        "app_otp": otp
    }
    url = "https://github.com/sessions/two-factor"
    resp = session.post(url, data=payload)
    resp.raise_for_status()
    # Session.cookies includes a valid _gh_sess if successful.


def fetch_oauth_form(session: requests.Session) -> str:
    """GET /settings/applications/new and return the authenticity_token in that form."""
    url = "https://github.com/settings/applications/new"
    resp = session.get(url)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    form = soup.find("form", attrs={"action": "/settings/applications"})
    if not form:
        raise RuntimeError("Couldn't find the OAuth application form")
    return form.find("input", {"name": "authenticity_token"})["value"]


def create_oauth_app(
    session: requests.Session,
    auth_token: str,
    name: str,
    url: str,
    description: str,
    callback_url: str,
    device_flow: bool = False
) -> None:
    """POST to /settings/applications to create a new OAuth Application."""
    payload = {
        "authenticity_token": auth_token,
        "oauth_application[name]": name,
        "oauth_application[url]": url,
        "oauth_application[description]": description,
        "oauth_application[callback_url]": callback_url,
        "oauth_application[device_flow_enabled]": "1" if device_flow else "0"
    }
    post_url = "https://github.com/settings/applications"
    resp = session.post(post_url, data=payload)
    resp.raise_for_status()
    if resp.status_code not in (200, 302):
        raise RuntimeError(f"Failed to create OAuth App: HTTP {resp.status_code}")


def get_oauth_app_id(session: requests.Session, app_name: str) -> str:
    """
    GET /settings/developers and return the numeric app_id for the first.
    """
    url = "https://github.com/settings/developers"
    resp = session.get(url)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    candidates = soup.find_all(
        "a",
        class_="text-bold",
        href=re.compile(r"^/settings/applications/\d+$")
    )
    for link in candidates:
        if link.text.strip() == app_name:
            return link["href"].rsplit("/", 1)[-1]

    raise RuntimeError(f"No application named {app_name!r} found on {url}")


def fetch_advanced_token(session: requests.Session, app_id: str) -> str:
    """GET the /settings/applications/{app_id}/advanced page and return its authenticity_token."""
    url = f"https://github.com/settings/applications/{app_id}/advanced"
    resp = session.get(url)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    form = soup.find("form", attrs={"action": f"/settings/applications/{app_id}"})
    if not form:
        raise RuntimeError("Couldn't find the OAuth 'advanced' form for app_id " + app_id)
    return form.find("input", {"name": "authenticity_token"})["value"]


def delete_oauthapp(session: requests.Session, app_id: str, auth_token: str) -> None:
    """DELETE the OAuth app."""
    payload = {
        "_method": "delete",
        "authenticity_token": auth_token
    }
    post_url = f"https://github.com/settings/applications/{app_id}"
    resp = session.post(post_url, data=payload)
    resp.raise_for_status()


def parse_client_id_and_secret(session: requests.Session, app_id: str) -> dict:
    """
    1) GET the “Advanced” page at /settings/applications/{app_id}/advanced.

       - Parse out the Client ID (in a <code>…</code> tag).
       - Parse out the hidden authenticity_token for the client‐secret form.
    2) POST to  /settings/applications/{app_id}/client_secret
       with fields: authenticity_token, id, sudo_referrer, sudo_app_otp.
    3) The response HTML will contain <code id="new-oauth-token" class="token">…</code>.
       Extract that as the new Client Secret.
    Returns {"ClientID": <str>, "ClientSecret": <str>}.
    """
    # Fetch the “Advanced” page
    advanced_url = f"https://github.com/settings/applications/{app_id}"
    resp = session.get(advanced_url)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")

    # Extract Client ID
    code_tag = soup.find("code")
    if not code_tag:
        raise RuntimeError("Could not find <code> tag for Client ID on advanced page")
    client_id = code_tag.get_text(strip=True)

    # Find <input name="authenticity_token"> inside the form that posts to “/client_secret”
    form = soup.find("form", {"action": f"/settings/applications/{app_id}/client_secret"})
    if not form:
        raise RuntimeError("Could not find the client_secret form on the advanced page")

    hidden_token_input = form.find("input", {"name": "authenticity_token"})
    if not hidden_token_input or not hidden_token_input.get("value"):
        raise RuntimeError("Could not find authenticity_token in the client_secret form")
    authenticity_token = hidden_token_input["value"]

    # POST payload to generate a new client secret.
    totp_secret = os.getenv("GITHUB_TOTP_SECRET")
    if not totp_secret:
        raise RuntimeError("Environment variable GITHUB_TOTP_SECRET is required for 2FA re-authentication")

    otp_code = pyotp.TOTP(totp_secret).now()

    post_url = f"https://github.com/settings/applications/{app_id}/client_secret"
    payload = {
        "authenticity_token": authenticity_token,
        "id":                app_id,
        "sudo_referrer":     advanced_url,
        "sudo_app_otp":      otp_code
    }

    post_resp = session.post(post_url, data=payload)
    post_resp.raise_for_status()

    # Parse the response HTML for the new client secret:
    soup2 = BeautifulSoup(post_resp.text, "html.parser")
    secret_code_tag = soup2.find("code", {"id": "new-oauth-token", "class": "token"})
    if not secret_code_tag:
        raise RuntimeError("Failed to find <code id='new-oauth-token'> after POST to /client_secret")

    client_secret = secret_code_tag.get_text(strip=True)

    return {"ClientID": client_id, "ClientSecret": client_secret}


def delete_all_oauth_apps_with_name(session: requests.Session, app_name: str) -> None:
    """
    Find every OAuth App whose visible name == app_name, then delete them one by one.

    1) GET /settings/developers → find all <a class="text-bold" href="/settings/applications/<id>">link.text</a>
       where link.text.strip() == app_name.
    2) For each such <id>:
         a) GET /settings/applications/<id>/advanced  → parse the hidden authenticity_token
         b) POST to /settings/applications/<id> with _method=delete + authenticity_token
    """
    dev_url = "https://github.com/settings/developers"
    resp = session.get(dev_url)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    candidate_links = soup.find_all(
        "a",
        class_="text-bold",
        href=re.compile(r"^/settings/applications/\d+$")
    )

    for link in candidate_links:
        if link.text.strip() == app_name:
            # Extract the numeric app_id
            href = link["href"]
            app_id = href.rsplit("/", 1)[-1]
            # Fetch the “advanced” page to get authenticity_token for deletion
            advanced_url = f"https://github.com/settings/applications/{app_id}/advanced"
            adv_resp = session.get(advanced_url)
            adv_resp.raise_for_status()

            adv_soup = BeautifulSoup(adv_resp.text, "html.parser")

            delete_form = adv_soup.find("form", {"action": f"/settings/applications/{app_id}"})
            if not delete_form:
                raise RuntimeError(f"Could not find delete form for app_id={app_id}")

            token_input = delete_form.find("input", {"name": "authenticity_token"})
            if not token_input or not token_input.get("value"):
                raise RuntimeError(f"Could not find authenticity_token on advanced page for app_id={app_id}")

            authenticity_token = token_input["value"]

            # Perform the actual delete POST
            delete_url = f"https://github.com/settings/applications/{app_id}"
            payload = {
                "_method": "delete",
                "authenticity_token": authenticity_token
            }
            del_resp = session.post(delete_url, data=payload)
            del_resp.raise_for_status()

            print(f"Deleted OAuth App id={app_id} (name='{app_name}')")
