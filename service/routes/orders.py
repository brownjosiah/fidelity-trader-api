"""Order management routes: status, preview, place, cancel, and modify."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, Query

from fidelity_trader import FidelityClient
from fidelity_trader.models.cancel_order import CancelResponse
from fidelity_trader.models.cancel_replace import CancelReplaceRequest, CancelReplacePreviewResponse, CancelReplacePlaceResponse
from fidelity_trader.models.conditional_order import (
    ConditionalOrderRequest,
    ConditionalPreviewResponse,
    ConditionalPlaceResponse,
)
from fidelity_trader.models.equity_order import EquityOrderRequest, EquityPreviewResponse, EquityPlaceResponse
from fidelity_trader.models.option_order import (
    MultiLegOptionOrderRequest,
    MultiLegOptionPreviewResponse,
    MultiLegOptionPlaceResponse,
)
from fidelity_trader.models.order import OrderStatusResponse
from fidelity_trader.models.single_option_order import (
    SingleOptionOrderRequest,
    SingleOptionPreviewResponse,
    SingleOptionPlaceResponse,
)
from fidelity_trader.models.staged_order import StagedOrdersResponse
from service.dependencies import get_client
from service.models.requests import CancelOrderRequest, OrderPlaceRequest, ConditionalPlaceRequest
from service.models.responses import APIResponse, success

router = APIRouter(prefix="/api/v1/orders", tags=["Orders"])


# ── Status ───────────────────────────────────────────────────────────

@router.get("/status", response_model=APIResponse[OrderStatusResponse], response_model_by_alias=True)
async def get_order_status(
    acct_ids: str = Query(..., description="Comma-separated account numbers"),
    client: FidelityClient = Depends(get_client),
):
    """Fetch order status summary for the given accounts."""
    account_list = [a.strip() for a in acct_ids.split(",")]
    result = await asyncio.to_thread(client.order_status.get_order_status, account_list)
    return success(result.model_dump(by_alias=True))


@router.get("/staged", response_model=APIResponse[StagedOrdersResponse], response_model_by_alias=True)
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

@router.post("/equity/preview", response_model=APIResponse[EquityPreviewResponse], response_model_by_alias=True)
async def preview_equity_order(
    order: EquityOrderRequest,
    client: FidelityClient = Depends(get_client),
):
    """Preview an equity order and obtain a confirmation number."""
    result = await asyncio.to_thread(client.equity_orders.preview_order, order)
    return success(result.model_dump(by_alias=True))


@router.post("/equity/place", response_model=APIResponse[EquityPlaceResponse], response_model_by_alias=True)
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

@router.post("/option/preview", response_model=APIResponse[SingleOptionPreviewResponse], response_model_by_alias=True)
async def preview_single_option_order(
    order: SingleOptionOrderRequest,
    client: FidelityClient = Depends(get_client),
):
    """Preview a single-leg option order and obtain a confirmation number."""
    result = await asyncio.to_thread(client.single_option_orders.preview_order, order)
    return success(result.model_dump(by_alias=True))


@router.post("/option/place", response_model=APIResponse[SingleOptionPlaceResponse], response_model_by_alias=True)
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

@router.post("/options/preview", response_model=APIResponse[MultiLegOptionPreviewResponse], response_model_by_alias=True)
async def preview_multi_leg_option_order(
    order: MultiLegOptionOrderRequest,
    client: FidelityClient = Depends(get_client),
):
    """Preview a multi-leg option order and obtain a confirmation number."""
    result = await asyncio.to_thread(client.option_orders.preview_order, order)
    return success(result.model_dump(by_alias=True))


@router.post("/options/place", response_model=APIResponse[MultiLegOptionPlaceResponse], response_model_by_alias=True)
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

@router.post("/{conf_num}/cancel", response_model=APIResponse[CancelResponse], response_model_by_alias=True)
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

@router.post("/replace/preview", response_model=APIResponse[CancelReplacePreviewResponse], response_model_by_alias=True)
async def preview_cancel_replace_order(
    order: CancelReplaceRequest,
    client: FidelityClient = Depends(get_client),
):
    """Preview a cancel-and-replace (order modification)."""
    result = await asyncio.to_thread(client.cancel_replace.preview_order, order)
    return success(result.model_dump(by_alias=True))


@router.post("/replace/place", response_model=APIResponse[CancelReplacePlaceResponse], response_model_by_alias=True)
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

@router.post("/conditional/preview", response_model=APIResponse[ConditionalPreviewResponse], response_model_by_alias=True)
async def preview_conditional_order(
    order: ConditionalOrderRequest,
    client: FidelityClient = Depends(get_client),
):
    """Preview a conditional order (OTOCO/OTO/OCO)."""
    result = await asyncio.to_thread(client.conditional_orders.preview_order, order)
    return success(result.model_dump(by_alias=True))


@router.post("/conditional/place", response_model=APIResponse[ConditionalPlaceResponse], response_model_by_alias=True)
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
