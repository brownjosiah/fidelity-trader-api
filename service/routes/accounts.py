"""Account and portfolio data routes."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, Query

from fidelity_trader import FidelityClient
from service.dependencies import get_client
from service.models.responses import success

router = APIRouter(prefix="/api/v1/accounts", tags=["Accounts"])


@router.get("")
async def discover_accounts(client: FidelityClient = Depends(get_client)):
    """Discover all accounts for the authenticated user."""
    result = await asyncio.to_thread(client.accounts.discover_accounts)
    return success(result.model_dump(by_alias=True))


@router.get("/{acct}/positions")
async def get_positions(acct: str, client: FidelityClient = Depends(get_client)):
    """Fetch positions for a single account."""
    result = await asyncio.to_thread(client.positions.get_positions, [acct])
    return success(result.model_dump(by_alias=True))


@router.get("/{acct}/balances")
async def get_balances(acct: str, client: FidelityClient = Depends(get_client)):
    """Fetch balances for a single account."""
    result = await asyncio.to_thread(client.balances.get_balances, [acct])
    return success(result.model_dump(by_alias=True))


@router.get("/{acct}/transactions")
async def get_transactions(
    acct: str,
    from_date: int = Query(..., description="Start date as Unix timestamp (seconds)"),
    to_date: int = Query(..., description="End date as Unix timestamp (seconds)"),
    client: FidelityClient = Depends(get_client),
):
    """Fetch transaction history for a single account."""
    result = await asyncio.to_thread(
        client.transactions.get_transaction_history, [acct], from_date, to_date
    )
    return success(result.model_dump(by_alias=True))


@router.get("/{acct}/options-summary")
async def get_option_summary(acct: str, client: FidelityClient = Depends(get_client)):
    """Fetch option positions summary for a single account."""
    result = await asyncio.to_thread(client.option_summary.get_option_summary, [acct])
    return success(result.model_dump(by_alias=True))


@router.get("/{acct}/closed-positions")
async def get_closed_positions(
    acct: str,
    start_date: str = Query(..., description="ISO start date, e.g. 2026-01-01"),
    end_date: str = Query(..., description="ISO end date, e.g. 2026-03-30"),
    date_type: str = Query("YTD", description="Date range type label"),
    client: FidelityClient = Depends(get_client),
):
    """Fetch closed positions for a single account."""
    result = await asyncio.to_thread(
        client.closed_positions.get_closed_positions,
        [acct],
        start_date,
        end_date,
        date_type,
    )
    return success(result.model_dump(by_alias=True))


@router.get("/{acct}/loaned-securities")
async def get_loaned_securities(acct: str, client: FidelityClient = Depends(get_client)):
    """Fetch loaned securities data for a single account."""
    result = await asyncio.to_thread(client.loaned_securities.get_loaned_securities, [acct])
    return success(result.model_dump(by_alias=True))


@router.get("/{acct}/tax-lots/{symbol}")
async def get_tax_lots(
    acct: str,
    symbol: str,
    client: FidelityClient = Depends(get_client),
):
    """Fetch tax lot details for a specific symbol in an account."""
    result = await asyncio.to_thread(client.tax_lots.get_tax_lots, acct, symbol)
    return success(result.model_dump(by_alias=True))
