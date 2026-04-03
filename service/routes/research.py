"""Research routes: earnings, dividends, search, analytics, screener."""

from __future__ import annotations

import asyncio
from dataclasses import asdict
from typing import List

from fastapi import APIRouter, Body, Depends, Query

from fidelity_trader import FidelityClient
from fidelity_trader.models.analytics import AnalyticsResponse
from fidelity_trader.models.research import DividendsResponse, EarningsResponse
from fidelity_trader.models.search import AutosuggestResponse
from service.dependencies import get_client
from service.models.responses import APIResponse, success
from service.models.schemas import ScanResultSchema

router = APIRouter(prefix="/api/v1/research", tags=["Research"])


@router.get("/earnings", response_model=APIResponse[EarningsResponse], response_model_by_alias=True)
async def get_earnings(
    symbols: List[str] = Query(..., description="Ticker symbols to fetch earnings for"),
    client: FidelityClient = Depends(get_client),
):
    """Fetch earnings data for the given symbols."""
    result = await asyncio.to_thread(client.research.get_earnings, symbols)
    return success(result.model_dump(by_alias=True))


@router.get("/dividends", response_model=APIResponse[DividendsResponse], response_model_by_alias=True)
async def get_dividends(
    symbols: List[str] = Query(..., description="Ticker symbols to fetch dividends for"),
    client: FidelityClient = Depends(get_client),
):
    """Fetch dividend data for the given symbols."""
    result = await asyncio.to_thread(client.research.get_dividends, symbols)
    return success(result.model_dump(by_alias=True))


@router.get("/search", response_model=APIResponse[AutosuggestResponse], response_model_by_alias=True)
async def autosuggest(
    q: str = Query(..., description="Search query string"),
    client: FidelityClient = Depends(get_client),
):
    """Fetch symbol autosuggest results for the given query."""
    result = await asyncio.to_thread(client.search.autosuggest, q)
    return success(result.model_dump(by_alias=True))


@router.post("/analytics", response_model=APIResponse[AnalyticsResponse], response_model_by_alias=True)
async def analyze_position(
    underlying_symbol: str = Body(...),
    legs: list[dict] = Body(...),
    volatility_period: str = Body("90"),
    eval_at_expiry: bool = Body(True),
    client: FidelityClient = Depends(get_client),
):
    """Analyze an option position (one or more legs)."""
    result = await asyncio.to_thread(
        client.option_analytics.analyze_position,
        underlying_symbol,
        legs,
        volatility_period,
        eval_at_expiry,
    )
    return success(result.model_dump(by_alias=True))


@router.post("/screener", response_model=APIResponse[ScanResultSchema], response_model_by_alias=True)
async def execute_scan(
    scan_id: int = Body(..., embed=True),
    client: FidelityClient = Depends(get_client),
):
    """Execute a LiveVol screener scan by ID.

    The screener must be authenticated first (SAML flow).
    This endpoint handles authentication automatically.
    """
    await asyncio.to_thread(client.screener.authenticate)
    result = await asyncio.to_thread(client.screener.execute_scan, scan_id)
    return success(asdict(result))
