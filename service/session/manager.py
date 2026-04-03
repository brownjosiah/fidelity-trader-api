"""FidelityClient lifecycle management."""

from __future__ import annotations

import asyncio
import enum
import logging

from fidelity_trader import FidelityClient

logger = logging.getLogger(__name__)


class SessionState(str, enum.Enum):
    DISCONNECTED = "disconnected"
    AUTHENTICATED = "authenticated"
    EXPIRED = "expired"
    TOTP_PENDING = "totp_pending"


class SessionManager:
    """Manages a single FidelityClient instance and its lifecycle."""

    def __init__(self, settings) -> None:
        self._client: FidelityClient | None = None
        self._state = SessionState.DISCONNECTED
        self._settings = settings

    async def login(self, username: str, password: str, totp_secret: str | None = None) -> dict:
        """Authenticate with Fidelity. Runs the sync SDK login in a thread."""
        self._client = FidelityClient(live_trading=self._settings.live_trading)
        result = await asyncio.to_thread(self._client.login, username, password, totp_secret)
        self._state = SessionState.AUTHENTICATED
        logger.info("Session authenticated")
        return result

    async def logout(self) -> None:
        """Logout and clean up the client."""
        if self._client:
            try:
                await asyncio.to_thread(self._client.logout)
            except Exception:
                logger.warning("Error during logout", exc_info=True)
            self._client.close()
            self._client = None
        self._state = SessionState.DISCONNECTED
        logger.info("Session disconnected")

    def get_client(self) -> FidelityClient | None:
        """Return the active client, or None if not authenticated."""
        if self._client is None or self._state != SessionState.AUTHENTICATED:
            return None
        return self._client

    async def extend_session(self) -> bool:
        """Extend the Fidelity session via keep-alive endpoint."""
        if self._client is None:
            return False
        try:
            result = await asyncio.to_thread(self._client.session_keepalive.extend_session)
            return result
        except Exception:
            logger.warning("Session extend failed — marking as expired", exc_info=True)
            self._state = SessionState.EXPIRED
            return False

    @property
    def state(self) -> SessionState:
        return self._state

    @state.setter
    def state(self, value: SessionState) -> None:
        self._state = value

    @property
    def is_authenticated(self) -> bool:
        return self._state == SessionState.AUTHENTICATED
