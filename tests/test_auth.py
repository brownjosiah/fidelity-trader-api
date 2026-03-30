"""Tests for the authentication flow."""

import httpx
import pytest
import respx

from fidelity_trader.auth.session import AuthSession, AuthenticationError

AUTH_URL = "https://ecaap.fidelity.com"
BASE_URL = "https://digital.fidelity.com"


def _success_response(message: str, code: int = 1200) -> dict:
    return {
        "responseBaseInfo": {
            "sessionTokens": None,
            "status": {"code": code, "message": message},
            "links": [],
        }
    }


@respx.mock
def test_login_success():
    # Step 1: init login page
    respx.get(f"{BASE_URL}/prgw/digital/login/atp").mock(
        return_value=httpx.Response(200, text="<html>login</html>")
    )
    # Step 2: delete session
    respx.delete(f"{AUTH_URL}/user/session/login").mock(
        return_value=httpx.Response(204)
    )
    # Step 3: get remembered username
    respx.get(f"{AUTH_URL}/user/identity/remember/username").mock(
        return_value=httpx.Response(200, json=_success_response("User Identified"))
    )
    # Step 4: select remembered username
    respx.post(f"{AUTH_URL}/user/identity/remember/username/1").mock(
        return_value=httpx.Response(200, json=_success_response("User Identified"))
    )
    # Step 5: password auth
    respx.post(f"{AUTH_URL}/user/factor/password/authentication").mock(
        return_value=httpx.Response(200, json=_success_response("User Authenticated"))
    )
    # Step 6: update remembered username
    respx.put(f"{AUTH_URL}/user/identity/remember/username").mock(
        return_value=httpx.Response(200, json=_success_response("OK"))
    )
    # Step 7: create session
    session_resp = _success_response("Session Created")
    session_resp["authenticators"] = []
    respx.post(f"{AUTH_URL}/user/session/login").mock(
        return_value=httpx.Response(200, json=session_resp)
    )

    client = httpx.Client()
    auth = AuthSession(client, BASE_URL, AUTH_URL)
    result = auth.login("testuser", "testpass")

    assert auth.is_authenticated
    assert result["responseBaseInfo"]["status"]["message"] == "Session Created"
    client.close()


@respx.mock
def test_login_bad_password():
    respx.get(f"{BASE_URL}/prgw/digital/login/atp").mock(
        return_value=httpx.Response(200)
    )
    respx.delete(f"{AUTH_URL}/user/session/login").mock(
        return_value=httpx.Response(204)
    )
    respx.get(f"{AUTH_URL}/user/identity/remember/username").mock(
        return_value=httpx.Response(200, json=_success_response("User Identified"))
    )
    respx.post(f"{AUTH_URL}/user/identity/remember/username/1").mock(
        return_value=httpx.Response(200, json=_success_response("User Identified"))
    )
    respx.post(f"{AUTH_URL}/user/factor/password/authentication").mock(
        return_value=httpx.Response(
            200, json=_success_response("Authentication Failed", code=1400)
        )
    )

    client = httpx.Client()
    auth = AuthSession(client, BASE_URL, AUTH_URL)

    with pytest.raises(AuthenticationError, match="Authentication Failed"):
        auth.login("testuser", "wrongpass")

    assert not auth.is_authenticated
    client.close()
