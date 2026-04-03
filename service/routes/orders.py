"""Order management routes: status, preview, place, cancel, and modify."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, Query

from fidelity_trader import FidelityClient
from fidelity_trader.models.equity_order import EquityOrderRequest
from fidelity_trader.models.single_option_order import SingleOptionOrderRequest
from fidelity_trader.models.option_order import MultiLegOptionOrderRequest
from fidelity_trader.models.cancel_replace import CancelReplaceRequest
from fidelity_trader.models.conditional_order import ConditionalOrderRequest
from service.dependencies import get_client
from service.models.requests import CancelOrderRequest, OrderPlaceRequest, ConditionalPlaceRequest
from service.models.responses import success

router = APIRouter(prefix="/api/v1/orders", tags=["Orders"])


# ── Status ───────────────────────────────────────────────────────────

@router.get("/status")
async def get_order_status(
    acct_ids: str = Query(..., description="Comma-separated account numbers"),
    client: FidelityClient = Depends(get_client),
):
    """Fetch order status summary for the given accounts."""
    account_list = [a.strip() for a in acct_ids.split(",")]
    result = await asyncio.to_thread(client.order_status.get_order_status, account_list)
    return success(result.model_dump(by_alias=True))


@router.get("/staged")
async def get_staged_orders(
    stage_type: str = Query("saveD_ORDER", description="Stage type"),
    client: FidelityClient = Depends(get_client),
):
    """Retrieve staged/saved orders."""
    result = await asyncio.to_thread(
        client.staged_orders.get_staged_orders, stage_type
    )
    return success(result.model_dump(by_alias=True))


# ── Equity Orders ────────────────────────────────────────────────────

@router.post("/equity/preview")
async def preview_equity_order(
    order: EquityOrderRequest,
    client: FidelityClient = Depends(get_client),
):
    """Preview an equity order and obtain a confirmation number."""
    result = await asyncio.to_thread(client.equity_orders.preview_order, order)
    return success(result.model_dump(by_alias=True))


@router.post("/equity/place")
async def place_equity_order(
    body: OrderPlaceRequest,
    client: FidelityClient = Depends(get_client),
):
    """Place a previously-previewed equity order."""
    order = EquityOrderRequest(**body.order)
    result = await asyncio.to_thread(
        client.equity_orders.place_order, order, body.conf_num
    )
    return success(result.model_dump(by_alias=True))


# ── Single-Leg Option Orders ────────────────────────────────────────

@router.post("/option/preview")
async def preview_single_option_order(
    order: SingleOptionOrderRequest,
    client: FidelityClient = Depends(get_client),
):
    """Preview a single-leg option order and obtain a confirmation number."""
    result = await asyncio.to_thread(client.single_option_orders.preview_order, order)
    return success(result.model_dump(by_alias=True))


@router.post("/option/place")
async def place_single_option_order(
    body: OrderPlaceRequest,
    client: FidelityClient = Depends(get_client),
):
    """Place a previously-previewed single-leg option order."""
    order = SingleOptionOrderRequest(**body.order)
    result = await asyncio.to_thread(
        client.single_option_orders.place_order, order, body.conf_num
    )
    return success(result.model_dump(by_alias=True))


# ── Multi-Leg Option Orders ─────────────────────────────────────────

@router.post("/options/preview")
async def preview_multi_leg_option_order(
    order: MultiLegOptionOrderRequest,
    client: FidelityClient = Depends(get_client),
):
    """Preview a multi-leg option order and obtain a confirmation number."""
    result = await asyncio.to_thread(client.option_orders.preview_order, order)
    return success(result.model_dump(by_alias=True))


@router.post("/options/place")
async def place_multi_leg_option_order(
    body: OrderPlaceRequest,
    client: FidelityClient = Depends(get_client),
):
    """Place a previously-previewed multi-leg option order."""
    order = MultiLegOptionOrderRequest(**body.order)
    result = await asyncio.to_thread(
        client.option_orders.place_order, order, body.conf_num
    )
    return success(result.model_dump(by_alias=True))


# ── Cancel ───────────────────────────────────────────────────────────

@router.post("/{conf_num}/cancel")
async def cancel_order(
    conf_num: str,
    body: CancelOrderRequest,
    client: FidelityClient = Depends(get_client),
):
    """Cancel an open order by confirmation number."""
    result = await asyncio.to_thread(
        client.cancel_order.cancel_order,
        conf_num,
        body.acct_num,
        body.action_code,
    )
    return success(result.model_dump(by_alias=True))


# ── Cancel-and-Replace ──────────────────────────────────────────────

@router.post("/replace/preview")
async def preview_cancel_replace_order(
    order: CancelReplaceRequest,
    client: FidelityClient = Depends(get_client),
):
    """Preview a cancel-and-replace (order modification)."""
    result = await asyncio.to_thread(client.cancel_replace.preview_order, order)
    return success(result.model_dump(by_alias=True))


@router.post("/replace/place")
async def place_cancel_replace_order(
    body: OrderPlaceRequest,
    client: FidelityClient = Depends(get_client),
):
    """Place a previously-previewed cancel-and-replace order modification."""
    order = CancelReplaceRequest(**body.order)
    result = await asyncio.to_thread(
        client.cancel_replace.place_order, order, body.conf_num
    )
    return success(result.model_dump(by_alias=True))


# ── Conditional Orders ──────────────────────────────────────────────

@router.post("/conditional/preview")
async def preview_conditional_order(
    order: ConditionalOrderRequest,
    client: FidelityClient = Depends(get_client),
):
    """Preview a conditional order (OTOCO/OTO/OCO)."""
    result = await asyncio.to_thread(client.conditional_orders.preview_order, order)
    return success(result.model_dump(by_alias=True))


@router.post("/conditional/place")
async def place_conditional_order(
    body: ConditionalPlaceRequest,
    client: FidelityClient = Depends(get_client),
):
    """Place a previously-previewed conditional order."""
    order = ConditionalOrderRequest(**body.order)
    result = await asyncio.to_thread(
        client.conditional_orders.place_order, order, body.conf_nums
    )
    return success(result.model_dump(by_alias=True))
