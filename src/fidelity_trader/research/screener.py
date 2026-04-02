"""Screener/scanner API using LiveVol's service integrated into Fidelity Trader+.

The screener requires a three-step SAML authentication flow:
1. Get a SAML assertion from Fidelity
2. Exchange the SAML assertion for a LiveVol JWT token
3. Use the JWT token to execute scans

Traffic captured from Fidelity Trader+ desktop application.
"""

from __future__ import annotations

from typing import Optional

import httpx

from fidelity_trader._http import BASE_URL
from fidelity_trader.models.screener import LiveVolSession, ScanResult

LIVEVOL_URL = "https://fidelity.apps.livevol.com"
LIVEVOL_AUTH_URL = "https://fidelity-widgets.financial.com"

_SAML_PATH = "/ftgw/digital/rschwidgets/api/saml"
_SAML_LOGIN_PATH = "/auth/api/v1/sessions/samllogin"
_EXECUTE_SCAN_PATH = "/DataService/ScannerServiceReference.asmx/ExecuteScan"


class ScreenerAPI:
    """Client for the LiveVol screener integrated into Fidelity Trader+."""

    def __init__(self, http: httpx.Client) -> None:
        self._http = http
        self._session: Optional[LiveVolSession] = None

    def _get_saml_assertion(self) -> str:
        """Step 1: Fetch SAML assertion from Fidelity.

        GET to BASE_URL/ftgw/digital/rschwidgets/api/saml
        Returns a plain-text base64-encoded SAML assertion.
        """
        resp = self._http.get(f"{BASE_URL}{_SAML_PATH}")
        resp.raise_for_status()
        return resp.text.strip()

    def _exchange_saml(self, saml_assertion: str) -> LiveVolSession:
        """Step 2: Exchange SAML assertion for a LiveVol session + JWT token.

        POST to LIVEVOL_AUTH_URL with form-encoded SAMLResponse body.
        Returns a LiveVolSession with sid, token, and expires_at.
        """
        resp = self._http.post(
            f"{LIVEVOL_AUTH_URL}{_SAML_LOGIN_PATH}",
            params={"fetchToken": "true"},
            data={"SAMLResponse": saml_assertion},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        resp.raise_for_status()
        body = resp.json()
        return LiveVolSession(
            sid=body["sid"],
            token=body["token"],
            expires_at=body["expiresAt"],
        )

    def authenticate(self) -> LiveVolSession:
        """Run the full 3-step SAML authentication flow.

        1. Fetch SAML assertion from Fidelity
        2. Exchange assertion for LiveVol JWT token
        3. Cache and return the session

        Returns the LiveVolSession with the JWT token needed for scans.
        """
        saml_assertion = self._get_saml_assertion()
        session = self._exchange_saml(saml_assertion)
        self._session = session
        return session

    def execute_scan(
        self, scan_id: int, token: Optional[str] = None
    ) -> ScanResult:
        """Execute a scanner scan by ID.

        POST to LIVEVOL_URL/DataService/ScannerServiceReference.asmx/ExecuteScan
        with form-encoded TOKEN and SCANID. Returns parsed XML ScanResult.

        If no token is provided, uses the cached token from authenticate().
        Raises ValueError if no token is available.

        Args:
            scan_id: The scan identifier (e.g. 2 for call volume scan).
            token: Optional JWT token. If None, uses cached token.

        Returns:
            ScanResult with parsed rows from the scan.
        """
        if token is None:
            if self._session is None:
                raise ValueError(
                    "No token provided and no cached session. "
                    "Call authenticate() first or pass a token."
                )
            token = self._session.token

        resp = self._http.post(
            f"{LIVEVOL_URL}{_EXECUTE_SCAN_PATH}",
            data={"TOKEN": token, "SCANID": str(scan_id)},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        resp.raise_for_status()
        return ScanResult.from_xml(resp.text)
