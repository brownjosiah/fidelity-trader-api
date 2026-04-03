import httpx
from fidelity_trader._http import create_session
from fidelity_trader._http import create_atp_session, ATP_HEADERS, DPSERVICE_URL, STREAMING_NEWS_URL

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

def test_create_atp_session_returns_httpx_client():
    client = create_atp_session()
    assert isinstance(client, httpx.Client)
    assert client.headers["AppId"] == "AP149323"
    assert client.headers["AppName"] == "Active Trader Desktop for Windows"
    client.close()

def test_atp_headers_match_captured_traffic():
    assert ATP_HEADERS["AppId"] == "AP149323"
    assert ATP_HEADERS["Content-Type"] == "application/json; charset=utf-8"

def test_dpservice_url_defined():
    assert DPSERVICE_URL == "https://dpservice.fidelity.com"
    assert STREAMING_NEWS_URL == "https://streaming-news.mds.fidelity.com"
