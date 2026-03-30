"""Main client that composes all Fidelity API modules."""

import httpx

from fidelity_trader.auth.session import AuthSession


class FidelityClient:
    """Unofficial Fidelity Trader+ API client.

    Usage:
        client = FidelityClient()
        client.login(username="...", password="...")
        # client is now authenticated and can make API calls
    """

    BASE_URL = "https://digital.fidelity.com"
    AUTH_URL = "https://ecaap.fidelity.com"

    def __init__(self) -> None:
        self._http = httpx.Client(
            follow_redirects=True,
            timeout=30.0,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/146.0.0.0 Safari/537.36 Edg/146.0.0.0 "
                    "ATPNext/4.4.1.7 FTPlusDesktop/4.4.1.7"
                ),
                "AppId": "RETAIL-CC-LOGIN-SDK",
                "AppName": "PILoginExperience",
                "Content-Type": "application/json",
                "Accept": "*/*",
                "Origin": "https://digital.fidelity.com",
                "Referer": "https://digital.fidelity.com/",
                "Accept-Token-Type": "ET",
                "Accept-Token-Location": "HEADER",
                "Token-Location": "HEADER",
                "Cache-Control": "no-cache, no-store, must-revalidate",
            },
        )
        self._auth = AuthSession(self._http, self.BASE_URL, self.AUTH_URL)

    def login(self, username: str, password: str) -> dict:
        """Authenticate with Fidelity and establish a session.

        Returns the session creation response.
        """
        return self._auth.login(username, password)

    def logout(self) -> None:
        """Clear the current session."""
        self._auth.logout()

    @property
    def is_authenticated(self) -> bool:
        return self._auth.is_authenticated

    def close(self) -> None:
        self._http.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
