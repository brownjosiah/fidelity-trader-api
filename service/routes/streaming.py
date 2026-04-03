"""REST control endpoints for streaming subscriptions."""

from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel

from service.models.responses import APIResponse, success
from service.models.schemas import (
    StreamingStatusData,
    StreamingSubscribedData,
    StreamingSubscriptionsData,
    StreamingUnsubscribedData,
)

router = APIRouter(prefix="/api/v1/streaming", tags=["streaming"])


class SymbolsRequest(BaseModel):
    symbols: list[str]


@router.post("/subscribe", response_model=APIResponse[StreamingSubscribedData], response_model_by_alias=True)
async def subscribe(request: Request, body: SymbolsRequest):
    """Subscribe to symbols on the MDDS stream.

    These are "global" subscriptions not tied to any SSE/WS consumer.
    Useful for pre-warming the stream before a consumer connects.
    """
    manager = request.app.state.mdds_manager
    # Use a sentinel consumer ID for REST-initiated subscriptions.
    consumer_id = "__rest__"
    if consumer_id not in manager._consumers:
        _, _ = manager.register_consumer()
        # Re-key under the sentinel ID
        last_id = list(manager._consumers.keys())[-1]
        manager._consumers[consumer_id] = manager._consumers.pop(last_id)
        manager._consumer_symbols[consumer_id] = manager._consumer_symbols.pop(last_id, set())

    symbols = [s.upper() for s in body.symbols]
    await manager.subscribe(symbols, consumer_id)
    return success(data={"subscribed": symbols})


@router.post("/unsubscribe", response_model=APIResponse[StreamingUnsubscribedData], response_model_by_alias=True)
async def unsubscribe(request: Request, body: SymbolsRequest):
    """Unsubscribe symbols from the MDDS stream."""
    manager = request.app.state.mdds_manager
    consumer_id = "__rest__"
    symbols = [s.upper() for s in body.symbols]
    await manager.unsubscribe(symbols, consumer_id)
    return success(data={"unsubscribed": symbols})


@router.get("/subscriptions", response_model=APIResponse[StreamingSubscriptionsData], response_model_by_alias=True)
async def subscriptions(request: Request):
    """Return current symbol subscriptions with refcounts."""
    manager = request.app.state.mdds_manager
    return success(data={"subscriptions": manager.get_subscriptions()})


@router.get("/status", response_model=APIResponse[StreamingStatusData], response_model_by_alias=True)
async def status(request: Request):
    """MDDS connection status."""
    manager = request.app.state.mdds_manager
    return success(data={
        "connected": manager.is_connected,
        "consumers": len(manager._consumers),
        "subscriptions": len(manager._subscriptions),
    })
