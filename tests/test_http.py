import httpx
from fidelity_trader._http import create_session, REQUEST_HEADERS

def test_create_session_returns_httpx_client():
    client = create_session()
    assert isinstance(client, httpx.Client)
    assert client.headers["AppId"] == "RETAIL-CC-LOGIN-SDK"
    client.close()

def test_create_session_has_required_headers():
    client = create_session()
    assert "ATPNext" in client.headers["User-Agent"]
    assert client.headers["Content-Type"] == "application/json"
    client.close()
