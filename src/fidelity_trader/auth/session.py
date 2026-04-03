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
from fidelity_trader._http import make_req_id, REQUEST_HEADERS
from fidelity_trader.exceptions import AuthenticationError, CSRFTokenError

# Login-specific headers that override the ATP session defaults
_LOGIN_HEADERS = {
    "AppId": REQUEST_HEADERS["AppId"],
    "AppName": REQUEST_HEADERS["AppName"],
    "Content-Type": REQUEST_HEADERS["Content-Type"],
    "Accept": REQUEST_HEADERS["Accept"],
    "Origin": REQUEST_HEADERS["Origin"],
    "Referer": REQUEST_HEADERS["Referer"],
    "Accept-Token-Type": REQUEST_HEADERS["Accept-Token-Type"],
    "Accept-Token-Location": REQUEST_HEADERS["Accept-Token-Location"],
    "Token-Location": REQUEST_HEADERS["Token-Location"],
    "Cache-Control": REQUEST_HEADERS["Cache-Control"],
}


class AuthSession:
    """Handles the multi-step Fidelity login handshake."""

    def __init__(self, http: httpx.Client, base_url: str, auth_url: str) -> None:
        self._http = http
        self._base_url = base_url
        self._auth_url = auth_url
        self._authenticated = False
        self._csrf_token: str | None = None

    @property
    def is_authenticated(self) -> bool:
        return self._authenticated

    def login(self, username: str, password: str, totp_secret: str = None) -> dict:
        """Execute the full login flow. Returns session creation response.

        If totp_secret is provided, generates and submits a TOTP code for 2FA.
        """

        # Step 1: Init login page (sets initial cookies like SESSION_SCTX)
        self._http.get(
            f"{self._base_url}/prgw/digital/login/atp",
            params={
                "exp": "new",
                "AuthRedUrl": f"{self._base_url}/ftgw/digital/portfolio/extendsession",
            },
            headers=_LOGIN_HEADERS,
        )

        # Step 2: Clear any existing session
        self._http.request(
            "DELETE",
            f"{self._auth_url}/user/session/login",
            headers={**_LOGIN_HEADERS, "fsreqid": make_req_id(), "Accept-Token-Type": "FAC"},
            json={},
        )

        # Step 3: Check for remembered username
        self._http.get(
            f"{self._auth_url}/user/identity/remember/username",
            headers={**_LOGIN_HEADERS, "fsreqid": make_req_id()},
        )

        # Step 4: Select remembered username (gets ET token cookie)
        self._http.post(
            f"{self._auth_url}/user/identity/remember/username/1",
            headers={**_LOGIN_HEADERS, "fsreqid": make_req_id()},
            json={},
        )

        # Step 5: Submit credentials
        auth_resp = self._http.post(
            f"{self._auth_url}/user/factor/password/authentication",
            headers={**_LOGIN_HEADERS, "fsreqid": make_req_id()},
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
            headers={**_LOGIN_HEADERS, "fsreqid": make_req_id()},
            json={},
        )

        # Step 7: Create session (gets ATC, FC, RC, SC cookies)
        session_data = self._create_session()
        session_status = session_data.get("responseBaseInfo", {}).get("status", {})

        # Step 7b: Handle 2FA if session returns code 1201
        if session_status.get("code") == 1201:
            if not totp_secret:
                raise AuthenticationError(
                    "2FA is required. Provide totp_secret (base32 secret key) "
                    "or totp_code (6-digit code from your authenticator app)."
                )

            # Detect whether this is a raw 6-digit code or a base32 secret key
            totp_code = self._resolve_totp_code(totp_secret)

            # Submit TOTP code
            totp_resp = self._http.post(
                f"{self._auth_url}/user/factor/totp/authentication",
                headers={**_LOGIN_HEADERS, "fsreqid": make_req_id()},
                json={"securityCode": totp_code},
            )
            totp_data = totp_resp.json()
            totp_status = totp_data.get("responseBaseInfo", {}).get("status", {})
            if totp_status.get("code") != 1200:
                raise AuthenticationError(
                    f"2FA failed: {totp_status.get('message', 'Unknown error')}"
                )

            # Retry session creation after 2FA
            session_data = self._create_session()
            session_status = session_data.get("responseBaseInfo", {}).get("status", {})

        if session_status.get("code") != 1200:
            raise AuthenticationError(
                f"Session creation failed: {session_status.get('message', 'Unknown error')}"
            )

        self._authenticated = True
        return session_data

    @staticmethod
    def _resolve_totp_code(totp_input: str) -> str:
        """Resolve a TOTP input to a 6-digit code.

        Accepts either:
        - A 6-digit code directly (e.g. "482913") — returned as-is
        - A base32 secret key (e.g. "JBSWY3DPEHPK3PXP") — generates current code via pyotp
        """
        stripped = totp_input.strip()
        if stripped.isdigit() and len(stripped) == 6:
            return stripped
        # Treat as base32 secret key
        try:
            import pyotp
            return pyotp.TOTP(stripped).now()
        except Exception as exc:
            raise AuthenticationError(
                f"Invalid TOTP input: expected a 6-digit code or a base32 secret key. Error: {exc}"
            ) from exc

    def _create_session(self) -> dict:
        """POST to session/login and return parsed JSON."""
        resp = self._http.post(
            f"{self._auth_url}/user/session/login",
            headers={
                **_LOGIN_HEADERS,
                "fsreqid": make_req_id(),
                "eventtype": "LOGIN",
                "sub_eventtype": "rt_login",
            },
            json={},
        )
        return resp.json()

    def get_csrf_token(self) -> str:
        """Fetch and cache the CSRF token from the tokens endpoint."""
        if self._csrf_token is not None:
            return self._csrf_token
        resp = self._http.get(f"{self._base_url}/prgw/digital/research/api/tokens")
        if resp.status_code != 200:
            raise CSRFTokenError(
                f"Failed to fetch CSRF token: HTTP {resp.status_code}"
            )
        data = resp.json()
        token = data.get("csrfToken")
        if not token:
            raise CSRFTokenError("CSRF token missing from response")
        self._csrf_token = token
        return self._csrf_token

    def csrf_headers(self) -> dict:
        """Return headers dict containing the CSRF token."""
        return {"X-CSRF-TOKEN": self.get_csrf_token()}

    def invalidate_csrf(self) -> None:
        """Clear the cached CSRF token."""
        self._csrf_token = None

    def logout(self) -> None:
        """Clear the session."""
        if self._authenticated:
            self._http.request(
                "DELETE",
                f"{self._auth_url}/user/session/login",
                headers={**_LOGIN_HEADERS, "fsreqid": make_req_id(), "Accept-Token-Type": "FAC"},
                json={},
            )
            self._authenticated = False
            self.invalidate_csrf()
