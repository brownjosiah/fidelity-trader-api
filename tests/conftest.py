import httpx
import pytest

from fidelity_trader._http import BASE_URL, AUTH_URL

@pytest.fixture
def mock_http():
    client = httpx.Client()
    yield client
    client.close()

@pytest.fixture
def fidelity_response():
    def _make(message: str, code: int = 1200, **extra):
        resp = {
            "responseBaseInfo": {
                "sessionTokens": None,
                "status": {"code": code, "message": message},
                "links": [],
            }
        }
        resp.update(extra)
        return resp
    return _make
