"""Async wrapper around FidelityClient using asyncio.to_thread."""

import asyncio

from fidelity_trader.client import FidelityClient


class AsyncFidelityClient:
    """Async variant of FidelityClient.

    Wraps the sync client and delegates calls to a thread executor
    via asyncio.to_thread, so they don't block the event loop.

    Usage:
        async with AsyncFidelityClient() as client:
            await client.login(username, password)
            positions = await client.get_positions(["Z12345678"])
    """

    def __init__(self, **kwargs) -> None:
        self._sync = FidelityClient(**kwargs)

    # ------------------------------------------------------------------
    # Auth lifecycle
    # ------------------------------------------------------------------

    async def login(
        self, username: str, password: str, totp_secret: str = None
    ) -> dict:
        return await asyncio.to_thread(
            self._sync.login, username, password, totp_secret
        )

    async def logout(self) -> None:
        await asyncio.to_thread(self._sync.logout)

    @property
    def is_authenticated(self) -> bool:
        return self._sync.is_authenticated

    # ------------------------------------------------------------------
    # Auto-refresh (sync — just delegates, no I/O)
    # ------------------------------------------------------------------

    def enable_auto_refresh(self, interval: int = 300) -> None:
        self._sync.enable_auto_refresh(interval)

    def disable_auto_refresh(self) -> None:
        self._sync.disable_auto_refresh()

    # ------------------------------------------------------------------
    # Close / context manager
    # ------------------------------------------------------------------

    async def close(self) -> None:
        await asyncio.to_thread(self._sync.close)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()

    # ------------------------------------------------------------------
    # Module accessors — expose the sync module objects directly.
    # Users can wrap individual calls via asyncio.to_thread themselves:
    #   result = await asyncio.to_thread(client.research.get_earnings, ...)
    # ------------------------------------------------------------------

    @property
    def positions(self):
        return self._sync.positions

    @property
    def balances(self):
        return self._sync.balances

    @property
    def option_summary(self):
        return self._sync.option_summary

    @property
    def transactions(self):
        return self._sync.transactions

    @property
    def order_status(self):
        return self._sync.order_status

    @property
    def equity_orders(self):
        return self._sync.equity_orders

    @property
    def option_orders(self):
        return self._sync.option_orders

    @property
    def cancel_order(self):
        return self._sync.cancel_order

    @property
    def single_option_orders(self):
        return self._sync.single_option_orders

    @property
    def cancel_replace(self):
        return self._sync.cancel_replace

    @property
    def research(self):
        return self._sync.research

    @property
    def search(self):
        return self._sync.search

    @property
    def streaming(self):
        return self._sync.streaming

    @property
    def watchlists(self):
        return self._sync.watchlists

    @property
    def accounts(self):
        return self._sync.accounts

    @property
    def option_chain(self):
        return self._sync.option_chain

    @property
    def chart(self):
        return self._sync.chart

    @property
    def option_analytics(self):
        return self._sync.option_analytics

    @property
    def alerts(self):
        return self._sync.alerts

    @property
    def closed_positions(self):
        return self._sync.closed_positions

    @property
    def loaned_securities(self):
        return self._sync.loaned_securities

    @property
    def tax_lots(self):
        return self._sync.tax_lots

    @property
    def available_markets(self):
        return self._sync.available_markets

    @property
    def preferences(self):
        return self._sync.preferences

    @property
    def security_context(self):
        return self._sync.security_context

    @property
    def session_keepalive(self):
        return self._sync.session_keepalive

    @property
    def holiday_calendar(self):
        return self._sync.holiday_calendar

    @property
    def staged_orders(self):
        return self._sync.staged_orders

    @property
    def price_triggers(self):
        return self._sync.price_triggers

    @property
    def conditional_orders(self):
        return self._sync.conditional_orders

    @property
    def screener(self):
        return self._sync.screener

    # ------------------------------------------------------------------
    # Async convenience methods for the most common operations.
    # For everything else, access the module property and wrap the call:
    #   result = await asyncio.to_thread(client.research.get_earnings, ...)
    # ------------------------------------------------------------------

    async def get_positions(self, account_numbers, **kwargs):
        """Async shortcut for positions.get_positions()."""
        return await asyncio.to_thread(
            self._sync.positions.get_positions, account_numbers, **kwargs
        )

    async def get_balances(self, account_numbers, **kwargs):
        """Async shortcut for balances.get_balances()."""
        return await asyncio.to_thread(
            self._sync.balances.get_balances, account_numbers, **kwargs
        )

    async def get_order_status(self, account_numbers, **kwargs):
        """Async shortcut for order_status.get_order_status()."""
        return await asyncio.to_thread(
            self._sync.order_status.get_order_status, account_numbers, **kwargs
        )
