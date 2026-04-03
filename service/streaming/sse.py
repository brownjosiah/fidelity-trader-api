"""Server-Sent Events endpoint for real-time quote streaming."""

from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Query, Request
from starlette.responses import StreamingResponse

router = APIRouter(prefix="/api/v1/streaming", tags=["streaming"])


@router.get("/quotes")
async def stream_quotes(
    request: Request,
    symbols: str = Query(..., description="Comma-separated symbols, e.g. AAPL,TSLA"),
):
    """SSE stream of real-time quotes.

    Connect with::

        GET /api/v1/streaming/quotes?symbols=AAPL,TSLA

    The stream emits ``event: quote`` messages with JSON data and
    periodic ``: keepalive`` comments (SSE heartbeat) when idle.
    """
    manager = request.app.state.mdds_manager
    consumer_id, queue = manager.register_consumer()
    symbol_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]

    await manager.subscribe(symbol_list, consumer_id)

    async def event_generator():
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    quote = await asyncio.wait_for(queue.get(), timeout=30)
                    yield f"event: quote\ndata: {json.dumps(quote)}\n\n"
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        finally:
            await manager.unsubscribe(symbol_list, consumer_id)
            manager.unregister_consumer(consumer_id)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
