"""Reference data routes: holiday calendar."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, Query

from fidelity_trader import FidelityClient
from fidelity_trader.models.holiday_calendar import HolidayCalendarResponse
from service.dependencies import get_client
from service.models.responses import APIResponse, success

router = APIRouter(prefix="/api/v1/reference", tags=["Reference"])


@router.get("/holiday-calendar", response_model=APIResponse[HolidayCalendarResponse], response_model_by_alias=True)
async def get_holiday_calendar(
    country_code: str = Query("US", description="Country code for the market calendar"),
    client: FidelityClient = Depends(get_client),
):
    """Fetch the market holiday calendar for the given country."""
    result = await asyncio.to_thread(
        client.holiday_calendar.get_holidays,
        country_code,
    )
    return success(result.model_dump(by_alias=True))
