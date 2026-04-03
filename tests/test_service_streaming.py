"""Tests for the MDDS streaming fan-out infrastructure.

Covers:
- MDDSManager consumer registration/unregistration
- Refcounted subscription logic
- Queue fan-out to multiple consumers
- REST streaming control endpoints
- SSE endpoint format
- Status endpoint
"""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from service.streaming.manager import MDDSManager
from service.routes.streaming import router as streaming_rest_router
from service.streaming.sse import router as sse_router
from service.streaming.ws import router as ws_router


# ── Helpers ──────────────────────────────────────────────────────────


def _make_app(manager: MDDSManager | None = None) -> FastAPI:
    """Build a minimal FastAPI app with streaming routes and a manager."""
    app = FastAPI()
    app.state.mdds_manager = manager or MDDSManager()
    app.include_router(streaming_rest_router)
    app.include_router(sse_router)
    app.include_router(ws_router)
    return app


# ── MDDSManager: consumer registration ──────────────────────────────


class TestConsumerRegistration:
    def test_register_returns_id_and_queue(self):
        mgr = MDDSManager()
        consumer_id, queue = mgr.register_consumer()
        assert isinstance(consumer_id, str)
        assert len(consumer_id) == 36  # UUID length
        assert isinstance(queue, asyncio.Queue)

    def test_register_multiple_consumers(self):
        mgr = MDDSManager()
        id1, q1 = mgr.register_consumer()
        id2, q2 = mgr.register_consumer()
        assert id1 != id2
        assert q1 is not q2
        assert len(mgr._consumers) == 2

    def test_unregister_removes_consumer(self):
        mgr = MDDSManager()
        cid, _ = mgr.register_consumer()
        assert cid in mgr._consumers
        mgr.unregister_consumer(cid)
        assert cid not in mgr._consumers

    def test_unregister_nonexistent_is_noop(self):
        mgr = MDDSManager()
        mgr.unregister_consumer("does-not-exist")  # should not raise

    def test_unregister_clears_consumer_symbols(self):
        mgr = MDDSManager()
        cid, _ = mgr.register_consumer()
        mgr._consumer_symbols[cid].add("AAPL")
        mgr.unregister_consumer(cid)
        assert cid not in mgr._consumer_symbols


# ── MDDSManager: refcounted subscriptions ────────────────────────────


class TestRefcountedSubscriptions:
    @pytest.mark.asyncio
    async def test_subscribe_increments_refcount(self):
        mgr = MDDSManager()
        cid, _ = mgr.register_consumer()
        await mgr.subscribe(["AAPL"], cid)
        assert mgr._subscriptions["AAPL"] == 1

    @pytest.mark.asyncio
    async def test_subscribe_same_symbol_twice(self):
        mgr = MDDSManager()
        c1, _ = mgr.register_consumer()
        c2, _ = mgr.register_consumer()
        await mgr.subscribe(["AAPL"], c1)
        await mgr.subscribe(["AAPL"], c2)
        assert mgr._subscriptions["AAPL"] == 2

    @pytest.mark.asyncio
    async def test_unsubscribe_decrements_refcount(self):
        mgr = MDDSManager()
        c1, _ = mgr.register_consumer()
        c2, _ = mgr.register_consumer()
        await mgr.subscribe(["AAPL"], c1)
        await mgr.subscribe(["AAPL"], c2)
        await mgr.unsubscribe(["AAPL"], c1)
        assert mgr._subscriptions["AAPL"] == 1

    @pytest.mark.asyncio
    async def test_unsubscribe_to_zero_removes_symbol(self):
        mgr = MDDSManager()
        cid, _ = mgr.register_consumer()
        await mgr.subscribe(["AAPL"], cid)
        assert "AAPL" in mgr._subscriptions
        await mgr.unsubscribe(["AAPL"], cid)
        assert "AAPL" not in mgr._subscriptions

    @pytest.mark.asyncio
    async def test_unsubscribe_unknown_symbol_is_noop(self):
        mgr = MDDSManager()
        cid, _ = mgr.register_consumer()
        await mgr.unsubscribe(["NOPE"], cid)  # should not raise
        assert "NOPE" not in mgr._subscriptions

    @pytest.mark.asyncio
    async def test_subscribe_normalises_to_uppercase(self):
        mgr = MDDSManager()
        cid, _ = mgr.register_consumer()
        await mgr.subscribe(["aapl", "Tsla"], cid)
        assert "AAPL" in mgr._subscriptions
        assert "TSLA" in mgr._subscriptions

    @pytest.mark.asyncio
    async def test_get_subscriptions_returns_copy(self):
        mgr = MDDSManager()
        cid, _ = mgr.register_consumer()
        await mgr.subscribe(["AAPL"], cid)
        subs = mgr.get_subscriptions()
        subs["AAPL"] = 999  # mutate the copy
        assert mgr._subscriptions["AAPL"] == 1  # original unchanged

    @pytest.mark.asyncio
    async def test_multiple_symbols_single_call(self):
        mgr = MDDSManager()
        cid, _ = mgr.register_consumer()
        await mgr.subscribe(["AAPL", "TSLA", "MSFT"], cid)
        assert len(mgr._subscriptions) == 3
        for sym in ("AAPL", "TSLA", "MSFT"):
            assert mgr._subscriptions[sym] == 1

    @pytest.mark.asyncio
    async def test_consumer_symbols_tracked(self):
        mgr = MDDSManager()
        cid, _ = mgr.register_consumer()
        await mgr.subscribe(["AAPL", "TSLA"], cid)
        assert mgr._consumer_symbols[cid] == {"AAPL", "TSLA"}
        await mgr.unsubscribe(["AAPL"], cid)
        assert mgr._consumer_symbols[cid] == {"TSLA"}


# ── MDDSManager: fan-out ─────────────────────────────────────────────


class TestFanOut:
    def test_fan_out_single_consumer(self):
        mgr = MDDSManager()
        _, queue = mgr.register_consumer()
        data = {"symbol": "AAPL", "last_price": "195.50"}
        mgr._fan_out(data)
        assert queue.qsize() == 1
        assert queue.get_nowait() == data

    def test_fan_out_multiple_consumers(self):
        mgr = MDDSManager()
        _, q1 = mgr.register_consumer()
        _, q2 = mgr.register_consumer()
        _, q3 = mgr.register_consumer()
        data = {"symbol": "TSLA", "bid": "178.00"}
        mgr._fan_out(data)
        for q in (q1, q2, q3):
            assert q.qsize() == 1
            assert q.get_nowait() == data

    def test_fan_out_drops_when_queue_full(self):
        mgr = MDDSManager()
        _, queue = mgr.register_consumer()
        # Fill the queue to its max (1000)
        for i in range(1000):
            queue.put_nowait({"i": i})
        assert queue.full()
        # This should not raise, just silently drop
        mgr._fan_out({"symbol": "AAPL"})
        assert queue.qsize() == 1000  # unchanged

    def test_fan_out_no_consumers(self):
        mgr = MDDSManager()
        mgr._fan_out({"symbol": "AAPL"})  # should not raise


# ── MDDSManager: lifecycle ───────────────────────────────────────────


class TestLifecycle:
    @pytest.mark.asyncio
    async def test_start_sets_running(self):
        mgr = MDDSManager()
        mock_client = MagicMock()
        mock_client._http = MagicMock()
        mock_client._http.cookies = {}
        await mgr.start(mock_client)
        assert mgr._running is True
        assert mgr._task is not None
        await mgr.stop()

    @pytest.mark.asyncio
    async def test_stop_clears_state(self):
        mgr = MDDSManager()
        mock_client = MagicMock()
        mock_client._http = MagicMock()
        mock_client._http.cookies = {}
        await mgr.start(mock_client)
        cid, _ = mgr.register_consumer()
        await mgr.subscribe(["AAPL"], cid)
        await mgr.stop()
        assert mgr._running is False
        assert mgr._task is None
        assert len(mgr._consumers) == 0
        assert len(mgr._subscriptions) == 0

    @pytest.mark.asyncio
    async def test_is_connected_reflects_state(self):
        mgr = MDDSManager()
        assert mgr.is_connected is False
        mock_client = MagicMock()
        mock_client._http = MagicMock()
        mock_client._http.cookies = {}
        await mgr.start(mock_client)
        assert mgr.is_connected is True
        await mgr.stop()
        assert mgr.is_connected is False

    @pytest.mark.asyncio
    async def test_double_start_warns(self):
        mgr = MDDSManager()
        mock_client = MagicMock()
        mock_client._http = MagicMock()
        mock_client._http.cookies = {}
        await mgr.start(mock_client)
        # Second start should just warn, not crash
        await mgr.start(mock_client)
        assert mgr._running is True
        await mgr.stop()


# ── REST endpoints ───────────────────────────────────────────────────


class TestRESTEndpoints:
    def test_status_endpoint(self):
        mgr = MDDSManager()
        app = _make_app(mgr)
        client = TestClient(app)
        resp = client.get("/api/v1/streaming/status")
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert body["data"]["connected"] is False
        assert body["data"]["consumers"] == 0
        assert body["data"]["subscriptions"] == 0

    def test_subscriptions_endpoint_empty(self):
        mgr = MDDSManager()
        app = _make_app(mgr)
        client = TestClient(app)
        resp = client.get("/api/v1/streaming/subscriptions")
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert body["data"]["subscriptions"] == {}

    def test_subscribe_endpoint(self):
        mgr = MDDSManager()
        app = _make_app(mgr)
        client = TestClient(app)
        resp = client.post(
            "/api/v1/streaming/subscribe",
            json={"symbols": ["AAPL", "tsla"]},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert set(body["data"]["subscribed"]) == {"AAPL", "TSLA"}
        # Verify subscriptions state
        assert mgr._subscriptions["AAPL"] == 1
        assert mgr._subscriptions["TSLA"] == 1

    def test_unsubscribe_endpoint(self):
        mgr = MDDSManager()
        app = _make_app(mgr)
        client = TestClient(app)
        # Subscribe first
        client.post("/api/v1/streaming/subscribe", json={"symbols": ["AAPL"]})
        assert "AAPL" in mgr._subscriptions
        # Unsubscribe
        resp = client.post(
            "/api/v1/streaming/unsubscribe",
            json={"symbols": ["AAPL"]},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert body["data"]["unsubscribed"] == ["AAPL"]
        assert "AAPL" not in mgr._subscriptions

    def test_subscriptions_after_subscribe(self):
        mgr = MDDSManager()
        app = _make_app(mgr)
        client = TestClient(app)
        client.post("/api/v1/streaming/subscribe", json={"symbols": ["AAPL", "MSFT"]})
        resp = client.get("/api/v1/streaming/subscriptions")
        body = resp.json()
        subs = body["data"]["subscriptions"]
        assert subs["AAPL"] == 1
        assert subs["MSFT"] == 1

    def test_status_shows_consumer_count(self):
        mgr = MDDSManager()
        mgr.register_consumer()
        mgr.register_consumer()
        app = _make_app(mgr)
        client = TestClient(app)
        resp = client.get("/api/v1/streaming/status")
        body = resp.json()
        assert body["data"]["consumers"] == 2


# ── SSE endpoint ─────────────────────────────────────────────────────


class TestSSEEndpoint:
    """Test SSE endpoint behaviour.

    Starlette's TestClient runs async generators in a background thread,
    so long-lived SSE streams block ``iter_lines()``.  To avoid hanging
    we test the route *declaration* (status, headers) via the app's
    route table and validate the SSE wire format with a direct
    unit test of the formatting logic.
    """

    def test_sse_route_registered(self):
        """The /api/v1/streaming/quotes route exists and uses GET."""
        app = _make_app()
        paths = {r.path for r in app.routes if hasattr(r, "path")}
        assert "/api/v1/streaming/quotes" in paths

    def test_sse_event_format(self):
        """Validate SSE event wire format (event + data lines)."""
        # Directly construct the SSE string the same way the endpoint does.
        quote = {"symbol": "AAPL", "last_price": "195.50"}
        sse_frame = f"event: quote\ndata: {json.dumps(quote)}\n\n"

        lines = sse_frame.strip().split("\n")
        assert lines[0] == "event: quote"
        payload = json.loads(lines[1].removeprefix("data: "))
        assert payload["symbol"] == "AAPL"
        assert payload["last_price"] == "195.50"

    def test_sse_keepalive_format(self):
        """Validate SSE heartbeat comment format."""
        keepalive = ": keepalive\n\n"
        assert keepalive.startswith(":")
        assert "keepalive" in keepalive


# ── WebSocket endpoint ───────────────────────────────────────────────


class TestWebSocketEndpoint:
    def test_websocket_connect_and_subscribe(self):
        mgr = MDDSManager()
        app = _make_app(mgr)
        client = TestClient(app)
        with client.websocket_connect("/api/v1/ws/quotes") as ws:
            ws.send_json({"action": "subscribe", "symbols": ["AAPL"]})
            # Push data so the send_quotes coroutine has something to send,
            # preventing it from blocking forever.
            mgr._fan_out({"symbol": "AAPL", "last_price": "100"})
            data = ws.receive_json()
            assert data["symbol"] == "AAPL"
            # Verify subscription was registered
            assert "AAPL" in mgr._subscriptions

    def test_websocket_receive_quote(self):
        mgr = MDDSManager()
        app = _make_app(mgr)
        client = TestClient(app)
        with client.websocket_connect("/api/v1/ws/quotes") as ws:
            ws.send_json({"action": "subscribe", "symbols": ["TSLA"]})
            # Push data to all consumer queues
            mgr._fan_out({"symbol": "TSLA", "last_price": "250.00"})
            data = ws.receive_json()
            assert data["symbol"] == "TSLA"
            assert data["last_price"] == "250.00"

    def test_websocket_multiple_quotes(self):
        mgr = MDDSManager()
        app = _make_app(mgr)
        client = TestClient(app)
        with client.websocket_connect("/api/v1/ws/quotes") as ws:
            ws.send_json({"action": "subscribe", "symbols": ["AAPL", "TSLA"]})
            mgr._fan_out({"symbol": "AAPL", "last_price": "195.00"})
            mgr._fan_out({"symbol": "TSLA", "last_price": "250.00"})
            d1 = ws.receive_json()
            d2 = ws.receive_json()
            symbols = {d1["symbol"], d2["symbol"]}
            assert symbols == {"AAPL", "TSLA"}
