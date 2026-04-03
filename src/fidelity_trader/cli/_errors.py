"""Error handler decorator for CLI commands."""

from __future__ import annotations

import functools
from typing import Any, Callable

import httpx

from fidelity_trader import (
    AuthenticationError,
    SessionExpiredError,
    CSRFTokenError,
    APIError,
)
from fidelity_trader.cli._output import print_error


def handle_errors(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator that catches SDK exceptions and prints user-friendly messages."""

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return func(*args, **kwargs)
        except KeyboardInterrupt:
            raise SystemExit(0)
        except AuthenticationError as exc:
            print_error(f"Authentication failed: {exc}")
            raise SystemExit(1)
        except SessionExpiredError:
            print_error("Session expired. Run `ft login` to re-authenticate.")
            raise SystemExit(1)
        except CSRFTokenError:
            print_error("Session error. Run `ft login` to re-authenticate.")
            raise SystemExit(1)
        except APIError as exc:
            print_error(f"API error: {exc}")
            raise SystemExit(1)
        except httpx.HTTPStatusError as exc:
            print_error(f"HTTP {exc.response.status_code} error")
            raise SystemExit(1)
        except httpx.ConnectError:
            print_error("Connection failed. Check your internet connection.")
            raise SystemExit(1)
        except FileNotFoundError:
            print_error("Not logged in. Run `ft login` first.")
            raise SystemExit(1)

    return wrapper
