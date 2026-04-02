"""Tests for retry transport, create_atp_session retry params, and FidelityClient passthrough."""

import logging
from unittest.mock import MagicMock, patch, call

import httpx
import pytest

from fidelity_trader.retry import RetryTransport
from fidelity_trader._http import create_atp_session
from fidelity_trader.client import FidelityClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_request() -> httpx.Request:
    """Build a minimal httpx.Request for testing."""
    return httpx.Request("GET", "https://example.com/test")


def _mock_transport(*responses_or_errors):
    """Return a mock transport that yields the given responses/errors in order."""
    transport = MagicMock(spec=httpx.BaseTransport)
    side_effects = []
    for item in responses_or_errors:
        if isinstance(item, Exception):
            side_effects.append(item)
        else:
            side_effects.append(item)
    transport.handle_request.side_effect = side_effects
    return transport


def _response(status_code: int, headers: dict | None = None) -> httpx.Response:
    return httpx.Response(status_code, headers=headers or {})


# ---------------------------------------------------------------------------
# No retry when max_retries=0
# ---------------------------------------------------------------------------

class TestNoRetry:
    def test_no_retry_on_success(self):
        inner = _mock_transport(_response(200))
        transport = RetryTransport(transport=inner, max_retries=0)
        resp = transport.handle_request(_make_request())
        assert resp.status_code == 200
        assert inner.handle_request.call_count == 1

    def test_no_retry_on_500_when_disabled(self):
        inner = _mock_transport(_response(500))
        transport = RetryTransport(transport=inner, max_retries=0)
        resp = transport.handle_request(_make_request())
        assert resp.status_code == 500
        assert inner.handle_request.call_count == 1

    @patch("fidelity_trader.retry.time.sleep")
    def test_no_retry_on_connection_error_when_disabled(self, mock_sleep):
        inner = _mock_transport(httpx.ConnectError("refused"))
        transport = RetryTransport(transport=inner, max_retries=0)
        with pytest.raises(httpx.ConnectError):
            transport.handle_request(_make_request())
        assert inner.handle_request.call_count == 1
        mock_sleep.assert_not_called()


# ---------------------------------------------------------------------------
# Retry on server errors (5xx)
# ---------------------------------------------------------------------------

class TestRetryOnServerErrors:
    @patch("fidelity_trader.retry.time.sleep")
    def test_retry_on_500(self, mock_sleep):
        inner = _mock_transport(_response(500), _response(200))
        transport = RetryTransport(transport=inner, max_retries=3)
        resp = transport.handle_request(_make_request())
        assert resp.status_code == 200
        assert inner.handle_request.call_count == 2

    @patch("fidelity_trader.retry.time.sleep")
    def test_retry_on_502(self, mock_sleep):
        inner = _mock_transport(_response(502), _response(200))
        transport = RetryTransport(transport=inner, max_retries=3)
        resp = transport.handle_request(_make_request())
        assert resp.status_code == 200

    @patch("fidelity_trader.retry.time.sleep")
    def test_retry_on_503(self, mock_sleep):
        inner = _mock_transport(_response(503), _response(200))
        transport = RetryTransport(transport=inner, max_retries=3)
        resp = transport.handle_request(_make_request())
        assert resp.status_code == 200

    @patch("fidelity_trader.retry.time.sleep")
    def test_retry_on_504(self, mock_sleep):
        inner = _mock_transport(_response(504), _response(200))
        transport = RetryTransport(transport=inner, max_retries=3)
        resp = transport.handle_request(_make_request())
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Retry on 429 with Retry-After header
# ---------------------------------------------------------------------------

class TestRateLimitRetry:
    @patch("fidelity_trader.retry.time.sleep")
    def test_retry_on_429_respects_retry_after(self, mock_sleep):
        inner = _mock_transport(
            _response(429, headers={"Retry-After": "5"}),
            _response(200),
        )
        transport = RetryTransport(transport=inner, max_retries=3)
        resp = transport.handle_request(_make_request())
        assert resp.status_code == 200
        # Should sleep for 5 seconds (from Retry-After), not backoff
        mock_sleep.assert_called_once_with(5.0)

    @patch("fidelity_trader.retry.time.sleep")
    def test_retry_on_429_without_retry_after_uses_backoff(self, mock_sleep):
        inner = _mock_transport(_response(429), _response(200))
        transport = RetryTransport(
            transport=inner, max_retries=3, retry_delay=1.0, backoff_factor=2.0
        )
        resp = transport.handle_request(_make_request())
        assert resp.status_code == 200
        # First attempt backoff: 1.0 * 2.0^0 = 1.0
        mock_sleep.assert_called_once_with(1.0)


# ---------------------------------------------------------------------------
# Retry on connection errors and timeouts
# ---------------------------------------------------------------------------

class TestRetryOnConnectionErrors:
    @patch("fidelity_trader.retry.time.sleep")
    def test_retry_on_connect_error(self, mock_sleep):
        inner = _mock_transport(httpx.ConnectError("refused"), _response(200))
        transport = RetryTransport(transport=inner, max_retries=3)
        resp = transport.handle_request(_make_request())
        assert resp.status_code == 200
        assert inner.handle_request.call_count == 2

    @patch("fidelity_trader.retry.time.sleep")
    def test_retry_on_read_timeout(self, mock_sleep):
        inner = _mock_transport(httpx.ReadTimeout("timeout"), _response(200))
        transport = RetryTransport(transport=inner, max_retries=3)
        resp = transport.handle_request(_make_request())
        assert resp.status_code == 200
        assert inner.handle_request.call_count == 2

    @patch("fidelity_trader.retry.time.sleep")
    def test_retry_on_write_timeout(self, mock_sleep):
        inner = _mock_transport(httpx.WriteTimeout("timeout"), _response(200))
        transport = RetryTransport(transport=inner, max_retries=3)
        resp = transport.handle_request(_make_request())
        assert resp.status_code == 200

    @patch("fidelity_trader.retry.time.sleep")
    def test_retry_on_connect_timeout(self, mock_sleep):
        inner = _mock_transport(httpx.ConnectTimeout("timeout"), _response(200))
        transport = RetryTransport(transport=inner, max_retries=3)
        resp = transport.handle_request(_make_request())
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Max retries exhausted
# ---------------------------------------------------------------------------

class TestMaxRetriesExhausted:
    @patch("fidelity_trader.retry.time.sleep")
    def test_returns_last_response_after_max_retries(self, mock_sleep):
        inner = _mock_transport(
            _response(503), _response(503), _response(503), _response(503),
        )
        transport = RetryTransport(transport=inner, max_retries=3)
        resp = transport.handle_request(_make_request())
        assert resp.status_code == 503
        # 1 initial + 3 retries = 4 total calls
        assert inner.handle_request.call_count == 4

    @patch("fidelity_trader.retry.time.sleep")
    def test_raises_last_exception_after_max_retries(self, mock_sleep):
        inner = _mock_transport(
            httpx.ConnectError("1"),
            httpx.ConnectError("2"),
            httpx.ConnectError("3"),
            httpx.ConnectError("4"),
        )
        transport = RetryTransport(transport=inner, max_retries=3)
        with pytest.raises(httpx.ConnectError, match="4"):
            transport.handle_request(_make_request())
        assert inner.handle_request.call_count == 4


# ---------------------------------------------------------------------------
# No retry on client errors (4xx except 429)
# ---------------------------------------------------------------------------

class TestNoRetryOnClientErrors:
    @patch("fidelity_trader.retry.time.sleep")
    def test_no_retry_on_400(self, mock_sleep):
        inner = _mock_transport(_response(400))
        transport = RetryTransport(transport=inner, max_retries=3)
        resp = transport.handle_request(_make_request())
        assert resp.status_code == 400
        assert inner.handle_request.call_count == 1
        mock_sleep.assert_not_called()

    @patch("fidelity_trader.retry.time.sleep")
    def test_no_retry_on_401(self, mock_sleep):
        inner = _mock_transport(_response(401))
        transport = RetryTransport(transport=inner, max_retries=3)
        resp = transport.handle_request(_make_request())
        assert resp.status_code == 401
        assert inner.handle_request.call_count == 1
        mock_sleep.assert_not_called()

    @patch("fidelity_trader.retry.time.sleep")
    def test_no_retry_on_403(self, mock_sleep):
        inner = _mock_transport(_response(403))
        transport = RetryTransport(transport=inner, max_retries=3)
        resp = transport.handle_request(_make_request())
        assert resp.status_code == 403
        assert inner.handle_request.call_count == 1
        mock_sleep.assert_not_called()

    @patch("fidelity_trader.retry.time.sleep")
    def test_no_retry_on_404(self, mock_sleep):
        inner = _mock_transport(_response(404))
        transport = RetryTransport(transport=inner, max_retries=3)
        resp = transport.handle_request(_make_request())
        assert resp.status_code == 404
        assert inner.handle_request.call_count == 1
        mock_sleep.assert_not_called()


# ---------------------------------------------------------------------------
# Exponential backoff timing
# ---------------------------------------------------------------------------

class TestExponentialBackoff:
    @patch("fidelity_trader.retry.time.sleep")
    def test_backoff_delays_increase_exponentially(self, mock_sleep):
        inner = _mock_transport(
            _response(500), _response(500), _response(500), _response(200),
        )
        transport = RetryTransport(
            transport=inner, max_retries=3, retry_delay=1.0, backoff_factor=2.0
        )
        resp = transport.handle_request(_make_request())
        assert resp.status_code == 200
        # Delays: 1.0*2^0=1.0, 1.0*2^1=2.0, 1.0*2^2=4.0
        assert mock_sleep.call_args_list == [call(1.0), call(2.0), call(4.0)]

    @patch("fidelity_trader.retry.time.sleep")
    def test_custom_backoff_factor(self, mock_sleep):
        inner = _mock_transport(_response(500), _response(500), _response(200))
        transport = RetryTransport(
            transport=inner, max_retries=3, retry_delay=0.5, backoff_factor=3.0
        )
        resp = transport.handle_request(_make_request())
        assert resp.status_code == 200
        # Delays: 0.5*3^0=0.5, 0.5*3^1=1.5
        assert mock_sleep.call_args_list == [call(0.5), call(1.5)]

    @patch("fidelity_trader.retry.time.sleep")
    def test_backoff_on_connection_error(self, mock_sleep):
        inner = _mock_transport(
            httpx.ConnectError("fail"),
            httpx.ConnectError("fail"),
            _response(200),
        )
        transport = RetryTransport(
            transport=inner, max_retries=3, retry_delay=2.0, backoff_factor=2.0
        )
        resp = transport.handle_request(_make_request())
        assert resp.status_code == 200
        # Delays: 2.0*2^0=2.0, 2.0*2^1=4.0
        assert mock_sleep.call_args_list == [call(2.0), call(4.0)]


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

class TestLogging:
    @patch("fidelity_trader.retry.time.sleep")
    def test_logs_retry_on_status_code(self, mock_sleep, caplog):
        inner = _mock_transport(_response(503), _response(200))
        transport = RetryTransport(transport=inner, max_retries=3)
        with caplog.at_level(logging.WARNING, logger="fidelity_trader.retry"):
            transport.handle_request(_make_request())
        assert len(caplog.records) == 1
        assert "Retry 1/3" in caplog.records[0].message
        assert "HTTP 503" in caplog.records[0].message

    @patch("fidelity_trader.retry.time.sleep")
    def test_logs_retry_on_connection_error(self, mock_sleep, caplog):
        inner = _mock_transport(httpx.ConnectError("refused"), _response(200))
        transport = RetryTransport(transport=inner, max_retries=3)
        with caplog.at_level(logging.WARNING, logger="fidelity_trader.retry"):
            transport.handle_request(_make_request())
        assert len(caplog.records) == 1
        assert "Retry 1/3" in caplog.records[0].message
        assert "ConnectError" in caplog.records[0].message

    @patch("fidelity_trader.retry.time.sleep")
    def test_multiple_retries_produce_multiple_log_entries(self, mock_sleep, caplog):
        inner = _mock_transport(
            _response(500), _response(502), _response(200)
        )
        transport = RetryTransport(transport=inner, max_retries=3)
        with caplog.at_level(logging.WARNING, logger="fidelity_trader.retry"):
            transport.handle_request(_make_request())
        assert len(caplog.records) == 2
        assert "Retry 1/3" in caplog.records[0].message
        assert "Retry 2/3" in caplog.records[1].message


# ---------------------------------------------------------------------------
# create_atp_session with retry params
# ---------------------------------------------------------------------------

class TestCreateAtpSessionRetry:
    def test_default_no_retry_transport(self):
        client = create_atp_session()
        try:
            # Default transport should NOT be a RetryTransport
            assert not isinstance(client._transport, RetryTransport)
        finally:
            client.close()

    def test_with_retries_wraps_transport(self):
        client = create_atp_session(max_retries=3)
        try:
            assert isinstance(client._transport, RetryTransport)
            assert client._transport._max_retries == 3
        finally:
            client.close()

    def test_retry_params_passed_through(self):
        client = create_atp_session(
            max_retries=5, retry_delay=0.5, backoff_factor=3.0
        )
        try:
            t = client._transport
            assert isinstance(t, RetryTransport)
            assert t._max_retries == 5
            assert t._retry_delay == 0.5
            assert t._backoff_factor == 3.0
        finally:
            client.close()


# ---------------------------------------------------------------------------
# FidelityClient passes retry config through
# ---------------------------------------------------------------------------

class TestFidelityClientRetryConfig:
    def test_default_no_retry(self):
        client = FidelityClient()
        try:
            assert not isinstance(client._http._transport, RetryTransport)
        finally:
            client.close()

    def test_retry_config_passthrough(self):
        client = FidelityClient(max_retries=2, retry_delay=0.5)
        try:
            t = client._http._transport
            assert isinstance(t, RetryTransport)
            assert t._max_retries == 2
            assert t._retry_delay == 0.5
        finally:
            client.close()


# ---------------------------------------------------------------------------
# Transport close
# ---------------------------------------------------------------------------

class TestTransportClose:
    def test_close_delegates_to_inner_transport(self):
        inner = MagicMock(spec=httpx.BaseTransport)
        transport = RetryTransport(transport=inner, max_retries=3)
        transport.close()
        inner.close.assert_called_once()


# ---------------------------------------------------------------------------
# Success on first try (no retry needed)
# ---------------------------------------------------------------------------

class TestSuccessNoRetry:
    @patch("fidelity_trader.retry.time.sleep")
    def test_200_response_no_sleep(self, mock_sleep):
        inner = _mock_transport(_response(200))
        transport = RetryTransport(transport=inner, max_retries=3)
        resp = transport.handle_request(_make_request())
        assert resp.status_code == 200
        assert inner.handle_request.call_count == 1
        mock_sleep.assert_not_called()
