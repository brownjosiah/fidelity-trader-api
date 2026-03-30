"""Fidelity authentication flow based on captured API traffic.

Login flow:
  1. GET  /prgw/digital/login/atp          -- init login page / session cookie
  2. DELETE ecaap/user/session/login        -- clear stale sessions
  3. GET  ecaap/user/identity/remember/username  -- check remembered user
  4. POST ecaap/user/identity/remember/username/1 -- select remembered user (gets ET token)
  5. POST ecaap/user/factor/password/authentication -- submit credentials
  6. PUT  ecaap/user/identity/remember/username   -- update remembered user
  7. POST ecaap/user/session/login          -- create authenticated session (gets ATC/FC/RC/SC)
"""

import httpx
from fidelity_trader._http import make_req_id
from fidelity_trader.exceptions import AuthenticationError


class AuthSession:
    """Handles the multi-step Fidelity login handshake."""

    def __init__(self, http: httpx.Client, base_url: str, auth_url: str) -> None:
        self._http = http
        self._base_url = base_url
        self._auth_url = auth_url
        self._authenticated = False

    @property
    def is_authenticated(self) -> bool:
        return self._authenticated

    def login(self, username: str, password: str) -> dict:
        """Execute the full login flow. Returns session creation response."""

        # Step 1: Init login page (sets initial cookies like SESSION_SCTX)
        self._http.get(
            f"{self._base_url}/prgw/digital/login/atp",
            params={
                "exp": "new",
                "AuthRedUrl": f"{self._base_url}/ftgw/digital/portfolio/extendsession",
            },
        )

        # Step 2: Clear any existing session
        self._http.request(
            "DELETE",
            f"{self._auth_url}/user/session/login",
            headers={"fsreqid": make_req_id(), "Accept-Token-Type": "FAC"},
            json={},
        )

        # Step 3: Check for remembered username
        self._http.get(
            f"{self._auth_url}/user/identity/remember/username",
            headers={"fsreqid": make_req_id()},
        )

        # Step 4: Select remembered username (gets ET token cookie)
        self._http.post(
            f"{self._auth_url}/user/identity/remember/username/1",
            headers={"fsreqid": make_req_id()},
            json={},
        )

        # Step 5: Submit credentials
        auth_resp = self._http.post(
            f"{self._auth_url}/user/factor/password/authentication",
            headers={"fsreqid": make_req_id()},
            json={"username": username, "password": password},
        )
        auth_data = auth_resp.json()
        status = auth_data.get("responseBaseInfo", {}).get("status", {})
        if status.get("code") != 1200:
            raise AuthenticationError(
                f"Authentication failed: {status.get('message', 'Unknown error')}"
            )

        # Step 6: Update remembered username
        self._http.put(
            f"{self._auth_url}/user/identity/remember/username",
            headers={"fsreqid": make_req_id()},
            json={},
        )

        # Step 7: Create session (gets ATC, FC, RC, SC cookies)
        session_resp = self._http.post(
            f"{self._auth_url}/user/session/login",
            headers={
                "fsreqid": make_req_id(),
                "eventtype": "LOGIN",
                "sub_eventtype": "rt_login",
            },
            json={},
        )
        session_data = session_resp.json()
        session_status = session_data.get("responseBaseInfo", {}).get("status", {})
        if session_status.get("code") != 1200:
            raise AuthenticationError(
                f"Session creation failed: {session_status.get('message', 'Unknown error')}"
            )

        self._authenticated = True
        return session_data

    def logout(self) -> None:
        """Clear the session."""
        if self._authenticated:
            self._http.request(
                "DELETE",
                f"{self._auth_url}/user/session/login",
                headers={"fsreqid": make_req_id(), "Accept-Token-Type": "FAC"},
                json={},
            )
            self._authenticated = False
