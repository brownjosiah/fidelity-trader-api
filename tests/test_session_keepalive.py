"""Tests for the session keep-alive / extend-session API."""

import httpx
import pytest
import respx

from fidelity_trader.auth.session_keepalive import (
    SessionKeepAliveAPI,
    EXTEND_SESSION_URL,
)
from fidelity_trader._http import BASE_URL


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

EXPECTED_URL = f"{BASE_URL}/ftgw/digital/portfolio/extendsession"


# ---------------------------------------------------------------------------
# URL / constant tests
# ---------------------------------------------------------------------------

class TestExtendSessionURL:
    def test_url_uses_base_url(self):
        assert EXTEND_SESSION_URL.startswith(BASE_URL)

    def test_url_path(self):
        assert EXTEND_SESSION_URL == EXPECTED_URL

    def test_url_not_dpservice(self):
        assert "dpservice" not in EXTEND_SESSION_URL


# ---------------------------------------------------------------------------
# extend_session() tests
# ---------------------------------------------------------------------------

class TestExtendSession:
    @respx.mock
    def test_returns_true_on_200(self):
        route = respx.get(EXPECTED_URL).mock(
            return_value=httpx.Response(200)
        )

        api = SessionKeepAliveAPI(httpx.Client())
        try:
            result = api.extend_session()
        finally:
            api._http.close()

        assert result is True
        assert route.called

    @respx.mock
    def test_returns_true_on_200_with_empty_body(self):
        route = respx.get(EXPECTED_URL).mock(
            return_value=httpx.Response(200, content=b"")
        )

        api = SessionKeepAliveAPI(httpx.Client())
        try:
            result = api.extend_session()
        finally:
            api._http.close()

        assert result is True
        assert route.called

    @respx.mock
    def test_raises_on_401(self):
        respx.get(EXPECTED_URL).mock(
            return_value=httpx.Response(401)
        )

        api = SessionKeepAliveAPI(httpx.Client())
        try:
            with pytest.raises(httpx.HTTPStatusError) as exc_info:
                api.extend_session()
            assert exc_info.value.response.status_code == 401
        finally:
            api._http.close()

    @respx.mock
    def test_raises_on_403(self):
        respx.get(EXPECTED_URL).mock(
            return_value=httpx.Response(403)
        )

        api = SessionKeepAliveAPI(httpx.Client())
        try:
            with pytest.raises(httpx.HTTPStatusError) as exc_info:
                api.extend_session()
            assert exc_info.value.response.status_code == 403
        finally:
            api._http.close()

    @respx.mock
    def test_raises_on_500(self):
        respx.get(EXPECTED_URL).mock(
            return_value=httpx.Response(500)
        )

        api = SessionKeepAliveAPI(httpx.Client())
        try:
            with pytest.raises(httpx.HTTPStatusError):
                api.extend_session()
        finally:
            api._http.close()

    @respx.mock
    def test_uses_get_method(self):
        route = respx.get(EXPECTED_URL).mock(
            return_value=httpx.Response(200)
        )

        api = SessionKeepAliveAPI(httpx.Client())
        try:
            api.extend_session()
        finally:
            api._http.close()

        assert route.calls[0].request.method == "GET"

    @respx.mock
    def test_no_request_body(self):
        route = respx.get(EXPECTED_URL).mock(
            return_value=httpx.Response(200)
        )

        api = SessionKeepAliveAPI(httpx.Client())
        try:
            api.extend_session()
        finally:
            api._http.close()

        assert route.calls[0].request.content == b""


# ---------------------------------------------------------------------------
# is_session_alive() tests
# ---------------------------------------------------------------------------

class TestIsSessionAlive:
    @respx.mock
    def test_returns_true_on_success(self):
        respx.get(EXPECTED_URL).mock(
            return_value=httpx.Response(200)
        )

        api = SessionKeepAliveAPI(httpx.Client())
        try:
            assert api.is_session_alive() is True
        finally:
            api._http.close()

    @respx.mock
    def test_returns_false_on_http_error(self):
        respx.get(EXPECTED_URL).mock(
            return_value=httpx.Response(401)
        )

        api = SessionKeepAliveAPI(httpx.Client())
        try:
            assert api.is_session_alive() is False
        finally:
            api._http.close()

    @respx.mock
    def test_returns_false_on_403(self):
        respx.get(EXPECTED_URL).mock(
            return_value=httpx.Response(403)
        )

        api = SessionKeepAliveAPI(httpx.Client())
        try:
            assert api.is_session_alive() is False
        finally:
            api._http.close()

    @respx.mock
    def test_returns_false_on_500(self):
        respx.get(EXPECTED_URL).mock(
            return_value=httpx.Response(500)
        )

        api = SessionKeepAliveAPI(httpx.Client())
        try:
            assert api.is_session_alive() is False
        finally:
            api._http.close()

    @respx.mock
    def test_returns_false_on_connection_error(self):
        respx.get(EXPECTED_URL).mock(
            side_effect=httpx.ConnectError("Connection refused")
        )

        api = SessionKeepAliveAPI(httpx.Client())
        try:
            assert api.is_session_alive() is False
        finally:
            api._http.close()

    @respx.mock
    def test_returns_false_on_timeout(self):
        respx.get(EXPECTED_URL).mock(
            side_effect=httpx.ReadTimeout("Read timed out")
        )

        api = SessionKeepAliveAPI(httpx.Client())
        try:
            assert api.is_session_alive() is False
        finally:
            api._http.close()


# ---------------------------------------------------------------------------
# Shared httpx.Client tests
# ---------------------------------------------------------------------------

class TestSharedClient:
    @respx.mock
    def test_uses_provided_http_client(self):
        route = respx.get(EXPECTED_URL).mock(
            return_value=httpx.Response(200)
        )

        client = httpx.Client()
        api = SessionKeepAliveAPI(client)
        try:
            api.extend_session()
        finally:
            client.close()

        assert api._http is client
        assert route.called
