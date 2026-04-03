"""Watchlist and alerts routes: watchlists, alert subscription, price triggers."""

from __future__ import annotations

import asyncio
from dataclasses import asdict
from typing import List, Optional, Union

from fastapi import APIRouter, Body, Depends, Query

from fidelity_trader import FidelityClient
from fidelity_trader.models.price_trigger import (
    PriceTriggerCreateResponse,
    PriceTriggerDeleteResponse,
    PriceTriggersResponse,
)
from fidelity_trader.models.watchlist import WatchlistResponse, WatchlistSaveResponse
from service.dependencies import get_client
from service.models.responses import APIResponse, success
from service.models.schemas import AlertActivationSchema

router = APIRouter(prefix="/api/v1", tags=["Watchlists & Alerts"])


# ── Watchlists ───────────────────────────────────────────────────────

@router.get("/watchlists", response_model=APIResponse[WatchlistResponse], response_model_by_alias=True)
async def get_watchlists(
    watchlist_ids: Optional[List[str]] = Query(None, description="Specific watchlist UUIDs to retrieve"),
    watchlist_type_code: str = Query("WL", description="Watchlist type code"),
    include_security_details: bool = Query(True, description="Include per-security metadata"),
    client: FidelityClient = Depends(get_client),
):
    """Fetch all watchlists (or specific ones by ID) for the authenticated customer."""
    result = await asyncio.to_thread(
        client.watchlists.get_watchlists,
        watchlist_ids,
        watchlist_type_code,
        include_security_details,
    )
    return success(result.model_dump(by_alias=True))


@router.post("/watchlists/save", response_model=APIResponse[WatchlistSaveResponse], response_model_by_alias=True)
async def save_watchlist(
    watchlist_details: Union[dict, list[dict]] = Body(...),
    client: FidelityClient = Depends(get_client),
):
    """Save (create or update) one or more watchlists."""
    result = await asyncio.to_thread(
        client.watchlists.save_watchlist,
        watchlist_details,
    )
    return success(result.model_dump(by_alias=True))


# ── Alerts ───────────────────────────────────────────────────────────

@router.get("/alerts/subscribe", response_model=APIResponse[AlertActivationSchema], response_model_by_alias=True)
async def subscribe_alerts(
    client: FidelityClient = Depends(get_client),
):
    """Subscribe to ATP/ATBT alerts and retrieve STOMP/JMS credentials."""
    result = await asyncio.to_thread(client.alerts.subscribe)
    return success(asdict(result))


@router.get("/alerts/price-triggers", response_model=APIResponse[PriceTriggersResponse], response_model_by_alias=True)
async def get_price_triggers(
    symbol: str = Query(..., description="Ticker symbol to query"),
    status: str = Query("active", description="Filter by trigger status"),
    offset: int = Query(0, description="Pagination offset"),
    client: FidelityClient = Depends(get_client),
):
    """Fetch the list of price triggers for a given symbol."""
    result = await asyncio.to_thread(
        client.price_triggers.get_price_triggers,
        symbol,
        status,
        offset,
    )
    return success(result.model_dump(by_alias=True))


@router.post("/alerts/price-triggers", response_model=APIResponse[PriceTriggerCreateResponse], response_model_by_alias=True)
async def create_price_trigger(
    symbol: str = Body(...),
    operator: str = Body(...),
    value: float = Body(...),
    currency: str = Body("USD"),
    notes: str = Body(""),
    client: FidelityClient = Depends(get_client),
):
    """Create a new price trigger."""
    result = await asyncio.to_thread(
        client.price_triggers.create_price_trigger,
        symbol,
        operator,
        value,
        currency,
        notes,
    )
    return success(result.model_dump(by_alias=True))


@router.delete("/alerts/price-triggers/{trigger_id}", response_model=APIResponse[PriceTriggerDeleteResponse], response_model_by_alias=True)
async def delete_price_trigger(
    trigger_id: str,
    client: FidelityClient = Depends(get_client),
):
    """Delete a price trigger by ID."""
    result = await asyncio.to_thread(
        client.price_triggers.delete_price_triggers,
        [trigger_id],
    )
    return success(result.model_dump(by_alias=True))
