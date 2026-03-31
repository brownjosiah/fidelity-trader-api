"""Security context API — user entitlements and permissions."""

import httpx

from fidelity_trader._http import BASE_URL
from fidelity_trader.models.security_context import SecurityContextResponse


class SecurityContextAPI:
    """Query user entitlements and permissions.

    This endpoint must be called after login to enable real-time quote
    access on fastquote.fidelity.com.
    """

    def __init__(self, http: httpx.Client) -> None:
        self._http = http

    def get_context(self) -> SecurityContextResponse:
        """Fetch the current security context (entitlements, persona, etc.)."""
        resp = self._http.post(
            f"{BASE_URL}/ftgw/digital/pico/api/v1/context/security",
            json={},
        )
        resp.raise_for_status()
        return SecurityContextResponse.from_api_response(resp.json())
