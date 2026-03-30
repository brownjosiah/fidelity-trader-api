"""Tests for the authentication flow."""

import httpx
import pytest
import respx

from fidelity_trader.auth.session import AuthSession
from fidelity_trader.exceptions import AuthenticationError
from fidelity_trader._http import BASE_URL, AUTH_URL


@respx.mock
def test_login_success(fidelity_response):
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
        return_value=httpx.Response(200, json=fidelity_response("User Identified"))
    )
    # Step 4: select remembered username
    respx.post(f"{AUTH_URL}/user/identity/remember/username/1").mock(
        return_value=httpx.Response(200, json=fidelity_response("User Identified"))
    )
    # Step 5: password auth
    respx.post(f"{AUTH_URL}/user/factor/password/authentication").mock(
        return_value=httpx.Response(200, json=fidelity_response("User Authenticated"))
    )
    # Step 6: update remembered username
    respx.put(f"{AUTH_URL}/user/identity/remember/username").mock(
        return_value=httpx.Response(200, json=fidelity_response("OK"))
    )
    # Step 7: create session
    session_resp = fidelity_response("Session Created", authenticators=[])
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
def test_login_bad_password(fidelity_response):
    respx.get(f"{BASE_URL}/prgw/digital/login/atp").mock(
        return_value=httpx.Response(200)
    )
    respx.delete(f"{AUTH_URL}/user/session/login").mock(
        return_value=httpx.Response(204)
    )
    respx.get(f"{AUTH_URL}/user/identity/remember/username").mock(
        return_value=httpx.Response(200, json=fidelity_response("User Identified"))
    )
    respx.post(f"{AUTH_URL}/user/identity/remember/username/1").mock(
        return_value=httpx.Response(200, json=fidelity_response("User Identified"))
    )
    respx.post(f"{AUTH_URL}/user/factor/password/authentication").mock(
        return_value=httpx.Response(
            200, json=fidelity_response("Authentication Failed", code=1400)
        )
    )

    client = httpx.Client()
    auth = AuthSession(client, BASE_URL, AUTH_URL)

    with pytest.raises(AuthenticationError, match="Authentication Failed"):
        auth.login("testuser", "wrongpass")

    assert not auth.is_authenticated
    client.close()
