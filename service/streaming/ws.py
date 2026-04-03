"""WebSocket endpoint for real-time quote streaming."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(tags=["streaming"])


@router.websocket("/api/v1/ws/quotes")
async def websocket_quotes(websocket: WebSocket):
    """Bidirectional WebSocket for quote streaming.

    After connecting, send JSON commands to subscribe/unsubscribe::

        {"action": "subscribe", "symbols": ["AAPL", "TSLA"]}
        {"action": "unsubscribe", "symbols": ["AAPL"]}

    The server pushes quote updates as JSON messages.
    """
    await websocket.accept()
    manager = websocket.app.state.mdds_manager
    consumer_id, queue = manager.register_consumer()
    subscribed_symbols: set[str] = set()

    try:

        async def send_quotes():
            while True:
                quote = await queue.get()
                await websocket.send_json(quote)

        async def recv_commands():
            while True:
                data = await websocket.receive_json()
                action = data.get("action")
                syms = [s.upper() for s in data.get("symbols", [])]
                if action == "subscribe":
                    await manager.subscribe(syms, consumer_id)
                    subscribed_symbols.update(syms)
                elif action == "unsubscribe":
                    await manager.unsubscribe(syms, consumer_id)
                    subscribed_symbols.difference_update(syms)

        await asyncio.gather(send_quotes(), recv_commands())
    except WebSocketDisconnect:
        pass
    finally:
        if subscribed_symbols:
            await manager.unsubscribe(list(subscribed_symbols), consumer_id)
        manager.unregister_consumer(consumer_id)
