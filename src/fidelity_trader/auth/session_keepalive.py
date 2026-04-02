"""Session keep-alive API — extend/refresh the Fidelity session."""

import httpx

from fidelity_trader._http import BASE_URL

EXTEND_SESSION_URL = f"{BASE_URL}/ftgw/digital/portfolio/extendsession"


class SessionKeepAliveAPI:
    """Keep the Fidelity session alive by touching the extend-session endpoint.

    Fidelity sessions expire after ~30 minutes of inactivity.  A simple GET
    to the extend-session endpoint resets the inactivity timer (the response
    body is empty; the server just refreshes the session cookies).
    """

    def __init__(self, http: httpx.Client) -> None:
        self._http = http

    def extend_session(self) -> bool:
        """Send a keep-alive GET to reset the session inactivity timer.

        Returns ``True`` on a successful 200 response.
        Raises :class:`httpx.HTTPStatusError` on any non-2xx status.
        """
        resp = self._http.get(EXTEND_SESSION_URL)
        resp.raise_for_status()
        return True

    def is_session_alive(self) -> bool:
        """Convenience wrapper: returns ``True`` if the session is still
        valid, ``False`` if the keep-alive request fails for any reason.
        """
        try:
            return self.extend_session()
        except (httpx.HTTPStatusError, httpx.RequestError):
            return False
