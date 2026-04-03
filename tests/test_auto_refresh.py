"""Tests for the SessionAutoRefresh background thread."""

import time
from unittest.mock import MagicMock, patch


from fidelity_trader.auth.auto_refresh import SessionAutoRefresh
from fidelity_trader.auth.session_keepalive import SessionKeepAliveAPI


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_keepalive(succeed: bool = True) -> MagicMock:
    """Return a mock SessionKeepAliveAPI whose extend_session either
    returns True or raises an exception."""
    mock = MagicMock(spec=SessionKeepAliveAPI)
    if succeed:
        mock.extend_session.return_value = True
    else:
        mock.extend_session.side_effect = RuntimeError("connection failed")
    return mock


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------

class TestLifecycle:
    def test_start_creates_running_thread(self):
        ka = _make_keepalive()
        auto = SessionAutoRefresh(ka, interval=60)
        try:
            auto.start()
            assert auto.is_running is True
        finally:
            auto.stop()

    def test_stop_terminates_thread(self):
        ka = _make_keepalive()
        auto = SessionAutoRefresh(ka, interval=60)
        auto.start()
        auto.stop()
        assert auto.is_running is False

    def test_stop_without_start_is_safe(self):
        ka = _make_keepalive()
        auto = SessionAutoRefresh(ka, interval=60)
        auto.stop()  # should not raise

    def test_double_start_is_idempotent(self):
        ka = _make_keepalive()
        auto = SessionAutoRefresh(ka, interval=60)
        try:
            auto.start()
            first_thread = auto._thread
            auto.start()  # second call should be ignored
            assert auto._thread is first_thread
        finally:
            auto.stop()

    def test_multiple_start_stop_cycles(self):
        ka = _make_keepalive()
        auto = SessionAutoRefresh(ka, interval=0.05)
        for _ in range(3):
            auto.start()
            assert auto.is_running is True
            auto.stop()
            assert auto.is_running is False


# ---------------------------------------------------------------------------
# Thread properties
# ---------------------------------------------------------------------------

class TestThreadProperties:
    def test_thread_is_daemon(self):
        ka = _make_keepalive()
        auto = SessionAutoRefresh(ka, interval=60)
        try:
            auto.start()
            assert auto._thread.daemon is True
        finally:
            auto.stop()

    def test_thread_name(self):
        ka = _make_keepalive()
        auto = SessionAutoRefresh(ka, interval=60)
        try:
            auto.start()
            assert auto._thread.name == "fidelity-session-refresh"
        finally:
            auto.stop()

    def test_is_running_false_before_start(self):
        ka = _make_keepalive()
        auto = SessionAutoRefresh(ka, interval=60)
        assert auto.is_running is False

    def test_stop_is_clean_thread_exits_promptly(self):
        ka = _make_keepalive()
        auto = SessionAutoRefresh(ka, interval=60)
        auto.start()
        thread = auto._thread
        auto.stop()
        # Thread should have exited within the join timeout
        assert not thread.is_alive()


# ---------------------------------------------------------------------------
# Refresh counters
# ---------------------------------------------------------------------------

class TestRefreshCounters:
    def test_refresh_count_increments_on_success(self):
        ka = _make_keepalive(succeed=True)
        auto = SessionAutoRefresh(ka, interval=0.05)
        auto.start()
        time.sleep(0.25)
        auto.stop()
        assert auto.refresh_count >= 2

    def test_failure_count_increments_on_error(self):
        ka = _make_keepalive(succeed=False)
        auto = SessionAutoRefresh(ka, interval=0.05)
        auto.start()
        time.sleep(0.25)
        auto.stop()
        assert auto.failure_count >= 2
        assert auto.refresh_count == 0

    def test_last_refresh_is_none_before_start(self):
        ka = _make_keepalive()
        auto = SessionAutoRefresh(ka, interval=60)
        assert auto.last_refresh is None

    def test_last_refresh_updates_on_success(self):
        ka = _make_keepalive(succeed=True)
        auto = SessionAutoRefresh(ka, interval=0.05)
        before = time.time()
        auto.start()
        time.sleep(0.15)
        auto.stop()
        assert auto.last_refresh is not None
        assert auto.last_refresh >= before

    def test_last_refresh_not_updated_on_failure(self):
        ka = _make_keepalive(succeed=False)
        auto = SessionAutoRefresh(ka, interval=0.05)
        auto.start()
        time.sleep(0.15)
        auto.stop()
        assert auto.last_refresh is None

    def test_counters_start_at_zero(self):
        ka = _make_keepalive()
        auto = SessionAutoRefresh(ka, interval=60)
        assert auto.refresh_count == 0
        assert auto.failure_count == 0


# ---------------------------------------------------------------------------
# Custom interval
# ---------------------------------------------------------------------------

class TestInterval:
    def test_custom_interval_is_respected(self):
        """With a very short interval, multiple refreshes should happen fast."""
        ka = _make_keepalive(succeed=True)
        auto = SessionAutoRefresh(ka, interval=0.05)
        auto.start()
        time.sleep(0.3)
        auto.stop()
        # Should have fired several times in 0.3s at 0.05s interval
        assert auto.refresh_count >= 3

    def test_long_interval_fires_once_immediately(self):
        """The first refresh fires immediately, before the interval elapses."""
        ka = _make_keepalive(succeed=True)
        auto = SessionAutoRefresh(ka, interval=600)
        auto.start()
        time.sleep(0.15)
        auto.stop()
        # Should have fired exactly once (immediately on start)
        assert auto.refresh_count == 1


# ---------------------------------------------------------------------------
# Error resilience
# ---------------------------------------------------------------------------

class TestErrorResilience:
    def test_thread_survives_exceptions(self):
        """The refresh thread should keep running after failures."""
        ka = _make_keepalive(succeed=False)
        auto = SessionAutoRefresh(ka, interval=0.05)
        auto.start()
        time.sleep(0.2)
        assert auto.is_running is True
        auto.stop()

    def test_mixed_success_and_failure(self):
        """If keepalive alternates between success and failure, both
        counters should increment."""
        ka = MagicMock(spec=SessionKeepAliveAPI)
        call_count = 0

        def _alternate():
            nonlocal call_count
            call_count += 1
            if call_count % 2 == 0:
                raise RuntimeError("fail")
            return True

        ka.extend_session.side_effect = _alternate
        auto = SessionAutoRefresh(ka, interval=0.05)
        auto.start()
        time.sleep(0.35)
        auto.stop()
        assert auto.refresh_count >= 1
        assert auto.failure_count >= 1


# ---------------------------------------------------------------------------
# FidelityClient integration
# ---------------------------------------------------------------------------

class TestClientIntegration:
    def test_enable_auto_refresh(self):
        from fidelity_trader import FidelityClient

        client = FidelityClient()
        try:
            with patch.object(
                client.session_keepalive, "extend_session", return_value=True
            ):
                client.enable_auto_refresh(interval=0.05)
                assert client._auto_refresh is not None
                assert client._auto_refresh.is_running is True
                time.sleep(0.15)
                assert client._auto_refresh.refresh_count >= 1
        finally:
            client.close()

    def test_disable_auto_refresh(self):
        from fidelity_trader import FidelityClient

        client = FidelityClient()
        try:
            with patch.object(
                client.session_keepalive, "extend_session", return_value=True
            ):
                client.enable_auto_refresh(interval=60)
                client.disable_auto_refresh()
                assert client._auto_refresh is None
        finally:
            client.close()

    def test_close_stops_auto_refresh(self):
        from fidelity_trader import FidelityClient

        client = FidelityClient()
        with patch.object(
            client.session_keepalive, "extend_session", return_value=True
        ):
            client.enable_auto_refresh(interval=60)
            auto = client._auto_refresh
            client.close()
            assert auto.is_running is False

    def test_enable_replaces_existing_auto_refresh(self):
        from fidelity_trader import FidelityClient

        client = FidelityClient()
        try:
            with patch.object(
                client.session_keepalive, "extend_session", return_value=True
            ):
                client.enable_auto_refresh(interval=60)
                first = client._auto_refresh
                client.enable_auto_refresh(interval=30)
                second = client._auto_refresh
                assert first is not second
                assert first.is_running is False
                assert second.is_running is True
        finally:
            client.close()
