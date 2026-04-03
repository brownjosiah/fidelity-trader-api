import re

import httpx
import pytest



def strip_ansi(text: str) -> str:
    """Remove ANSI escape codes from text so assertions work in non-TTY (CI)."""
    return re.sub(r'\x1b\[[0-9;]*m', '', text)

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
