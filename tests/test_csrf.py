import httpx
import respx
from fidelity_trader._http import BASE_URL, AUTH_URL
from fidelity_trader.auth.session import AuthSession

@respx.mock
def test_get_csrf_token():
    respx.get(f"{BASE_URL}/prgw/digital/research/api/tokens").mock(
        return_value=httpx.Response(200, json={"csrfToken": "abc123token"})
    )
    client = httpx.Client()
    auth = AuthSession(client, BASE_URL, AUTH_URL)
    token = auth.get_csrf_token()
    assert token == "abc123token"
    client.close()

@respx.mock
def test_csrf_token_cached():
    route = respx.get(f"{BASE_URL}/prgw/digital/research/api/tokens").mock(
        return_value=httpx.Response(200, json={"csrfToken": "abc123token"})
    )
    client = httpx.Client()
    auth = AuthSession(client, BASE_URL, AUTH_URL)
    auth.get_csrf_token()
    auth.get_csrf_token()
    assert route.call_count == 1
    client.close()

@respx.mock
def test_csrf_headers():
    respx.get(f"{BASE_URL}/prgw/digital/research/api/tokens").mock(
        return_value=httpx.Response(200, json={"csrfToken": "abc123token"})
    )
    client = httpx.Client()
    auth = AuthSession(client, BASE_URL, AUTH_URL)
    headers = auth.csrf_headers()
    assert headers["X-CSRF-TOKEN"] == "abc123token"
    client.close()
