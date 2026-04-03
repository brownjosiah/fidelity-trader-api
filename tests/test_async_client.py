"""Tests for the AsyncFidelityClient wrapper."""


import pytest
from unittest.mock import patch

from fidelity_trader import AsyncFidelityClient
from fidelity_trader.client import FidelityClient
from fidelity_trader.portfolio.positions import PositionsAPI
from fidelity_trader.portfolio.balances import BalancesAPI
from fidelity_trader.portfolio.option_summary import OptionSummaryAPI
from fidelity_trader.portfolio.transactions import TransactionsAPI
from fidelity_trader.orders.status import OrderStatusAPI
from fidelity_trader.orders.equity import EquityOrderAPI
from fidelity_trader.orders.options import MultiLegOptionOrderAPI
from fidelity_trader.orders.cancel import OrderCancelAPI
from fidelity_trader.orders.single_option import SingleOptionOrderAPI
from fidelity_trader.orders.cancel_replace import CancelReplaceAPI
from fidelity_trader.research.data import ResearchAPI
from fidelity_trader.research.search import SearchAPI
from fidelity_trader.streaming.news import StreamingNewsAPI
from fidelity_trader.watchlists.watchlists import WatchlistAPI
from fidelity_trader.portfolio.accounts import AccountsAPI
from fidelity_trader.market_data.fastquote import FastQuoteAPI
from fidelity_trader.market_data.chart import ChartAPI
from fidelity_trader.research.analytics import OptionAnalyticsAPI
from fidelity_trader.research.screener import ScreenerAPI
from fidelity_trader.alerts.subscription import AlertsAPI
from fidelity_trader.portfolio.closed_positions import ClosedPositionsAPI
from fidelity_trader.portfolio.loaned_securities import LoanedSecuritiesAPI
from fidelity_trader.portfolio.tax_lots import TaxLotAPI
from fidelity_trader.reference.markets import AvailableMarketsAPI
from fidelity_trader.settings.preferences import PreferencesAPI
from fidelity_trader.auth.security_context import SecurityContextAPI
from fidelity_trader.auth.session_keepalive import SessionKeepAliveAPI
from fidelity_trader.reference.holiday_calendar import HolidayCalendarAPI
from fidelity_trader.orders.staged import StagedOrderAPI
from fidelity_trader.alerts.price_triggers import PriceTriggersAPI
from fidelity_trader.orders.conditional import ConditionalOrderAPI


# ---------------------------------------------------------------------------
# Async context manager
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_async_context_manager_returns_client():
    async with AsyncFidelityClient() as client:
        assert isinstance(client, AsyncFidelityClient)


@pytest.mark.asyncio
async def test_async_context_manager_closes_on_exit():
    async with AsyncFidelityClient() as client:
        http = client._sync._http

    assert http.is_closed


# ---------------------------------------------------------------------------
# login / logout delegate to sync client
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_login_delegates_to_sync_client():
    async with AsyncFidelityClient() as client:
        expected = {"status": "ok"}
        with patch.object(client._sync, "login", return_value=expected) as mock_login:
            result = await client.login("user", "pass")
            mock_login.assert_called_once_with("user", "pass", None)
            assert result == expected


@pytest.mark.asyncio
async def test_login_passes_totp_secret():
    async with AsyncFidelityClient() as client:
        expected = {"status": "ok"}
        with patch.object(client._sync, "login", return_value=expected) as mock_login:
            result = await client.login("user", "pass", totp_secret="SECRET123")
            mock_login.assert_called_once_with("user", "pass", "SECRET123")
            assert result == expected


@pytest.mark.asyncio
async def test_logout_delegates_to_sync_client():
    async with AsyncFidelityClient() as client:
        with patch.object(client._sync, "logout") as mock_logout:
            await client.logout()
            mock_logout.assert_called_once()


# ---------------------------------------------------------------------------
# is_authenticated property
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_is_authenticated_false_by_default():
    async with AsyncFidelityClient() as client:
        assert client.is_authenticated is False


@pytest.mark.asyncio
async def test_is_authenticated_reflects_sync_state():
    async with AsyncFidelityClient() as client:
        client._sync._auth._authenticated = True
        assert client.is_authenticated is True


# ---------------------------------------------------------------------------
# close delegates
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_close_delegates_to_sync_client():
    client = AsyncFidelityClient()
    with patch.object(client._sync, "close") as mock_close:
        await client.close()
        mock_close.assert_called_once()


# ---------------------------------------------------------------------------
# enable/disable auto_refresh
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_enable_auto_refresh_delegates():
    async with AsyncFidelityClient() as client:
        with patch.object(
            client._sync, "enable_auto_refresh"
        ) as mock_enable:
            client.enable_auto_refresh(interval=120)
            mock_enable.assert_called_once_with(120)


@pytest.mark.asyncio
async def test_disable_auto_refresh_delegates():
    async with AsyncFidelityClient() as client:
        with patch.object(
            client._sync, "disable_auto_refresh"
        ) as mock_disable:
            client.disable_auto_refresh()
            mock_disable.assert_called_once()


# ---------------------------------------------------------------------------
# Module accessors return the sync module objects
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_module_accessors_return_sync_modules():
    async with AsyncFidelityClient() as client:
        sync = client._sync

        assert client.positions is sync.positions
        assert isinstance(client.positions, PositionsAPI)

        assert client.balances is sync.balances
        assert isinstance(client.balances, BalancesAPI)

        assert client.option_summary is sync.option_summary
        assert isinstance(client.option_summary, OptionSummaryAPI)

        assert client.transactions is sync.transactions
        assert isinstance(client.transactions, TransactionsAPI)

        assert client.order_status is sync.order_status
        assert isinstance(client.order_status, OrderStatusAPI)

        assert client.equity_orders is sync.equity_orders
        assert isinstance(client.equity_orders, EquityOrderAPI)

        assert client.option_orders is sync.option_orders
        assert isinstance(client.option_orders, MultiLegOptionOrderAPI)

        assert client.cancel_order is sync.cancel_order
        assert isinstance(client.cancel_order, OrderCancelAPI)

        assert client.single_option_orders is sync.single_option_orders
        assert isinstance(client.single_option_orders, SingleOptionOrderAPI)

        assert client.cancel_replace is sync.cancel_replace
        assert isinstance(client.cancel_replace, CancelReplaceAPI)

        assert client.research is sync.research
        assert isinstance(client.research, ResearchAPI)

        assert client.search is sync.search
        assert isinstance(client.search, SearchAPI)

        assert client.streaming is sync.streaming
        assert isinstance(client.streaming, StreamingNewsAPI)

        assert client.watchlists is sync.watchlists
        assert isinstance(client.watchlists, WatchlistAPI)

        assert client.accounts is sync.accounts
        assert isinstance(client.accounts, AccountsAPI)

        assert client.option_chain is sync.option_chain
        assert isinstance(client.option_chain, FastQuoteAPI)

        assert client.chart is sync.chart
        assert isinstance(client.chart, ChartAPI)

        assert client.option_analytics is sync.option_analytics
        assert isinstance(client.option_analytics, OptionAnalyticsAPI)

        assert client.alerts is sync.alerts
        assert isinstance(client.alerts, AlertsAPI)

        assert client.closed_positions is sync.closed_positions
        assert isinstance(client.closed_positions, ClosedPositionsAPI)

        assert client.loaned_securities is sync.loaned_securities
        assert isinstance(client.loaned_securities, LoanedSecuritiesAPI)

        assert client.tax_lots is sync.tax_lots
        assert isinstance(client.tax_lots, TaxLotAPI)

        assert client.available_markets is sync.available_markets
        assert isinstance(client.available_markets, AvailableMarketsAPI)

        assert client.preferences is sync.preferences
        assert isinstance(client.preferences, PreferencesAPI)

        assert client.security_context is sync.security_context
        assert isinstance(client.security_context, SecurityContextAPI)

        assert client.session_keepalive is sync.session_keepalive
        assert isinstance(client.session_keepalive, SessionKeepAliveAPI)

        assert client.holiday_calendar is sync.holiday_calendar
        assert isinstance(client.holiday_calendar, HolidayCalendarAPI)

        assert client.staged_orders is sync.staged_orders
        assert isinstance(client.staged_orders, StagedOrderAPI)

        assert client.price_triggers is sync.price_triggers
        assert isinstance(client.price_triggers, PriceTriggersAPI)

        assert client.conditional_orders is sync.conditional_orders
        assert isinstance(client.conditional_orders, ConditionalOrderAPI)

        assert client.screener is sync.screener
        assert isinstance(client.screener, ScreenerAPI)


# ---------------------------------------------------------------------------
# Async convenience methods
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_positions_delegates():
    async with AsyncFidelityClient() as client:
        expected = [{"symbol": "AAPL"}]
        with patch.object(
            client._sync.positions, "get_positions", return_value=expected
        ) as mock:
            result = await client.get_positions(["Z12345678"])
            mock.assert_called_once_with(["Z12345678"])
            assert result == expected


@pytest.mark.asyncio
async def test_get_positions_passes_kwargs():
    async with AsyncFidelityClient() as client:
        with patch.object(
            client._sync.positions, "get_positions", return_value=[]
        ) as mock:
            await client.get_positions(["Z12345678"], include_options=True)
            mock.assert_called_once_with(["Z12345678"], include_options=True)


@pytest.mark.asyncio
async def test_get_balances_delegates():
    async with AsyncFidelityClient() as client:
        expected = [{"balance": 1000}]
        with patch.object(
            client._sync.balances, "get_balances", return_value=expected
        ) as mock:
            result = await client.get_balances(["Z12345678"])
            mock.assert_called_once_with(["Z12345678"])
            assert result == expected


@pytest.mark.asyncio
async def test_get_order_status_delegates():
    async with AsyncFidelityClient() as client:
        expected = [{"order": "filled"}]
        with patch.object(
            client._sync.order_status, "get_order_status", return_value=expected
        ) as mock:
            result = await client.get_order_status(["Z12345678"])
            mock.assert_called_once_with(["Z12345678"])
            assert result == expected


# ---------------------------------------------------------------------------
# kwargs pass through to FidelityClient
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_kwargs_pass_through_to_sync_client():
    """AsyncFidelityClient(**kwargs) should forward kwargs to FidelityClient."""
    with patch.object(
        FidelityClient, "__init__", return_value=None
    ) as mock_init:
        AsyncFidelityClient(foo="bar", baz=42)
        mock_init.assert_called_once_with(foo="bar", baz=42)


# ---------------------------------------------------------------------------
# Package-level export
# ---------------------------------------------------------------------------


def test_async_client_exported_from_package():
    import fidelity_trader

    assert hasattr(fidelity_trader, "AsyncFidelityClient")
    assert fidelity_trader.AsyncFidelityClient is AsyncFidelityClient
