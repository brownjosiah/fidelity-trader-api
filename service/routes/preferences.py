"""Preferences routes: get, save, and delete user preferences."""

from __future__ import annotations

import asyncio
from typing import Optional

from fastapi import APIRouter, Body, Depends, Query

from fidelity_trader import FidelityClient
from service.dependencies import get_client
from service.models.responses import success

router = APIRouter(prefix="/api/v1/preferences", tags=["Preferences"])


@router.get("")
async def get_preferences(
    preference_path: str = Query("user/", description="Preference path to query"),
    pref_keys: Optional[list[str]] = Query(None, description="Specific keys to retrieve"),
    client: FidelityClient = Depends(get_client),
):
    """Fetch preferences at the given path."""
    result = await asyncio.to_thread(
        client.preferences.get_preferences,
        preference_path,
        pref_keys,
    )
    return success(result.model_dump(by_alias=True))


@router.put("")
async def save_preferences(
    preference_path: str = Body(...),
    values: dict[str, str] = Body(...),
    client: FidelityClient = Depends(get_client),
):
    """Save preference key-value pairs at the given path."""
    result = await asyncio.to_thread(
        client.preferences.save_preferences,
        preference_path,
        values,
    )
    return success(result.model_dump(by_alias=True))


@router.delete("")
async def delete_preferences(
    preference_path: str = Body(...),
    pref_keys: Optional[list[str]] = Body(None),
    client: FidelityClient = Depends(get_client),
):
    """Delete preferences at the given path."""
    result = await asyncio.to_thread(
        client.preferences.delete_preferences,
        preference_path,
        pref_keys,
    )
    return success(result.model_dump(by_alias=True))
