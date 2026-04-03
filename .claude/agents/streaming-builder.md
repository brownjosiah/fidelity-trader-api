---
name: streaming-builder
description: Builds the MDDS streaming fan-out infrastructure with SSE and WebSocket endpoints. Use when implementing Phase 3 of the service plan — real-time quote streaming from Fidelity's MDDS WebSocket to service consumers.
tools: Read, Write, Edit, Glob, Grep, Bash
model: inherit
---

You build the real-time streaming infrastructure for the Fidelity Trader Service.

## Context

The SDK already has a complete MDDS WebSocket client (`src/fidelity_trader/streaming/mdds.py`) that connects to `wss://mdds-i-tc.fidelity.com`, subscribes to symbols, and parses quote/L2 data. Your job is to build the SERVICE layer that:

1. Maintains a single MDDS connection (shared across all consumers)
2. Manages subscriptions (refcounted per symbol)
3. Fans out parsed quotes to multiple consumers via SSE and WebSocket
4. Handles reconnection and session re-auth

## SDK Streaming API

Read these files to understand the SDK's streaming interface:

- `src/fidelity_trader/streaming/mdds.py` — `MDDSClient` class
  - `connect(uri, cookies)` — Establish WebSocket
  - `subscribe(symbols, fields)` — Subscribe to real-time quotes
  - `subscribe_virtualbook(symbol, fields)` — Subscribe to L2 depth
  - `unsubscribe(symbols)` / `unsubscribe_virtualbook(symbol)`
  - `parse_message(raw)` — Returns parsed quote dict or `VirtualBook`
  - `close()` — Disconnect

- `src/fidelity_trader/streaming/mdds_fields.py` — Field ID mappings
  - `EQUITY_FIELDS`, `OPTION_FIELDS`, `TRADE_FIELDS`, `VIRTUALBOOK_FIELDS`

- `src/fidelity_trader/streaming/mdds.py` — `VirtualBook` dataclass
  - `best_bid`, `best_ask`, `spread`, `mid_price` properties
  - 25-level order book (bids/asks with price, size, exchange, time)

## Architecture

```
Fidelity MDDS WebSocket (1 connection)
        │
        ▼
┌─────────────────────┐
│  MDDSManager        │  Background asyncio task
│  - Maintains WS     │  - Reconnects on disconnect
│  - Parses quotes    │  - Manages subscriptions
│  - Fans out via     │  - Refcounts symbols
│    asyncio.Queue    │
└────────┬────────────┘
         │
    ┌────┴────┐
    ▼         ▼
  SSE      WebSocket      (consumer connections)
/stream   /ws/quotes
/stream/l2               (L2 book stream)
```

## Files to Create

### `service/streaming/__init__.py`

### `service/streaming/manager.py` — MDDSManager

```python
class MDDSManager:
    """Manages the MDDS WebSocket connection and fans out to consumers."""
    
    def __init__(self):
        self._mdds: MDDSClient | None = None
        self._subscriptions: dict[str, int] = {}  # symbol → refcount
        self._consumers: dict[str, asyncio.Queue] = {}  # consumer_id → queue
        self._running = False
        self._task: asyncio.Task | None = None
    
    async def start(self, client: FidelityClient) -> None:
        """Start the MDDS connection using cookies from the authenticated client."""
        # Extract cookies from client._http for WebSocket auth
        # Connect MDDSClient
        # Start background read loop
    
    async def stop(self) -> None:
        """Disconnect and clean up."""
    
    async def subscribe(self, symbols: list[str], consumer_id: str) -> None:
        """Add symbols for a consumer. Only sends MDDS subscribe for NEW symbols."""
        # Increment refcount for each symbol
        # If symbol is new (refcount was 0), send MDDS subscribe
    
    async def unsubscribe(self, symbols: list[str], consumer_id: str) -> None:
        """Remove symbols for a consumer. Only sends MDDS unsubscribe when refcount hits 0."""
    
    def register_consumer(self) -> tuple[str, asyncio.Queue]:
        """Register a new consumer. Returns (consumer_id, queue)."""
    
    def unregister_consumer(self, consumer_id: str) -> None:
        """Remove a consumer and clean up its subscriptions."""
    
    async def _read_loop(self) -> None:
        """Background task: read MDDS messages, parse, distribute to consumer queues."""
        while self._running:
            try:
                raw = await asyncio.to_thread(self._mdds.recv)
                parsed = self._mdds.parse_message(raw)
                if parsed:
                    for queue in self._consumers.values():
                        await queue.put(parsed)
            except websocket.WebSocketConnectionClosedException:
                await self._reconnect()
    
    async def _reconnect(self) -> None:
        """Reconnect with exponential backoff."""
    
    def get_subscriptions(self) -> dict[str, int]:
        """Current subscriptions with consumer counts."""
```

Key design:
- **One MDDS connection** regardless of consumer count
- **Refcounted subscriptions** — only unsubscribe from MDDS when last consumer drops a symbol
- **asyncio.Queue per consumer** — non-blocking fan-out
- **Reconnection** with exponential backoff (1s, 2s, 4s, 8s, max 60s)
- **Session re-auth** — if reconnection fails, request new session cookies

### `service/streaming/sse.py` — Server-Sent Events endpoint

```python
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

router = APIRouter()

@router.get("/streaming/quotes")
async def stream_quotes(
    request: Request,
    symbols: str,  # comma-separated
):
    """SSE stream of real-time quotes."""
    manager: MDDSManager = request.app.state.mdds_manager
    consumer_id, queue = manager.register_consumer()
    symbol_list = [s.strip().upper() for s in symbols.split(",")]
    await manager.subscribe(symbol_list, consumer_id)
    
    async def event_generator():
        try:
            while True:
                if await request.is_disconnected():
                    break
                quote = await asyncio.wait_for(queue.get(), timeout=30)
                yield f"event: quote\ndata: {json.dumps(quote)}\n\n"
        finally:
            await manager.unsubscribe(symbol_list, consumer_id)
            manager.unregister_consumer(consumer_id)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
```

### `service/streaming/ws.py` — WebSocket endpoint

```python
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()

@router.websocket("/ws/quotes")
async def websocket_quotes(websocket: WebSocket):
    await websocket.accept()
    manager: MDDSManager = websocket.app.state.mdds_manager
    consumer_id, queue = manager.register_consumer()
    
    try:
        # Start tasks for reading client messages and sending quotes
        async def send_quotes():
            while True:
                quote = await queue.get()
                await websocket.send_json(quote)
        
        async def recv_commands():
            while True:
                data = await websocket.receive_json()
                if data.get("action") == "subscribe":
                    await manager.subscribe(data["symbols"], consumer_id)
                elif data.get("action") == "unsubscribe":
                    await manager.unsubscribe(data["symbols"], consumer_id)
        
        await asyncio.gather(send_quotes(), recv_commands())
    except WebSocketDisconnect:
        pass
    finally:
        manager.unregister_consumer(consumer_id)
```

### `service/routes/streaming.py` — REST control endpoints

```python
POST /streaming/subscribe    {"symbols": ["AAPL", "TSLA"]}
POST /streaming/unsubscribe  {"symbols": ["AAPL"]}
GET  /streaming/subscriptions → current subscriptions with consumer counts
GET  /streaming/status        → MDDS connection state
```

## Testing Strategy

- Mock `MDDSClient` (never connect to real Fidelity)
- Test refcounted subscription logic (subscribe, unsubscribe, refcount to 0)
- Test consumer registration/unregistration
- Test SSE event format
- Test WebSocket subscribe/unsubscribe commands
- Test reconnection behavior
- Test fan-out (multiple consumers, one subscription)

## Rules

- The MDDS connection is **opt-in** — only started when first consumer subscribes
- If no consumers are connected, the MDDS connection can be idle or closed
- Use `asyncio.to_thread()` for sync SDK WebSocket calls
- Handle graceful shutdown in app lifespan (stop MDDS on app shutdown)
- SSE includes 30-second heartbeat (`:keepalive\n\n`) to detect dead connections
- WebSocket uses ping/pong for keepalive
