"""Session persistence and client factory for the ft CLI."""

from __future__ import annotations

import json
import os
import stat
import sys
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator

import httpx

from fidelity_trader import FidelityClient
from fidelity_trader.cli._config import get_config_dir, SESSION_FILE_NAME, ENV_ACCOUNT
from fidelity_trader.cli._output import print_error


def _session_path() -> Path:
    """Return the path to the session file."""
    return get_config_dir() / SESSION_FILE_NAME


def save_session(http_client: httpx.Client) -> None:
    """Persist cookies from an authenticated httpx.Client to disk."""
    cookies: dict[str, str] = {}
    for cookie in http_client.cookies.jar:
        cookies[cookie.name] = cookie.value

    payload = {
        "version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "cookies": cookies,
    }

    path = _session_path()
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    # Restrict file permissions on Unix (owner read/write only)
    if sys.platform != "win32":
        path.chmod(stat.S_IRUSR | stat.S_IWUSR)


def load_session_data() -> dict | None:
    """Read session file and return parsed data, or None if missing."""
    path = _session_path()
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def delete_session() -> bool:
    """Delete the session file. Returns True if a file was deleted."""
    path = _session_path()
    if path.exists():
        path.unlink()
        return True
    return False


@contextmanager
def get_client(
    live_trading: bool = False,
) -> Generator[FidelityClient, None, None]:
    """Context manager that yields a FidelityClient with restored session cookies.

    Loads cookies from the session file and injects them into the client's
    shared httpx.Client, then marks the auth session as authenticated.

    Args:
        live_trading: If True, enables live order placement on the client.

    Raises FileNotFoundError if no session file exists.
    """
    data = load_session_data()
    if data is None:
        raise FileNotFoundError("No session file found")

    cookies = data.get("cookies", {})
    client = FidelityClient(live_trading=live_trading)
    try:
        # Inject saved cookies into the shared httpx.Client cookie jar
        for name, value in cookies.items():
            client._http.cookies.set(name, value, domain=".fidelity.com")

        # Mark the auth layer as authenticated (cookies are already valid)
        client._auth._authenticated = True

        yield client
    finally:
        client.close()


def resolve_account(
    client: FidelityClient,
    account_flag: str | None,
) -> str:
    """Resolve which account to use.

    Priority:
      1. --account flag if provided
      2. FIDELITY_ACCOUNT env var
      3. If exactly one account, use it automatically
      4. If multiple, list them and exit asking the user to specify
    """
    # 1. Explicit flag
    if account_flag:
        return account_flag

    # 2. Environment variable
    env_account = os.environ.get(ENV_ACCOUNT)
    if env_account:
        return env_account

    # 3/4. Discover accounts
    resp = client.accounts.discover_accounts()
    account_numbers = [a.acct_num for a in resp.accounts if a.acct_num]

    if len(account_numbers) == 1:
        return account_numbers[0]

    if len(account_numbers) == 0:
        print_error("No accounts found.")
        raise SystemExit(1)

    # Multiple accounts — print them and ask user to pick
    print_error("Multiple accounts found. Specify one with --account or $FIDELITY_ACCOUNT:")
    for acct in resp.accounts:
        name = ""
        if acct.preference_detail and acct.preference_detail.name:
            name = f" ({acct.preference_detail.name})"
        acct_type = acct.acct_sub_type_desc or acct.acct_type or ""
        print(f"  {acct.acct_num}  {acct_type}{name}")
    raise SystemExit(1)
