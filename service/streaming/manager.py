"""MDDS streaming connection manager with fan-out to consumer queues.

Maintains a single MDDS WebSocket connection and distributes parsed
quotes to all registered consumers via per-consumer asyncio.Queue
instances.  Symbol subscriptions are refcounted so the upstream MDDS
connection only subscribes/unsubscribes when the first consumer
requests a symbol or the last consumer drops it.

Integration with app.py lifespan (not wired yet):
    # In lifespan():
    #     mdds_manager = MDDSManager()
    #     app.state.mdds_manager = mdds_manager
    #     # After login:
    #     await mdds_manager.start(session_manager.get_client())
    #     yield
    #     await mdds_manager.stop()
"""

from __future__ import annotations

import asyncio
import logging
import uuid

from fidelity_trader.streaming.mdds import MDDSClient

logger = logging.getLogger(__name__)


class MDDSManager:
    """Manages a single MDDS WebSocket connection and fans out data.

    Consumers register to receive a personal ``asyncio.Queue``.  When
    data arrives from Fidelity the manager pushes a JSON-serialisable
    dict to every registered queue.
    """

    def __init__(self) -> None:
        self._mdds: MDDSClient | None = None
        self._ws: object | None = None  # actual websocket connection
        self._subscriptions: dict[str, int] = {}  # symbol -> refcount
        self._consumers: dict[str, asyncio.Queue] = {}  # consumer_id -> queue
        self._consumer_symbols: dict[str, set[str]] = {}  # consumer_id -> subscribed symbols
        self._running = False
        self._task: asyncio.Task | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self, client) -> None:
        """Start the MDDS connection using cookies from an authenticated FidelityClient.

        Parameters
        ----------
        client:
            An authenticated ``FidelityClient`` whose ``_http`` transport
            carries the session cookies needed for WebSocket auth.
        """
        if self._running:
            logger.warning("MDDSManager already running")
            return

        self._mdds = MDDSClient()

        # Extract cookies from the authenticated httpx client for WS auth.
        cookies = {}
        if hasattr(client, "_http") and hasattr(client._http, "cookies"):
            for name, value in client._http.cookies.items():
                cookies[name] = value

        self._running = True
        self._task = asyncio.create_task(self._read_loop())
        logger.info("MDDSManager started")

    async def stop(self) -> None:
        """Shutdown the manager gracefully."""
        self._running = False
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        self._mdds = None
        self._ws = None
        self._subscriptions.clear()
        self._consumers.clear()
        self._consumer_symbols.clear()
        logger.info("MDDSManager stopped")

    # ------------------------------------------------------------------
    # Consumer registration
    # ------------------------------------------------------------------

    def register_consumer(self) -> tuple[str, asyncio.Queue]:
        """Create a new consumer and return ``(consumer_id, queue)``."""
        consumer_id = str(uuid.uuid4())
        queue: asyncio.Queue = asyncio.Queue(maxsize=1000)
        self._consumers[consumer_id] = queue
        self._consumer_symbols[consumer_id] = set()
        return consumer_id, queue

    def unregister_consumer(self, consumer_id: str) -> None:
        """Remove a consumer.  Does NOT auto-unsubscribe its symbols.

        Callers should ``unsubscribe()`` before unregistering.
        """
        self._consumers.pop(consumer_id, None)
        self._consumer_symbols.pop(consumer_id, None)

    # ------------------------------------------------------------------
    # Subscription management (refcounted)
    # ------------------------------------------------------------------

    async def subscribe(self, symbols: list[str], consumer_id: str) -> None:
        """Subscribe *consumer_id* to *symbols*.

        Only sends an MDDS subscribe command for symbols that have no
        existing subscribers (refcount goes from 0 to 1).
        """
        new_symbols: list[str] = []
        for sym in symbols:
            sym = sym.upper()
            prev = self._subscriptions.get(sym, 0)
            self._subscriptions[sym] = prev + 1
            if consumer_id in self._consumer_symbols:
                self._consumer_symbols[consumer_id].add(sym)
            if prev == 0:
                new_symbols.append(sym)

        if new_symbols and self._mdds is not None and self._ws is not None:
            self._mdds.build_subscribe_message(new_symbols)
            logger.info("MDDS subscribe: %s", new_symbols)
            # In production this would send via the websocket:
            # await self._ws.send(msg)

    async def unsubscribe(self, symbols: list[str], consumer_id: str) -> None:
        """Unsubscribe *consumer_id* from *symbols*.

        Only sends an MDDS unsubscribe command when the refcount
        reaches zero (last consumer drops the symbol).
        """
        dead_symbols: list[str] = []
        for sym in symbols:
            sym = sym.upper()
            if sym in self._subscriptions:
                self._subscriptions[sym] -= 1
                if self._subscriptions[sym] <= 0:
                    del self._subscriptions[sym]
                    dead_symbols.append(sym)
            if consumer_id in self._consumer_symbols:
                self._consumer_symbols[consumer_id].discard(sym)

        if dead_symbols and self._mdds is not None and self._ws is not None:
            self._mdds.build_unsubscribe_message(dead_symbols)
            logger.info("MDDS unsubscribe: %s", dead_symbols)
            # await self._ws.send(msg)

    # ------------------------------------------------------------------
    # Read loop (background task)
    # ------------------------------------------------------------------

    async def _read_loop(self) -> None:
        """Read MDDS messages and fan out to consumer queues."""
        while self._running:
            try:
                # In production this reads from the real websocket.
                # For now the loop just sleeps; start() would need to
                # establish the actual connection first.
                await asyncio.sleep(1)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning("MDDS read error: %s", e)
                if self._running:
                    await asyncio.sleep(5)

    def _fan_out(self, data: dict) -> None:
        """Push *data* to every registered consumer queue.

        Drops the message for any consumer whose queue is full.
        """
        for queue in self._consumers.values():
            try:
                queue.put_nowait(data)
            except asyncio.QueueFull:
                pass  # slow consumer — drop

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def get_subscriptions(self) -> dict[str, int]:
        """Return a snapshot of ``{symbol: refcount}``."""
        return dict(self._subscriptions)

    @property
    def is_connected(self) -> bool:
        """True when the background read loop is alive."""
        return self._running and self._task is not None and not self._task.done()
