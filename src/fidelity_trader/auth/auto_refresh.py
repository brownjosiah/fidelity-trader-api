"""Automatic session refresh — background thread that periodically extends
the Fidelity session to prevent the ~30-minute inactivity timeout."""

import logging
import threading
import time
from typing import Optional

from fidelity_trader.auth.session_keepalive import SessionKeepAliveAPI

logger = logging.getLogger(__name__)


class SessionAutoRefresh:
    """Background thread that periodically extends the Fidelity session.

    Usage::

        auto = SessionAutoRefresh(keepalive_api, interval=300)
        auto.start()
        # ... session stays alive ...
        auto.stop()
    """

    def __init__(self, keepalive: SessionKeepAliveAPI, interval: int = 300) -> None:
        """
        Parameters
        ----------
        keepalive:
            A :class:`SessionKeepAliveAPI` instance used to send the
            keep-alive request.
        interval:
            Seconds between refresh attempts (default 5 minutes).
        """
        self._keepalive = keepalive
        self._interval = interval

        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        self._last_refresh: Optional[float] = None
        self._refresh_count: int = 0
        self._failure_count: int = 0

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the background refresh thread (daemon=True)."""
        if self._thread is not None and self._thread.is_alive():
            logger.debug("Auto-refresh already running — ignoring start()")
            return

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run, name="fidelity-session-refresh", daemon=True
        )
        self._thread.start()
        logger.info(
            "Session auto-refresh started (interval=%ds)", self._interval
        )

    def stop(self) -> None:
        """Stop the background refresh thread."""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None
        logger.info("Session auto-refresh stopped")

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def is_running(self) -> bool:
        """Whether the background thread is currently alive."""
        return self._thread is not None and self._thread.is_alive()

    @property
    def last_refresh(self) -> Optional[float]:
        """Unix timestamp of the last successful refresh, or ``None``."""
        with self._lock:
            return self._last_refresh

    @property
    def refresh_count(self) -> int:
        """Total number of successful refresh calls."""
        with self._lock:
            return self._refresh_count

    @property
    def failure_count(self) -> int:
        """Total number of failed refresh attempts."""
        with self._lock:
            return self._failure_count

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _run(self) -> None:
        """Main loop executed in the background thread."""
        while not self._stop_event.is_set():
            try:
                self._keepalive.extend_session()
                now = time.time()
                with self._lock:
                    self._last_refresh = now
                    self._refresh_count += 1
                logger.debug("Session refreshed successfully")
            except Exception:
                with self._lock:
                    self._failure_count += 1
                logger.warning("Session refresh failed", exc_info=True)

            # Wait for the interval or until stop() is called
            self._stop_event.wait(timeout=self._interval)
