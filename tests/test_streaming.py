"""Tests for the streaming news authorization API model and StreamingNewsAPI client."""
import pytest
import httpx
import respx

from fidelity_trader._http import STREAMING_NEWS_URL
from fidelity_trader.models.streaming import StreamingAuthResponse
from fidelity_trader.streaming.news import StreamingNewsAPI

_AUTHORIZE_URL = f"{STREAMING_NEWS_URL}/ftgw/snaz/Authorize"

_SAMPLE_RESPONSE = {
    "StreamingHost": "fid-str.newsedge.net",
    "StreamingPort": "443",
    "PollingHost": "fid-polling.newsedge.net",
    "PollingPort": "443",
    "AccessToken": (
        "SUQ6IEY1ODM1MUNBLTEwQTUtNDk2RC1BOEE2LTkxRUYwODU5OEE5QQpDYWxsZXI6IDE4LjIyNC4xMjQu"
        "MTUwCklzc3VlZERhdGU6IDIwMjYwMzMwMjMxMzAyCkZVc2VySUQ6IDYyOTg4MWNlLTBhODgtMzBkYi0y"
        "MDAxLWEwZjIwMDVhYWEzMwpGTWVtYmVySUQ6IGVlNjI5ODgxY2UwYTg4MzBkYjIwMDFhMGYyMDA1YmFh"
        "MzMKRlRpZXJOYW1lOiBBVFBUaWVyMwpGU2Vzc2lvbklEOiA2OWNhY2U4ODQ3NWE4OWY3OTg5MzNlNjRi"
        "NDA2YWEzMzAwMDAKU2lnbmF0dXJlOiB1NkFzNDJZL3kyL294TnlDeTl3dXdrSHRtZkIrMXdUQi9yZlFK"
        "MjZOd2hieFFGdEhNSm5DcDhFbVZJUm82UHIxbUY4WjcxZUszUjFNS0ZxVitTcjVJendVSUtFY0g5QW8y"
        "T052N3NOL0E0OGJJam5Ud2swTDJyVHczRmM1VkxmMW8vaCtrZjZtYmVvMDA5Y0gvTTJyZWhkUEJwcmQw"
        "eWZ5NzA3RitTVVRGMnE4aDB1MzlxUFp1ZDVPOVllOU1lQlE3VkdIRVFCTlZualZzNlE2b0ovRHN5YTRI"
        "Sm9GNnNuSUxPTEhpbU02alJGYnlEVEtnQTJNSWdjMW1leCtRRFZOMWNCRk1tNWpyZStsVUJ5OCtDUEVk"
        "NEp4TDNiZmRCUjJ4cGNtOG5iUXdKeGwyY3RScytDb3Y1aTNBaGhMT2FWaFRRdzM3NlQ4NTgzd3VNN252"
        "RU9HcHc9PQ=="
    ),
}


# ---------------------------------------------------------------------------
# StreamingAuthResponse model tests
# ---------------------------------------------------------------------------

class TestStreamingAuthResponse:
    def test_parses_all_fields(self):
        resp = StreamingAuthResponse.model_validate(_SAMPLE_RESPONSE)
        assert resp.streaming_host == "fid-str.newsedge.net"
        assert resp.streaming_port == "443"
        assert resp.polling_host == "fid-polling.newsedge.net"
        assert resp.polling_port == "443"
        assert resp.access_token.startswith("SUQ6")

    def test_pascal_case_aliases(self):
        resp = StreamingAuthResponse.model_validate(_SAMPLE_RESPONSE)
        assert resp.streaming_host == _SAMPLE_RESPONSE["StreamingHost"]
        assert resp.streaming_port == _SAMPLE_RESPONSE["StreamingPort"]
        assert resp.polling_host == _SAMPLE_RESPONSE["PollingHost"]
        assert resp.polling_port == _SAMPLE_RESPONSE["PollingPort"]
        assert resp.access_token == _SAMPLE_RESPONSE["AccessToken"]

    def test_python_field_names_accessible(self):
        resp = StreamingAuthResponse.model_validate(_SAMPLE_RESPONSE)
        # Verify pythonic names work (not only aliases)
        assert hasattr(resp, "streaming_host")
        assert hasattr(resp, "streaming_port")
        assert hasattr(resp, "polling_host")
        assert hasattr(resp, "polling_port")
        assert hasattr(resp, "access_token")

    def test_different_port_values(self):
        data = {**_SAMPLE_RESPONSE, "StreamingPort": "8443", "PollingPort": "80"}
        resp = StreamingAuthResponse.model_validate(data)
        assert resp.streaming_port == "8443"
        assert resp.polling_port == "80"


# ---------------------------------------------------------------------------
# StreamingNewsAPI — HTTP layer (mocked)
# ---------------------------------------------------------------------------

class TestStreamingNewsAPIAuthorize:
    @respx.mock
    def test_authorize_makes_post_request(self):
        route = respx.post(_AUTHORIZE_URL).mock(
            return_value=httpx.Response(200, json=_SAMPLE_RESPONSE)
        )
        client = httpx.Client()
        api = StreamingNewsAPI(client)
        result = api.authorize()

        assert route.called
        assert isinstance(result, StreamingAuthResponse)

    @respx.mock
    def test_authorize_sends_empty_body(self):
        route = respx.post(_AUTHORIZE_URL).mock(
            return_value=httpx.Response(200, json=_SAMPLE_RESPONSE)
        )
        client = httpx.Client()
        api = StreamingNewsAPI(client)
        api.authorize()

        request = route.calls[0].request
        assert request.content == b""

    @respx.mock
    def test_authorize_returns_correct_fields(self):
        respx.post(_AUTHORIZE_URL).mock(
            return_value=httpx.Response(200, json=_SAMPLE_RESPONSE)
        )
        client = httpx.Client()
        api = StreamingNewsAPI(client)
        result = api.authorize()

        assert result.streaming_host == "fid-str.newsedge.net"
        assert result.streaming_port == "443"
        assert result.polling_host == "fid-polling.newsedge.net"
        assert result.polling_port == "443"
        assert result.access_token == _SAMPLE_RESPONSE["AccessToken"]

    @respx.mock
    def test_authorize_raises_on_http_error(self):
        respx.post(_AUTHORIZE_URL).mock(return_value=httpx.Response(401))
        client = httpx.Client()
        api = StreamingNewsAPI(client)
        with pytest.raises(httpx.HTTPStatusError):
            api.authorize()

    @respx.mock
    def test_authorize_raises_on_forbidden(self):
        respx.post(_AUTHORIZE_URL).mock(return_value=httpx.Response(403))
        client = httpx.Client()
        api = StreamingNewsAPI(client)
        with pytest.raises(httpx.HTTPStatusError):
            api.authorize()

    @respx.mock
    def test_authorize_hits_correct_url(self):
        route = respx.post(_AUTHORIZE_URL).mock(
            return_value=httpx.Response(200, json=_SAMPLE_RESPONSE)
        )
        client = httpx.Client()
        api = StreamingNewsAPI(client)
        api.authorize()

        request = route.calls[0].request
        assert str(request.url) == _AUTHORIZE_URL
