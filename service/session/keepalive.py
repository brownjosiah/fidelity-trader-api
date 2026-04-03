"""Background session keep-alive task."""

from __future__ import annotations

import asyncio
import logging

from service.session.manager import SessionManager

logger = logging.getLogger(__name__)


class KeepAliveTask:
    """Periodically extends the Fidelity session to prevent expiry."""

    def __init__(self, session_manager: SessionManager, interval: int = 300) -> None:
        self._manager = session_manager
        self._interval = interval
        self._task: asyncio.Task | None = None

    def start(self) -> None:
        """Start the keep-alive background loop."""
        if self._task is not None and not self._task.done():
            return
        self._task = asyncio.create_task(self._loop())
        logger.info("Keep-alive task started (interval=%ds)", self._interval)

    async def stop(self) -> None:
        """Cancel the background loop."""
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
            logger.info("Keep-alive task stopped")

    async def _loop(self) -> None:
        """Run keep-alive on a fixed interval."""
        while True:
            await asyncio.sleep(self._interval)
            if self._manager.is_authenticated:
                ok = await self._manager.extend_session()
                if ok:
                    logger.debug("Session extended successfully")
                else:
                    logger.warning("Session extend failed")
