"""Market data routes: option chain, montage, chart, available markets."""

from __future__ import annotations

import asyncio
from dataclasses import asdict
from typing import List

from fastapi import APIRouter, Depends, Query

from fidelity_trader import FidelityClient
from service.dependencies import get_client
from service.models.responses import success

router = APIRouter(prefix="/api/v1/market-data", tags=["Market Data"])


@router.get("/chain/{symbol}")
async def get_option_chain(
    symbol: str,
    client: FidelityClient = Depends(get_client),
):
    """Fetch the options chain for the given underlying symbol."""
    result = await asyncio.to_thread(client.option_chain.get_option_chain, symbol)
    return success(asdict(result))


@router.get("/montage/{symbol}")
async def get_montage(
    symbol: str,
    client: FidelityClient = Depends(get_client),
):
    """Fetch depth-of-market (exchange-level) quotes for a single option symbol."""
    result = await asyncio.to_thread(client.option_chain.get_montage, symbol)
    return success(asdict(result))


@router.get("/chart/{symbol}")
async def get_chart(
    symbol: str,
    start_date: str = Query(..., description="Start date as YYYY/MM/DD-HH:MM:SS"),
    end_date: str = Query(..., description="End date as YYYY/MM/DD-HH:MM:SS"),
    bar_width: str = Query("5", description="Bar size: 1, 5, 15, 30, 60, D, W, M"),
    extended_hours: bool = Query(True, description="Include pre/post-market bars"),
    client: FidelityClient = Depends(get_client),
):
    """Fetch historical OHLCV bar data for a symbol."""
    result = await asyncio.to_thread(
        client.chart.get_chart,
        symbol,
        start_date,
        end_date,
        bar_width,
        extended_hours,
    )
    return success(asdict(result))


@router.get("/markets/{symbol}")
async def get_available_markets(
    symbol: str,
    account_numbers: List[str] = Query(..., description="Account numbers to check"),
    client: FidelityClient = Depends(get_client),
):
    """Fetch available trading markets for a symbol and accounts."""
    result = await asyncio.to_thread(
        client.available_markets.get_available_markets,
        symbol,
        account_numbers,
    )
    return success(result.model_dump(by_alias=True))
