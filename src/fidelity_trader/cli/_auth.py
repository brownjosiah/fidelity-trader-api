"""Authentication commands: login, logout, status."""

from __future__ import annotations

import os
from typing import Optional

import typer

from fidelity_trader import FidelityClient
from fidelity_trader.exceptions import AuthenticationError
from fidelity_trader.cli._config import ENV_USERNAME, ENV_PASSWORD, ENV_TOTP_SECRET
from fidelity_trader.cli._errors import handle_errors
from fidelity_trader.cli._output import print_error, print_success, print_table
from fidelity_trader.cli._session import (
    delete_session,
    get_client,
    load_session_data,
    save_session,
)

auth_app = typer.Typer(help="Authentication commands")


@auth_app.command("login")
@handle_errors
def login(
    username: Optional[str] = typer.Option(None, "--username", "-u", help="Fidelity username"),
    password: Optional[str] = typer.Option(None, "--password", "-p", help="Fidelity password"),
    totp_secret: Optional[str] = typer.Option(
        None, "--totp-secret", help="TOTP base32 secret key (auto-generates codes)"
    ),
    totp_token: Optional[str] = typer.Option(
        None, "--totp-token", "-t", help="6-digit TOTP code from your authenticator app"
    ),
) -> None:
    """Log in to Fidelity and save the session."""
    # Resolve credentials: flags -> env vars -> interactive prompt
    if not username:
        username = os.environ.get(ENV_USERNAME)
    if not username:
        username = typer.prompt("Username")

    if not password:
        password = os.environ.get(ENV_PASSWORD)
    if not password:
        password = typer.prompt("Password", hide_input=True)

    if not totp_secret:
        totp_secret = os.environ.get(ENV_TOTP_SECRET)

    # --totp-token takes precedence (explicit code from user's phone)
    # --totp-secret is for automation (base32 key, auto-generates codes)
    totp_input = totp_token or totp_secret

    # Authenticate
    client = FidelityClient()
    try:
        try:
            client.login(username, password, totp_secret=totp_input or None)
        except AuthenticationError as e:
            # If 2FA is required and no secret/token was provided, prompt for it
            if "2FA is required" in str(e) and not totp_input:
                totp_input = typer.prompt(
                    "2FA required. Enter your 6-digit code or TOTP secret key"
                )
                client = FidelityClient()  # Fresh client (old session is tainted)
                client.login(username, password, totp_secret=totp_input)
            else:
                raise
        save_session(client._http)
        print_success("Login successful!")

        # Show discovered accounts
        try:
            resp = client.accounts.discover_accounts()
            if resp.accounts:
                rows = []
                for acct in resp.accounts:
                    name = ""
                    if acct.preference_detail and acct.preference_detail.name:
                        name = acct.preference_detail.name
                    rows.append({
                        "account": acct.acct_num or "--",
                        "type": acct.acct_sub_type_desc or acct.acct_type or "--",
                        "name": name or "--",
                    })
                print_table(
                    rows=rows,
                    columns=[
                        {"header": "Account", "key": "account"},
                        {"header": "Type", "key": "type"},
                        {"header": "Name", "key": "name"},
                    ],
                    title="Accounts",
                )
        except Exception:
            pass  # Non-fatal — session is saved regardless
    except Exception:
        client.close()
        raise
    else:
        client.close()


@auth_app.command("logout")
@handle_errors
def logout() -> None:
    """Log out and delete the saved session."""
    # Try to call logout on the server if we have a session
    try:
        with get_client() as client:
            client.logout()
    except Exception:
        pass  # Best-effort server logout

    if delete_session():
        print_success("Logged out.")
    else:
        print_error("No active session found.")


@auth_app.command("status")
@handle_errors
def status() -> None:
    """Check the current session status."""
    data = load_session_data()
    if data is None:
        print_error("Not logged in. Run `ft login` first.")
        raise SystemExit(1)

    created_at = data.get("created_at", "unknown")
    cookie_count = len(data.get("cookies", {}))

    print_success(f"Session found (created: {created_at})")
    print(f"  Cookies: {cookie_count}")

    # Try to verify the session is still alive
    try:
        with get_client() as client:
            resp = client.accounts.discover_accounts()
            acct_count = len(resp.accounts)
            print_success(f"  Session is active ({acct_count} account(s))")
    except Exception:
        print_error("  Session may be expired. Run `ft login` to re-authenticate.")
